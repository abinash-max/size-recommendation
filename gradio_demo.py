import os
import json
import time
import gradio as gr
import google.generativeai as genai
import PIL.Image

# Import functions from test.py
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBeUFgh4pLxLY6xxuqGNi3Fr-w1_NEBpTI")
# MODEL_NAME = "gemini-3-flash-preview"
MODEL_NAME = "gemini-3-pro-preview"
genai.configure(api_key=GOOGLE_API_KEY)

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

# ------------------------------------------------------------------
# SIZE RECOMMENDATION FUNCTION
# ------------------------------------------------------------------
def recommend_size(measurements, size_chart):
    """Recommends a size based on body measurements and size chart."""
    rec_start_time = time.time()
    
    if not measurements or "measurements_cm" not in measurements:
        return None
    
    meas = measurements["measurements_cm"]
    shoulder = meas.get("shoulder_width", {}).get("value", 0)
    chest = meas.get("chest_circumference", {}).get("value", 0)
    waist = meas.get("waist_circumference", {}).get("value", 0)
    
    size_order = list(size_chart.keys())
    checked_sizes = []
    
    for i, size in enumerate(size_order):
        size_measurements = size_chart[size]
        
        shoulder_fits = shoulder <= size_measurements.get("shoulder", float('inf'))
        chest_fits = chest <= size_measurements.get("chest", float('inf'))
        waist_fits = waist <= size_measurements.get("waist", float('inf'))
        
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
    
    rec_end_time = time.time()
    rec_latency = rec_end_time - rec_start_time
    return {
        "recommended_size": size_order[-1],
        "reason": "Could not determine fit, recommending largest size",
        "checked_sizes": checked_sizes,
        "recommendation_time_seconds": round(rec_latency, 6),
        "comparison": {}
    }

# ------------------------------------------------------------------
# GEMINI ANALYSIS FUNCTION
# ------------------------------------------------------------------
def analyze_body_with_gemini(image_path, reference_height_cm):
    """Analyzes an image using Gemini to estimate body measurements."""
    try:
        img = PIL.Image.open(image_path)
    except FileNotFoundError:
        return None

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

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        llm_start_time = time.time()
        
        response = model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        
        llm_end_time = time.time()
        llm_latency = llm_end_time - llm_start_time
        
        result = json.loads(response.text)
        result["llm_latency_seconds"] = round(llm_latency, 3)
        
        return result

    except Exception as e:
        return {"error": str(e)}

# ------------------------------------------------------------------
# GRADIO INTERFACE FUNCTION
# ------------------------------------------------------------------
def process_image(image, height_cm):
    """Main function for Gradio interface."""
    if image is None:
        return "❌ Please upload an image.", "", "", ""
    
    if height_cm is None or height_cm <= 0:
        return "❌ Please enter a valid height (in cm).", "", "", ""
    
    overall_start_time = time.time()
    
    # Save uploaded image temporarily
    temp_path = "temp_uploaded_image.jpg"
    image.save(temp_path)
    
    try:
        # Get measurements from LLM
        result = analyze_body_with_gemini(temp_path, height_cm)
        
        if result and "error" not in result:
            # Determine which size chart to use
            detected_gender = result.get("subject_analysis", {}).get("detected_gender", "").lower()
            
            if "female" in detected_gender:
                size_chart = SIZE_CHART_FEMALE
                chart_name = "Female"
            else:
                size_chart = SIZE_CHART_MALE
                chart_name = "Male"
            
            # Get size recommendation
            recommendation = recommend_size(result, size_chart)
            
            overall_end_time = time.time()
            overall_time = overall_end_time - overall_start_time
            
            # Format results
            measurements_text = f"""
**Body Measurements:**
- Shoulder Width: {result['measurements_cm']['shoulder_width']['value']:.1f} cm
- Chest Circumference: {result['measurements_cm']['chest_circumference']['value']:.1f} cm
- Waist Circumference: {result['measurements_cm']['waist_circumference']['value']:.1f} cm

**Subject Analysis:**
- Gender: {result['subject_analysis']['detected_gender']}
- Clothing: {result['subject_analysis']['clothing_worn']}
- Fit Type: {result['subject_analysis']['fit_type']}
"""
            
            if recommendation:
                recommendation_text = f"""
**Recommended Size: {recommendation['recommended_size']}** ({chart_name} Chart)

**Reason:** {recommendation['reason']}

**Size Comparison:**
- Shoulder: {recommendation['comparison']['shoulder']['measured']:.1f} cm (Limit: {recommendation['comparison']['shoulder']['size_limit']:.1f} cm) {'✅' if recommendation['comparison']['shoulder']['fits'] else '❌'}
- Chest: {recommendation['comparison']['chest']['measured']:.1f} cm (Limit: {recommendation['comparison']['chest']['size_limit']:.1f} cm) {'✅' if recommendation['comparison']['chest']['fits'] else '❌'}
- Waist: {recommendation['comparison']['waist']['measured']:.1f} cm (Limit: {recommendation['comparison']['waist']['size_limit']:.1f} cm) {'✅' if recommendation['comparison']['waist']['fits'] else '❌'}
"""
            else:
                recommendation_text = "❌ Could not determine size recommendation."
            
            timing_text = f"""
**Timing Information:**
- LLM API Call: {result.get('llm_latency_seconds', 0):.3f} seconds
- Size Recommendation: {recommendation.get('recommendation_time_seconds', 0):.6f} seconds
- Total Time: {overall_time:.3f} seconds
"""
            
            # Format size chart display
            chart_text = f"**{chart_name} Size Chart:**\n\n"
            chart_text += "| Size | Shoulder (cm) | Chest (cm) | Waist (cm) |\n"
            chart_text += "|------|---------------|------------|------------|\n"
            for size, values in size_chart.items():
                chart_text += f"| {size} | {values['shoulder']} | {values['chest']} | {values['waist']} |\n"
            
            return measurements_text, recommendation_text, timing_text, chart_text
            
        else:
            error_msg = result.get("error", "Unknown error occurred") if result else "Failed to get analysis result"
            return f"❌ Error: {error_msg}", "", "", ""
    
    except Exception as e:
        return f"❌ Error processing image: {str(e)}", "", "", ""
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ------------------------------------------------------------------
# GRADIO INTERFACE
# ------------------------------------------------------------------
def create_interface():
    with gr.Blocks(title="Size Recommendation System", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 👔 Size Recommendation System")
        gr.Markdown("Upload an image and enter height to get body measurements and size recommendation.")
        
        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(
                    type="pil",
                    label="Upload Image",
                    height=400
                )
                height_input = gr.Number(
                    label="Height (cm)",
                    value=170.0,
                    minimum=100,
                    maximum=250,
                    step=0.1
                )
                submit_btn = gr.Button("Analyze & Recommend Size", variant="primary", size="lg")
            
            with gr.Column(scale=1):
                measurements_output = gr.Markdown(label="Body Measurements")
                recommendation_output = gr.Markdown(label="Size Recommendation")
                timing_output = gr.Markdown(label="Timing Information")
        
        with gr.Row():
            size_chart_output = gr.Markdown(label="Size Chart (Default)")
        
        # Display default size charts
        default_charts = """
## Default Size Charts

### Male Size Chart
| Size | Shoulder (cm) | Chest (cm) | Waist (cm) |
|------|---------------|------------|------------|
| S | 40.6 | 96.5 | 71.1 |
| M | 43.2 | 101.6 | 76.2 |
| L | 45.7 | 106.7 | 81.3 |
| XL | 48.3 | 111.8 | 86.4 |
| XXL | 50.8 | 119.4 | 91.4 |

### Female Size Chart
| Size | Shoulder (cm) | Chest (cm) | Waist (cm) |
|------|---------------|------------|------------|
| XS | 34 | 81 | 66 |
| S | 36 | 86 | 71 |
| M | 37 | 91 | 76 |
| L | 38 | 97 | 81 |
| XL | 39 | 102 | 86 |
| XXL | 41 | 107 | 91 |
"""
        size_chart_output.value = default_charts
        
        submit_btn.click(
            fn=process_image,
            inputs=[image_input, height_input],
            outputs=[measurements_output, recommendation_output, timing_output, size_chart_output]
        )
        
        gr.Markdown("---")
        gr.Markdown("**Note:** The system automatically selects the appropriate size chart based on detected gender.")
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860)

