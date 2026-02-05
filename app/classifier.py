import os
from PIL import Image
from datetime import datetime
from app.config import CHECKPOINT_PATH, CLASSIFIER_MODEL_NAME, IMG_SIZE, CLASS_NAMES

# Lazy imports for torch (only when classifier is actually used)
def _import_torch():
    """Lazy import torch dependencies"""
    try:
        import torch
        import timm
        from torchvision import transforms
        return torch, timm, transforms
    except ImportError as e:
        raise ImportError(f"PyTorch dependencies not available: {e}. Install torch, torchvision, and timm.")

# Device configuration (will be set when torch is imported)
DEVICE = None  # Will be set to torch.device("cpu") when torch is imported

# Check if running on AWS Lambda
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Global variable to cache the model (persists across invocations in same container)
_cached_model = None
_cached_checkpoint_path = None

# For Lambda, download model from S3 if needed
def get_checkpoint_path():
    """
    Get checkpoint path, downloading from S3 if on Lambda.
    Lambda /tmp directory persists across invocations in the same container,
    so we can cache the downloaded model.
    """
    if IS_LAMBDA and CHECKPOINT_PATH.startswith("s3://"):
        import boto3
        s3 = boto3.client('s3')
        # Parse S3 path: s3://bucket/key
        path_parts = CHECKPOINT_PATH.replace("s3://", "").split("/", 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ""
        local_path = f"/tmp/{os.path.basename(key)}"
        
        # Download if not exists (cached in /tmp across invocations)
        if not os.path.exists(local_path):
            print(f"[Lambda] Downloading model from S3: s3://{bucket}/{key}")
            s3.download_file(bucket, key, local_path)
            print(f"[Lambda] Model downloaded to: {local_path}")
        else:
            print(f"[Lambda] Using cached model from: {local_path}")
        
        return local_path
    return CHECKPOINT_PATH


def get_or_load_model():
    """
    Get or load the classifier model.
    On Lambda, this caches the model in memory to avoid reloading on every invocation.
    """
    global _cached_model, _cached_checkpoint_path, DEVICE
    
    # Lazy import torch
    torch, timm, _ = _import_torch()
    if DEVICE is None:
        DEVICE = torch.device("cpu")
    
    checkpoint_path = get_checkpoint_path()
    
    # If model is already loaded and checkpoint hasn't changed, return cached model
    if _cached_model is not None and _cached_checkpoint_path == checkpoint_path:
        return _cached_model
    
    # Load model
    if not os.path.exists(checkpoint_path):
        return None
    
    print(f"[Classifier] Loading model from: {checkpoint_path}")
    model = timm.create_model(
        CLASSIFIER_MODEL_NAME,
        pretrained=False,
        num_classes=2
    )
    
    model.load_state_dict(
        torch.load(checkpoint_path, map_location=DEVICE)
    )
    model.to(DEVICE)
    model.eval()
    
    # Cache the model
    _cached_model = model
    _cached_checkpoint_path = checkpoint_path
    
    print(f"[Classifier] Model loaded and cached successfully")
    return model


def _get_transforms():
    """Get transforms (lazy import)"""
    _, _, transforms = _import_torch()
    from torchvision.transforms import InterpolationMode
    
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    
    return transforms.Compose([
        transforms.Resize(
            (IMG_SIZE, IMG_SIZE),
            interpolation=InterpolationMode.BICUBIC
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean, std)
    ])


def load_classifier_image(img_path):
    """Load and preprocess image for classifier."""
    import os
    
    # Verify file exists
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Image file not found: {img_path}")
    
    if os.path.getsize(img_path) == 0:
        raise ValueError(f"Image file is empty: {img_path}")
    
    try:
        val_transforms = _get_transforms()
        img = Image.open(img_path)
        img.verify()  # Verify it's a valid image
        
        # Reopen after verify (verify closes the file)
        img = Image.open(img_path)
        img = img.convert("RGB")
        img = val_transforms(img)
        return img.unsqueeze(0)  # (1, C, H, W)
    except Exception as e:
        raise ValueError(f"Error loading image '{img_path}': {str(e)}")


def check_image_recommendation(image_path):
    """
    Checks if the image is recommended using the classifier model.
    Returns: (is_recommended: bool, confidence: float, details: dict)
    """
    try:
        # Lazy import torch
        torch, _, _ = _import_torch()
        global DEVICE
        if DEVICE is None:
            DEVICE = torch.device("cpu")
    except ImportError as e:
        # PyTorch not available, skip classifier check
        return True, 1.0, {
            "status": "torch_not_available",
            "bypassed": True,
            "message": f"PyTorch not available: {str(e)}. Proceeding without classifier check."
        }
    
    # Get checkpoint path (download from S3 if on Lambda)
    checkpoint_path = get_checkpoint_path()
    
    # Check if checkpoint exists
    if not os.path.exists(checkpoint_path):
        return True, 1.0, {
            "status": "checkpoint_not_found",
            "bypassed": True,
            "message": f"Classifier checkpoint not found: {checkpoint_path}. Proceeding without classifier check."
        }
    
    try:
        # Load or get cached model
        model = get_or_load_model()
        
        if model is None:
            return True, 1.0, {
                "status": "checkpoint_not_found",
                "bypassed": True,
                "message": f"Classifier checkpoint not found: {checkpoint_path}. Proceeding without classifier check."
            }
        
        # Process image
        inference_start = datetime.now()
        
        # Load and preprocess image
        image_tensor = load_classifier_image(image_path).to(DEVICE)
        
        # Run inference
        with torch.no_grad():
            outputs = model(image_tensor)
        
        # Get probabilities
        probs = torch.softmax(outputs, dim=1)[0]
        
        # Get prediction
        conf, pred_idx = torch.max(probs, 0)
        
        pred_class = CLASS_NAMES[pred_idx.item()]
        pred_confidence = conf.item()
        
        # Get all class probabilities
        not_rec_prob = probs[0].item()
        rec_prob = probs[1].item()
        
        inference_end = datetime.now()
        inference_time = (inference_end - inference_start).total_seconds()
        
        is_recommended = (pred_class == "recommended")
        details = {
            "prediction": pred_class,
            "confidence": pred_confidence,
            "not_recommended_prob": not_rec_prob,
            "recommended_prob": rec_prob,
            "inference_time": inference_time,
            "status": "success"
        }
        
        return is_recommended, pred_confidence, details
        
    except Exception as e:
        return True, 1.0, {
            "status": "error",
            "error": str(e),
            "bypassed": True,
            "message": f"Error in classifier: {str(e)}. Proceeding without classifier check."
        }

