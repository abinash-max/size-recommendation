import cv2
import math
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ==========================================
#      USER CONFIGURATION (EDIT HERE)
# ==========================================

# 1. Paste your image path here (keep the quotes)
#    - Use forward slashes '/' or double backslashes '\\' for paths.
#    - Example: "C:/Users/Name/Downloads/photo.jpg"
IMAGE_PATH = "C:/Users/user/Downloads/20251208_074050.jpg" 

# 2. Enter the real world height of the person in Centimeters
REAL_HEIGHT_CM = 162.56

# ==========================================

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points (x, y)."""
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def main():
    # 1. Check if file exists
    if not os.path.exists(IMAGE_PATH):
        print(f"\n[ERROR] File not found: {IMAGE_PATH}")
        print("Please check the path in the 'USER CONFIGURATION' section of the script.\n")
        return

    # 2. Initialize MediaPipe Pose (new API for 0.10+)
    # Download model if not exists
    import urllib.request
    model_path = "pose_landmarker_lite.task"
    if not os.path.exists(model_path):
        print("Downloading pose landmarker model (first time only)...")
        model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
        urllib.request.urlretrieve(model_url, model_path)
        print("Model downloaded successfully!")
    
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        num_poses=1
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    # 3. Load the image
    image = cv2.imread(IMAGE_PATH)
    if image is None:
        print("[ERROR] Could not open the image file. Check file format/integrity.")
        return

    # Convert to RGB (MediaPipe needs RGB)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
    
    # 4. Process the image
    detection_result = detector.detect(image_mp)

    if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
        print("[ERROR] No human detected. Please use a clear full-body photo.")
        return

    # 5. Extract Landmarks (new API structure)
    landmarks = detection_result.pose_landmarks[0]
    h, w, _ = image.shape

    # Helper function to get pixel coordinates
    def get_point(landmark_idx):
        return (int(landmarks[landmark_idx].x * w), int(landmarks[landmark_idx].y * h))

    # Get key body points
    nose = get_point(0)                 # Nose (approx top anchor)
    l_shoulder = get_point(11)          # Left Shoulder
    r_shoulder = get_point(12)          # Right Shoulder
    l_hip = get_point(23)               # Left Hip
    r_hip = get_point(24)               # Right Hip
    l_ankle = get_point(27)             # Left Ankle
    r_ankle = get_point(28)             # Right Ankle

    # 6. Calculate Height in Pixels
    # Find midpoint between ankles
    mid_ankle = ((l_ankle[0] + r_ankle[0]) // 2, (l_ankle[1] + r_ankle[1]) // 2)
    
    # Calculate distance from Nose to Ankles
    pixel_body_height = calculate_distance(nose, mid_ankle)
    
    # ADJUSTMENT: Add ~12% for the head (forehead/hair) above the nose
    pixel_total_height = pixel_body_height * 1.12
    
    # 7. Calculate Scale Ratio (cm per pixel)
    cm_per_pixel = REAL_HEIGHT_CM / pixel_total_height

    # 8. Calculate Widths
    
    # --- Shoulder Width ---
    pixel_shoulder = calculate_distance(l_shoulder, r_shoulder)
    real_shoulder = pixel_shoulder * cm_per_pixel

    # --- Waist/Hip Width ---
    pixel_hip = calculate_distance(l_hip, r_hip)
    real_hip = pixel_hip * cm_per_pixel

    # --- Chest Width (Estimated) ---
    # We estimate chest position at 15% down from shoulders to hips
    l_chest = (int(l_shoulder[0] + (l_hip[0] - l_shoulder[0]) * 0.15), 
               int(l_shoulder[1] + (l_hip[1] - l_shoulder[1]) * 0.15))
    r_chest = (int(r_shoulder[0] + (r_hip[0] - r_shoulder[0]) * 0.15), 
               int(r_shoulder[1] + (r_hip[1] - r_shoulder[1]) * 0.15))
    
    pixel_chest = calculate_distance(l_chest, r_chest)
    real_chest = pixel_chest * cm_per_pixel

    # 9. Print Results
    print(f"\n--- MEASUREMENTS (Based on Height: {REAL_HEIGHT_CM}cm) ---")
    print(f"Shoulder Width : {real_shoulder:.2f} cm")
    print(f"Chest Width    : {real_chest:.2f} cm")
    print(f"Waist Width    : {real_hip:.2f} cm")
    print("--------------------------------------------------")

    # 10. Visualize on Image
    # Draw Lines
    cv2.line(image, l_shoulder, r_shoulder, (0, 255, 0), 2)  # Green (Shoulder)
    cv2.line(image, l_chest, r_chest, (0, 255, 255), 2)      # Yellow (Chest)
    cv2.line(image, l_hip, r_hip, (255, 0, 255), 2)          # Magenta (Waist)
    cv2.line(image, nose, mid_ankle, (255, 0, 0), 2)         # Blue (Height)

    # Add Text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, f"S: {real_shoulder:.1f}cm", (l_shoulder[0], l_shoulder[1]-10), font, 0.6, (0,255,0), 2)
    cv2.putText(image, f"C: {real_chest:.1f}cm", (l_chest[0], l_chest[1]-10), font, 0.6, (0,255,255), 2)
    cv2.putText(image, f"W: {real_hip:.1f}cm", (l_hip[0], l_hip[1]-10), font, 0.6, (255,0,255), 2)

    # Resize for display if image is huge
    h, w = image.shape[:2]
    if h > 800:
        scale = 800 / h
        image = cv2.resize(image, (int(w*scale), int(h*scale)))

    cv2.imshow('Body Measurements', image)
    print("Press any key on the image window to close it...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()