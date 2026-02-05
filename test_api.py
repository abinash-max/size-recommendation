"""
Test script for the Size Recommendation API
"""
import requests
import json
import os

# ============================================
# CONFIGURATION - Update these paths as needed
# ============================================
API_URL = "https://979vhqf5ok.execute-api.ap-south-1.amazonaws.com/prod"

# Default test image path (update this to your image path)
IMAGE_PATH = "C:/Users/user/Downloads/IMG-20260205-WA0010.jpg"  # Change this to your image file path
HEIGHT_CM = 170  # Default height in cm

# Optional: Custom size charts
MALE_SIZE_CHART = {
    "S": {"shoulder": 40.6, "chest": 96.5, "waist": 71.1},
    "M": {"shoulder": 43.2, "chest": 101.6, "waist": 76.2},
    "L": {"shoulder": 45.7, "chest": 106.7, "waist": 81.3},
    "XL": {"shoulder": 48.3, "chest": 111.8, "waist": 86.4},
    "XXL": {"shoulder": 50.8, "chest": 119.4, "waist": 91.4}
}

FEMALE_SIZE_CHART = {
    "XS": {"shoulder": 33, "chest": 76, "waist": 61},
    "S": {"shoulder": 34, "chest": 81, "waist": 66},
    "M": {"shoulder": 36, "chest": 86, "waist": 71},
    "L": {"shoulder": 37, "chest": 91, "waist": 76},
    "XL": {"shoulder": 38, "chest": 97, "waist": 81},
    "XXL": {"shoulder": 39, "chest": 102, "waist": 86}
}

# Set to True to use custom size charts, False to use API defaults
USE_CUSTOM_SIZE_CHARTS = False


def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing health endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}\n")
    except Exception as e:
        print(f"Error: {e}\n")


def test_size_charts():
    """Test size charts endpoint"""
    print("=" * 60)
    print("Testing size charts endpoint...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_URL}/size-charts")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")


def test_recommend(image_path, height_cm, male_chart=None, female_chart=None):
    """Test recommendation endpoint"""
    print("=" * 60)
    print("Testing recommendation endpoint...")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Height: {height_cm} cm")
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"ERROR: Image file not found: {image_path}")
        print("Please update IMAGE_PATH in the script.\n")
        return
    
    # Get file extension for proper content type
    ext = os.path.splitext(image_path)[1].lower()
    content_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    content_type = content_type_map.get(ext, 'image/jpeg')
    
    files = {
        'image': (os.path.basename(image_path), open(image_path, 'rb'), content_type)
    }
    data = {
        'height_cm': height_cm
    }
    
    if male_chart:
        data['male_size_chart'] = json.dumps(male_chart)
        print("Using custom male size chart")
    if female_chart:
        data['female_size_chart'] = json.dumps(female_chart)
        print("Using custom female size chart")
    
    print()
    
    try:
        print("Sending request...")
        response = requests.post(f"{API_URL}/recommend", files=files, data=data, timeout=300)
        print(f"Status: {response.status_code}")
        print("\nResponse:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out (this can happen with large images or slow LLM responses)")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        files['image'][1].close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Size Recommendation API Test Script")
    print("=" * 60 + "\n")
    
    # Test health
    test_health()
    
    # Test size charts
    test_size_charts()
    
    # Test recommendation
    if USE_CUSTOM_SIZE_CHARTS:
        test_recommend(IMAGE_PATH, HEIGHT_CM, MALE_SIZE_CHART, FEMALE_SIZE_CHART)
    else:
        test_recommend(IMAGE_PATH, HEIGHT_CM)
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)

