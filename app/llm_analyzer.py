import json
import time
import google.genai as genai
import PIL.Image
from app.config import GOOGLE_API_KEY, MODEL_NAME

# Configure the SDK (new google.genai API)
client = genai.Client(api_key=GOOGLE_API_KEY)


def analyze_body_with_gemini(image_path, reference_height_cm):
    """
    Analyzes an image using Gemini to estimate body measurements.
    """
    import os
    
    # Verify file exists and is readable
    if not os.path.exists(image_path):
        return {"error": f"Image file '{image_path}' not found."}
    
    if os.path.getsize(image_path) == 0:
        return {"error": f"Image file '{image_path}' is empty."}
    
    try:
        # Try to open and verify the image
        img = PIL.Image.open(image_path)
        img.verify()  # Verify it's a valid image
        
        # Reopen after verify (verify closes the file)
        img = PIL.Image.open(image_path)
        img = img.convert("RGB")  # Ensure RGB format
    except PIL.UnidentifiedImageError:
        return {"error": f"Cannot identify image file '{image_path}'. File may be corrupted or in an unsupported format."}
    except Exception as e:
        return {"error": f"Error opening image file '{image_path}': {str(e)}"}

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
        llm_start_time = time.time()
        
        # New google.genai API
        # Convert PIL Image to bytes for the API
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        # Generate content using new API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_bytes
                            }
                        }
                    ]
                }
            ],
            config={
                "response_mime_type": "application/json"
            }
        )
        
        llm_end_time = time.time()
        llm_latency = llm_end_time - llm_start_time
        
        # Extract text from response
        # The response structure may vary, try different attributes
        if hasattr(response, 'text'):
            response_text = response.text
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            response_text = response.candidates[0].content.parts[0].text
        else:
            response_text = str(response)
        
        result = json.loads(response_text)
        result["llm_latency_seconds"] = round(llm_latency, 3)
        
        return result

    except Exception as e:
        import traceback
        return {"error": f"API Error: {str(e)}", "traceback": traceback.format_exc()}

