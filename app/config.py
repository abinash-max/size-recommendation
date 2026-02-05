import os

# Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBeUFgh4pLxLY6xxuqGNi3Fr-w1_NEBpTI")
MODEL_NAME = "gemini-3-flash-preview"

# Classifier Configuration
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "C:/Users/user/Downloads/best_model-size-recommendation")
CLASSIFIER_MODEL_NAME = "fastvit_s12.apple_dist_in1k"
IMG_SIZE = 224
DEVICE = "cpu"  # Will be converted to torch.device in classifier.py
CLASS_NAMES = ["not-recommended", "recommended"]

# Size Charts
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

