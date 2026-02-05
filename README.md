# Size Recommendation API

A FastAPI-based service for body measurement analysis and size recommendation using AI.

## Features

- **Image Classification**: Checks if image is suitable for size recommendation
- **Body Measurement Analysis**: Uses Gemini AI to analyze body measurements
- **Size Recommendation**: Recommends clothing size based on measurements and gender-specific size charts
- **Gender Detection**: Automatically detects gender and uses appropriate size chart

## Project Structure

```
size-recommendation/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and size charts
│   ├── classifier.py        # Image recommendation classifier
│   ├── llm_analyzer.py     # Gemini AI body measurement analyzer
│   └── size_recommender.py  # Size recommendation logic
├── requirements.txt
└── README.md
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export GOOGLE_API_KEY="your-api-key"
export CHECKPOINT_PATH="path/to/best_model.pth"
```

## Usage

### Run the API server:

```bash
python -m app.main
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### API Endpoints

#### 1. Health Check
```bash
GET /health
```

#### 2. Get Size Charts
```bash
GET /size-charts
```

#### 3. Get Size Recommendation
```bash
POST /recommend
Content-Type: multipart/form-data

Parameters:
- image: Image file (required)
- height_cm: Height in centimeters (required)
- male_size_chart: JSON string of male size chart (optional)
- female_size_chart: JSON string of female size chart (optional)
```

**Size Chart Format:**
```json
{
  "S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1},
  "M": {"shoulder": 43.2, "chest": 101.6, "waist": 76.2},
  "L": {"shoulder": 45.7, "chest": 106.7, "waist": 81.3}
}
```

**Example using curl (with default charts):**
```bash
curl -X POST "http://127.0.0.1:8000/recommend" \
  -F "image=@path/to/image.jpg" \
  -F "height_cm=170.0"
```

**Example using curl (with custom size charts):**
```bash
curl -X POST "http://127.0.0.1:8000/recommend" \
  -F "image=@path/to/image.jpg" \
  -F "height_cm=170.0" \
  -F 'male_size_chart={"S":{"shoulder":40.6,"chest":96.5,"waist":71.1},"M":{"shoulder":43.2,"chest":101.6,"waist":76.2}}' \
  -F 'female_size_chart={"XS":{"shoulder":34,"chest":81,"waist":66},"S":{"shoulder":36,"chest":86,"waist":71}}'
```

**Note:** If size charts are not provided, the API will use default size charts from the configuration.

## Response Format

```json
{
  "success": true,
  "message": "Size recommendation completed successfully",
  "classifier_result": {
    "is_recommended": true,
    "confidence": 0.95,
    "details": {...}
  },
  "measurements": {
    "shoulder_width": 42.5,
    "chest_circumference": 95.2,
    "waist_circumference": 78.3,
    "subject_analysis": {...}
  },
  "size_recommendation": {
    "recommended_size": "M",
    "reason": "All measurements fit within this size",
    "chart_used": "Male",
    "comparison": {...}
  },
  "timing": {
    "classifier_time": 0.123,
    "llm_time": 2.345,
    "recommendation_time": 0.000123,
    "total_time": 2.468
  }
}
```

## Configuration

Edit `app/config.py` to modify:
- API keys
- Model paths
- Size charts
- Other configuration options

