import os
import json
import time
import google.generativeai as genai
import PIL.Image

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
# Replace with your actual Google AI Studio API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBeUFgh4pLxLY6xxuqGNi3Fr-w1_NEBpTI")

# STRICTLY using the model requested
MODEL_NAME = "gemini-3-flash-preview"

# Configure the SDK
genai.configure(api_key=GOOGLE_API_KEY)

# ------------------------------------------------------------------
# SIZE RECOMMENDATION FUNCTION
# ------------------------------------------------------------------
def recommend_size(measurements, size_chart):
    """
    Recommends a size based on body measurements and size chart.
    
    Logic: Finds the smallest size where ALL measurements fit (all <= size limits).
    Works for all sizes: S, M, L, XL, XXL, etc.
    
    If ANY measurement exceeds a size's limit, we check the next larger size.
    Continues until we find a size where all measurements fit, or reaches the largest size.
    
    Args:
        measurements: dict with 'shoulder_width', 'chest_circumference', 'waist_circumference'
        size_chart: dict with size names as keys and dicts with measurements as values
                    e.g., {'S': {'shoulder': 40.6, 'chest': 96.5, 'waist': 71.1}, 
                           'M': {'shoulder': 43.2, 'chest': 101.6, 'waist': 76.2}, ...}
    
    Returns:
        dict with recommended size and details, including timing information
    """
    # Record start time for size recommendation
    rec_start_time = time.time()
    
    if not measurements or "measurements_cm" not in measurements:
        return None
    
    meas = measurements["measurements_cm"]
    shoulder = meas.get("shoulder_width", {}).get("value", 0)
    chest = meas.get("chest_circumference", {}).get("value", 0)
    waist = meas.get("waist_circumference", {}).get("value", 0)
    
    # Get size order (S, M, L, XL, XXL, etc.)
    size_order = list(size_chart.keys())
    
    # Track which sizes were checked and why they didn't fit
    checked_sizes = []
    
    # Check each size from smallest to largest (S -> M -> L -> XL -> XXL)
    for i, size in enumerate(size_order):
        size_measurements = size_chart[size]
        
        # Check if all measurements fit in this size
        shoulder_fits = shoulder <= size_measurements.get("shoulder", float('inf'))
        chest_fits = chest <= size_measurements.get("chest", float('inf'))
        waist_fits = waist <= size_measurements.get("waist", float('inf'))
        
        # Track why this size doesn't fit (if it doesn't)
        reasons = []
        if not shoulder_fits:
            reasons.append(f"shoulder ({shoulder:.1f} > {size_measurements.get('shoulder', 0):.1f})")
        if not chest_fits:
            reasons.append(f"chest ({chest:.1f} > {size_measurements.get('chest', 0):.1f})")
        if not waist_fits:
            reasons.append(f"waist ({waist:.1f} > {size_measurements.get('waist', 0):.1f})")
        
        checked_sizes.append({
            "size": size,
            "fits": shoulder_fits and chest_fits and waist_fits,
            "reasons": reasons if reasons else ["All measurements fit"]
        })
        
        # If all measurements fit, this is the recommended size
        if shoulder_fits and chest_fits and waist_fits:
            rec_end_time = time.time()
            rec_latency = rec_end_time - rec_start_time
            return {
                "recommended_size": size,
                "reason": "All measurements fit within this size",
                "checked_sizes": checked_sizes,
                "recommendation_time_seconds": round(rec_latency, 6),
                "comparison": {
                    "shoulder": {
                        "measured": shoulder,
                        "size_limit": size_measurements.get("shoulder"),
                        "fits": shoulder_fits
                    },
                    "chest": {
                        "measured": chest,
                        "size_limit": size_measurements.get("chest"),
                        "fits": chest_fits
                    },
                    "waist": {
                        "measured": waist,
                        "size_limit": size_measurements.get("waist"),
                        "fits": waist_fits
                    }
                }
            }
        
        # If this is the last size and still doesn't fit, recommend the largest size
        if i == len(size_order) - 1:
            rec_end_time = time.time()
            rec_latency = rec_end_time - rec_start_time
            return {
                "recommended_size": size,
                "reason": "Measurements exceed largest available size - recommending largest size",
                "checked_sizes": checked_sizes,
                "recommendation_time_seconds": round(rec_latency, 6),
                "comparison": {
                    "shoulder": {
                        "measured": shoulder,
                        "size_limit": size_measurements.get("shoulder"),
                        "fits": shoulder_fits
                    },
                    "chest": {
                        "measured": chest,
                        "size_limit": size_measurements.get("chest"),
                        "fits": chest_fits
                    },
                    "waist": {
                        "measured": waist,
                        "size_limit": size_measurements.get("waist"),
                        "fits": waist_fits
                    }
                }
            }
    
    # Fallback: recommend the largest size
    rec_end_time = time.time()
    rec_latency = rec_end_time - rec_start_time
    return {
        "recommended_size": size_order[-1],
        "reason": "Could not determine fit, recommending largest size",
        "checked_sizes": checked_sizes,
        "recommendation_time_seconds": round(rec_latency, 6),
        "comparison": {}
    }

def analyze_body_with_gemini(image_path, reference_height_cm):
    """
    Analyzes an image using Gemini-3-Pro-Preview to estimate body measurements.
    """
    
    # 1. Load the Image
    try:
        img = PIL.Image.open(image_path)
    except FileNotFoundError:
        print(f"Error: Image file '{image_path}' not found.")
        return None

    # 2. Define the Prompt (Universal & Gender Aware)
    prompt = f"""
    You are an expert Biometric AI.
    
    **TASK:**
    Analyze the image provided. Calculate body measurements based on the reference height.
    
    **INPUT CONTEXT:**
    - Reference Height: {reference_height_cm} cm
    
    **INSTRUCTIONS:**
    1. **Scan:** Use the reference height to calculate a pixel-to-cm ratio.
    2. **Classify:** Detect gender (Male/Female) FIRST - this is critical for accurate measurements.
    
    3. **GENDER-SPECIFIC MEASUREMENT GUIDELINES:**
    
       **FOR FEMALES:**
       - **Chest Circumference (BUST):** Measure around the FULLEST PART of the bust/breasts, typically at nipple level. This is the BUST measurement, NOT the ribcage. Include the full volume of the breasts in the measurement. The tape should go around the fullest point of the chest, usually where the breasts protrude the most.
       - **Waist:** Measure at the natural waist (narrowest point, usually above the belly button)
       - **Shoulder Width:** Horizontal distance between the two shoulder points (acromion to acromion)
       
       **FOR MALES:**
       - **Chest Circumference:** Measure around the chest at nipple/pectoral level, around the ribcage (thoracic measurement)
       - **Waist:** Measure at the natural waist or belt line
       - **Shoulder Width:** Horizontal distance between the two shoulder points (acromion to acromion)
    
    4. **Clothing Logic:** 
       - Identify garments (e.g., Shacket, Hoodie, Saree, Blouse, T-shirt).
       - If clothing is Loose/Oversized, apply a negative offset to estimate the body underneath.
       - If clothing is Tight/Fitted, measure directly but account for fabric thickness.
       - For females wearing bras or fitted tops, the bust measurement should reflect the actual body measurement, not the clothing size.
    
    5. **3D Estimation:** The image is 2D. You must calculate the CIRCUMFERENCE (full loop) for Chest/Waist based on frontal width and anatomical depth ratios.
       - For females: Chest = Bust circumference (fullest part including breast volume)
       - For males: Chest = Chest circumference (ribcage/thoracic measurement)
    
    **OUTPUT FORMAT:**
    Return ONLY valid JSON.
    
    {{
      "status": "success",
      "subject_analysis": {{
        "detected_gender": "Male/Female",
        "clothing_worn": "string",
        "fit_type": "Tight/Regular/Loose/Oversized"
      }},
      "measurements_cm": {{
        "shoulder_width": {{ "value": float, "type": "Linear" }},
        "chest_circumference": {{ "value": float, "note": "For females: Bust measurement at fullest part. For males: Chest at nipple level" }},
        "waist_circumference": {{ "value": float, "note": "Estimated 3D loop" }}
      }}
    }}
    """

    # 3. Initialize Model
    # We use generation_config to force JSON response type (supported in Pro models)
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        print(f"Sending request to {MODEL_NAME}... please wait.")
        
        # Record start time for LLM API call
        llm_start_time = time.time()
        
        response = model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Record end time and calculate latency
        llm_end_time = time.time()
        llm_latency = llm_end_time - llm_start_time
        
        # 4. Parse JSON and add timing information
        result = json.loads(response.text)
        result["llm_latency_seconds"] = round(llm_latency, 3)
        
        return result

    except Exception as e:
        print(f"\nAPI Error. Ensure you have access to '{MODEL_NAME}'.")
        print(f"Details: {e}")
        return None

# ------------------------------------------------------------------
# MAIN EXECUTION
# ------------------------------------------------------------------
if __name__ == "__main__":
    # --- USER INPUTS ---
    IMAGE_FILE = "C:/Users/user/Downloads/IMG-20260205-WA0009.jpg" # Make sure this file exists
    REAL_HEIGHT_CM = 170.18
    
    # Size Charts - Gender Specific
    SIZE_CHART_MALE = {
        "S": {
            "shoulder": 40.6,
            "chest": 96.5,
            "waist": 71.1
        },
        "M": {
            "shoulder": 43.2,
            "chest": 101.6,
            "waist": 76.2
        },
        "L": {
            "shoulder": 45.7,
            "chest": 106.7,
            "waist": 81.3
        },
        "XL": {
            "shoulder": 48.3,
            "chest": 111.8,
            "waist": 86.4
        },
        "XXL": {
            "shoulder": 50.8,
            "chest": 119.4,
            "waist": 91.4
        }
    }
    
    # Female Size Chart (using max values from ranges for fitting logic)
    SIZE_CHART_FEMALE = {
        "XS": {
            "shoulder": 34,
            "chest": 81,
            "waist": 66
        },
        "S": {
            "shoulder": 36,
            "chest": 86,
            "waist": 71
        },
        "M": {
            "shoulder": 37,
            "chest": 91,
            "waist": 76
        },
        "L": {
            "shoulder": 38,
            "chest": 97,
            "waist": 81
        },
        "XL": {
            "shoulder": 39,
            "chest": 102,
            "waist": 86
        },
        "XXL": {
            "shoulder": 41,
            "chest": 107,
            "waist": 91
        }
    }

    # Record overall start time
    overall_start_time = time.time()
    
    # Get measurements from LLM
    result = analyze_body_with_gemini(IMAGE_FILE, REAL_HEIGHT_CM)

    if result:
        print("\n--- GEMINI ANALYSIS RESULT ---")
        print(json.dumps(result, indent=2))
        
        # Determine which size chart to use based on detected gender
        detected_gender = result.get("subject_analysis", {}).get("detected_gender", "").lower()
        
        if "female" in detected_gender:
            size_chart = SIZE_CHART_FEMALE
            print(f"\n👩 Using FEMALE size chart (detected gender: {result.get('subject_analysis', {}).get('detected_gender', 'Unknown')})")
        else:
            size_chart = SIZE_CHART_MALE
            print(f"\n👨 Using MALE size chart (detected gender: {result.get('subject_analysis', {}).get('detected_gender', 'Unknown')})")
        
        # Get size recommendation
        recommendation = recommend_size(result, size_chart)
        
        # Record overall end time
        overall_end_time = time.time()
        overall_time = overall_end_time - overall_start_time
        
        if recommendation:
            print("\n" + "="*70)
            print("SIZE RECOMMENDATION")
            print("="*70)
            print(f"✅ Recommended Size: {recommendation['recommended_size']}")
            print(f"📝 Reason: {recommendation['reason']}")
            
            # Show all sizes that were checked
            if 'checked_sizes' in recommendation:
                print("\n🔍 Size Evaluation Process:")
                for checked in recommendation['checked_sizes']:
                    status = "✅ FITS" if checked['fits'] else "❌ Doesn't fit"
                    print(f"   {checked['size']}: {status}")
                    if not checked['fits']:
                        print(f"      Reason: {'; '.join(checked['reasons'])}")
            
            print("\n📊 Final Size Comparison:")
            
            comp = recommendation['comparison']
            if comp:
                meas = result["measurements_cm"]
                
                print(f"\n   Shoulder Width:")
                print(f"      Measured: {comp['shoulder']['measured']:.1f} cm")
                print(f"      Size Limit: {comp['shoulder']['size_limit']:.1f} cm")
                print(f"      Fits: {'✅ Yes' if comp['shoulder']['fits'] else '❌ No'}")
                
                print(f"\n   Chest Circumference:")
                print(f"      Measured: {comp['chest']['measured']:.1f} cm")
                print(f"      Size Limit: {comp['chest']['size_limit']:.1f} cm")
                print(f"      Fits: {'✅ Yes' if comp['chest']['fits'] else '❌ No'}")
                
                print(f"\n   Waist Circumference:")
                print(f"      Measured: {comp['waist']['measured']:.1f} cm")
                print(f"      Size Limit: {comp['waist']['size_limit']:.1f} cm")
                print(f"      Fits: {'✅ Yes' if comp['waist']['fits'] else '❌ No'}")
            
            # Display timing information
            print("\n⏱️  TIMING INFORMATION:")
            print("-" * 70)
            if 'llm_latency_seconds' in result:
                llm_time = result['llm_latency_seconds']
                print(f"   LLM API Call: {llm_time:.3f} seconds ({llm_time * 1000:.1f} ms)")
            
            if 'recommendation_time_seconds' in recommendation:
                rec_time = recommendation['recommendation_time_seconds']
                print(f"   Size Recommendation: {rec_time:.6f} seconds ({rec_time * 1000:.3f} ms)")
            
            print(f"   Total Execution Time: {overall_time:.3f} seconds ({overall_time * 1000:.1f} ms)")
            print("="*70)
            
            # Add recommendation and timing to result
            result["size_recommendation"] = recommendation
            result["total_execution_time_seconds"] = round(overall_time, 3)
    else:
        # Record overall end time even if LLM failed
        overall_end_time = time.time()
        overall_time = overall_end_time - overall_start_time
        print(f"\n⏱️  Total Execution Time: {overall_time:.3f} seconds ({overall_time * 1000:.1f} ms)")