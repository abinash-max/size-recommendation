# API Usage Examples

## Base URL
```
https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod
```

## Endpoints

### 1. Health Check
```bash
curl https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/health
```

### 2. Get Size Charts
```bash
curl https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/size-charts
```

### 3. Size Recommendation (Main Endpoint)

#### Using cURL (PowerShell)
```powershell
$uri = "https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/recommend"
$imagePath = "path/to/your/image.jpg"
$height = 170.5

$form = @{
    image = Get-Item -Path $imagePath
    height_cm = $height
}

Invoke-RestMethod -Uri $uri -Method Post -Form $form
```

#### Using cURL (Bash/Linux)
```bash
curl -X POST "https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/recommend" \
  -F "image=@/path/to/image.jpg" \
  -F "height_cm=170.5"
```

#### Using Python requests
```python
import requests

url = "https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/recommend"

# Prepare the form data
files = {
    'image': ('image.jpg', open('path/to/image.jpg', 'rb'), 'image/jpeg')
}
data = {
    'height_cm': 170.5
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

#### Using Python requests with custom size charts
```python
import requests
import json

url = "https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/recommend"

# Custom size charts
male_chart = {
    "S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1},
    "M": {"shoulder": 43.2, "chest": 101.6, "waist": 76.2},
    "L": {"shoulder": 45.7, "chest": 106.7, "waist": 81.3}
}

female_chart = {
    "XS": {"shoulder": 33, "chest": 76, "waist": 61},
    "S": {"shoulder": 34, "chest": 81, "waist": 66},
    "M": {"shoulder": 36, "chest": 86, "waist": 71}
}

files = {
    'image': ('image.jpg', open('path/to/image.jpg', 'rb'), 'image/jpeg')
}
data = {
    'height_cm': 170.5,
    'male_size_chart': json.dumps(male_chart),
    'female_size_chart': json.dumps(female_chart)
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

#### Using JavaScript/Fetch
```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]); // fileInput is an <input type="file">
formData.append('height_cm', 170.5);

// Optional: Add custom size charts
const maleChart = {
    "S": {shoulder: 40.6, chest: 96.5, waist: 71.1},
    "M": {shoulder: 43.2, chest: 101.6, waist: 76.2}
};
formData.append('male_size_chart', JSON.stringify(maleChart));

fetch('https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod/recommend', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

## Request Parameters

- **image** (required): Image file (JPEG, PNG, etc.)
- **height_cm** (required): Height in centimeters (float, e.g., 170.5)
- **male_size_chart** (optional): JSON string of male size chart
- **female_size_chart** (optional): JSON string of female size chart

## Response Format

```json
{
    "success": true,
    "message": "Size recommendation completed",
    "classifier_result": {
        "prediction": "recommended",
        "confidence": 0.95
    },
    "measurements": {
        "shoulder_width": 41.5,
        "chest_circumference": 93.2,
        "waist_circumference": 78.5
    },
    "size_recommendation": {
        "recommended_size": "M",
        "gender": "Male"
    },
    "timing": {
        "total_time_seconds": 2.5,
        "llm_latency_seconds": 2.1
    }
}
```

