import os
import time
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from tempfile import NamedTemporaryFile
from app.classifier import check_image_recommendation
from app.llm_analyzer import analyze_body_with_gemini
from app.size_recommender import recommend_size, get_size_chart_by_gender
from app.config import SIZE_CHART_MALE, SIZE_CHART_FEMALE

app = FastAPI(
    title="Size Recommendation API",
    description="API for body measurement analysis and size recommendation",
    version="1.0.0"
)

# Add CORS middleware for API Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SizeChartInput(BaseModel):
    """Size chart structure for a single size"""
    shoulder: float
    chest: float
    waist: float


class SizeRecommendationRequest(BaseModel):
    """Request body for size recommendation with custom size charts"""
    male_size_chart: Optional[Dict[str, SizeChartInput]] = None
    female_size_chart: Optional[Dict[str, SizeChartInput]] = None


class SizeRecommendationResponse(BaseModel):
    success: bool
    message: str
    classifier_result: Optional[dict] = None
    measurements: Optional[dict] = None
    size_recommendation: Optional[dict] = None
    timing: Optional[dict] = None
    error: Optional[str] = None
    size_charts_used: Optional[dict] = None


@app.get("/")
async def root():
    return {
        "message": "Size Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "/recommend": "POST - Upload image and get size recommendation",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    """Explicit OpenAPI schema endpoint for API Gateway compatibility"""
    return app.openapi()


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    """Custom Swagger UI HTML that works with API Gateway"""
    from fastapi.responses import HTMLResponse
    
    # Use relative path that will work with API Gateway /prod/ prefix
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Size Recommendation API - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
        <style>
            html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
            *, *:before, *:after { box-sizing: inherit; }
            body { margin:0; padding:0; background: #fafafa; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                // Get current path and construct openapi.json URL relative to current path
                const currentPath = window.location.pathname;
                const basePath = currentPath.replace(/\/docs.*$/, '');
                const openApiUrl = basePath + '/openapi.json';
                
                const ui = SwaggerUIBundle({
                    url: openApiUrl,
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Custom ReDoc HTML that works with API Gateway"""
    from fastapi.responses import HTMLResponse
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Size Recommendation API - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <div id="redoc-container"></div>
        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
        <script>
            // Get current path and construct openapi.json URL relative to current path
            const currentPath = window.location.pathname;
            const basePath = currentPath.replace(/\/redoc.*$/, '');
            const openApiUrl = basePath + '/openapi.json';
            
            Redoc.init(openApiUrl, {
                scrollYOffset: 0,
                hideDownloadButton: false,
                expandResponses: '200,201',
                requiredPropsFirst: true
            }, document.getElementById('redoc-container'));
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/size-charts")
async def get_size_charts():
    """Get available size charts."""
    return {
        "male": SIZE_CHART_MALE,
        "female": SIZE_CHART_FEMALE
    }


def parse_size_chart_json(chart_json_str: Optional[str]) -> Optional[Dict[str, Dict[str, float]]]:
    """Parse size chart JSON string into dictionary."""
    if not chart_json_str:
        return None
    try:
        chart_dict = json.loads(chart_json_str)
        # Convert to the format expected by recommend_size function
        # Input: {"S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1}, ...}
        # Output: {"S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1}, ...}
        return chart_dict
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format for size chart: {str(e)}")


@app.post("/recommend", response_model=SizeRecommendationResponse)
async def recommend_size_endpoint(
    image: UploadFile = File(...),
    height_cm: float = Form(...),
    male_size_chart: Optional[str] = Form(None, description="JSON string of male size chart. Format: {\"S\": {\"shoulder\": 40.6, \"chest\": 96.5, \"waist\": 71.1}, ...}"),
    female_size_chart: Optional[str] = Form(None, description="JSON string of female size chart. Format: {\"XS\": {\"shoulder\": 34, \"chest\": 81, \"waist\": 66}, ...}")
):
    """
    Main endpoint for size recommendation.
    
    Process:
    1. First checks if image is recommended using classifier
    2. If recommended, proceeds with LLM analysis
    3. Returns size recommendation based on measurements
    
    Size Charts:
    - If provided, custom size charts will be used
    - If not provided, default size charts from config will be used
    - Format: JSON string with size names as keys and measurements as values
    - Example: {"S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1}, "M": {...}}
    """
    overall_start_time = time.time()
    
    # Validate inputs
    if height_cm <= 0 or height_cm > 300:
        raise HTTPException(status_code=400, detail="Height must be between 0 and 300 cm")
    
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Parse size charts (use provided or default)
    male_chart = parse_size_chart_json(male_size_chart) or SIZE_CHART_MALE
    female_chart = parse_size_chart_json(female_size_chart) or SIZE_CHART_FEMALE
    
    # Validate size charts structure
    try:
        for chart_name, chart in [("male", male_chart), ("female", female_chart)]:
            for size, measurements in chart.items():
                if not isinstance(measurements, dict):
                    raise ValueError(f"Invalid format for {chart_name} size chart: {size}")
                required_keys = ["shoulder", "chest", "waist"]
                for key in required_keys:
                    if key not in measurements:
                        raise ValueError(f"Missing '{key}' in {chart_name} size '{size}'")
                    if not isinstance(measurements[key], (int, float)):
                        raise ValueError(f"'{key}' in {chart_name} size '{size}' must be a number")
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid size chart format: {str(e)}")
    
    # Save uploaded file temporarily
    temp_file = None
    try:
        # Create temporary file
        suffix = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        content = await image.read()
        
        # Ensure we have content
        if not content:
            raise HTTPException(status_code=400, detail="Image file is empty")
        
        # Use /tmp directory on Lambda, system temp on local
        import tempfile
        temp_dir = "/tmp" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else tempfile.gettempdir()
        
        # Write to temporary file with proper flushing
        import uuid
        temp_file = os.path.join(temp_dir, f"upload_{uuid.uuid4().hex}{suffix}")
        
        with open(temp_file, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Verify file exists and has content
        if not os.path.exists(temp_file):
            raise HTTPException(status_code=400, detail="Failed to save image file")
        
        file_size = os.path.getsize(temp_file)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Image file is empty after saving")
        
        if file_size != len(content):
            raise HTTPException(status_code=400, detail=f"File size mismatch: expected {len(content)}, got {file_size}")
        
        # Step 1: Check if image is recommended
        is_recommended, confidence, classifier_details = check_image_recommendation(temp_file)
        
        if not is_recommended:
            return SizeRecommendationResponse(
                success=False,
                message="Image is not recommended for size recommendation",
                classifier_result={
                    "is_recommended": False,
                    "confidence": confidence,
                    "details": classifier_details
                },
                error="Image failed classifier check"
            )
        
        # Step 2: If recommended, proceed with LLM analysis
        result = analyze_body_with_gemini(temp_file, height_cm)
        
        if "error" in result:
            return SizeRecommendationResponse(
                success=False,
                message="Error during LLM analysis",
                classifier_result={
                    "is_recommended": True,
                    "confidence": confidence,
                    "details": classifier_details
                },
                error=result["error"]
            )
        
        # Step 3: Get size recommendation using provided or default charts
        detected_gender = result.get("subject_analysis", {}).get("detected_gender", "")
        
        # Use custom charts if provided, otherwise use defaults
        if "female" in detected_gender.lower():
            size_chart = female_chart
            chart_name = "Female"
        else:
            size_chart = male_chart
            chart_name = "Male"
        
        recommendation = recommend_size(result, size_chart)
        
        overall_end_time = time.time()
        overall_time = overall_end_time - overall_start_time
        
        # Prepare response
        return SizeRecommendationResponse(
            success=True,
            message="Size recommendation completed successfully",
            classifier_result={
                "is_recommended": True,
                "confidence": confidence,
                "details": classifier_details
            },
            measurements={
                "shoulder_width": result["measurements_cm"]["shoulder_width"]["value"],
                "chest_circumference": result["measurements_cm"]["chest_circumference"]["value"],
                "waist_circumference": result["measurements_cm"]["waist_circumference"]["value"],
                "subject_analysis": result["subject_analysis"]
            },
            size_recommendation={
                "recommended_size": recommendation["recommended_size"],
                "reason": recommendation["reason"],
                "chart_used": chart_name,
                "comparison": recommendation["comparison"]
            },
            timing={
                "classifier_time": classifier_details.get("inference_time", 0),
                "llm_time": result.get("llm_latency_seconds", 0),
                "recommendation_time": recommendation.get("recommendation_time_seconds", 0),
                "total_time": round(overall_time, 3)
            },
            size_charts_used={
                "male": male_chart if chart_name == "Male" else None,
                "female": female_chart if chart_name == "Female" else None,
                "chart_used": chart_name
            }
        )
    
    except Exception as e:
        return SizeRecommendationResponse(
            success=False,
            message="Error processing request",
            error=str(e)
        )
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

