"""
Script to upload the classifier model to AWS S3
"""
import os
import boto3
from botocore.exceptions import ClientError
import sys

def upload_model_to_s3(local_model_path, bucket_name, s3_key=None):
    """
    Upload model file to S3 bucket.
    
    Args:
        local_model_path: Local path to the model file
        bucket_name: S3 bucket name
        s3_key: S3 key (path) where to store the model. If None, uses filename
    """
    # Check if file exists
    if not os.path.exists(local_model_path):
        print(f"❌ Error: Model file not found: {local_model_path}")
        return False
    
    # Get file size
    file_size = os.path.getsize(local_model_path) / (1024 * 1024)  # Size in MB
    print(f"📦 Model file size: {file_size:.2f} MB")
    
    # Default S3 key if not provided
    if s3_key is None:
        s3_key = f"models/{os.path.basename(local_model_path)}"
    
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        print(f"\n📤 Uploading model to S3...")
        print(f"   Local path: {local_model_path}")
        print(f"   S3 bucket: {bucket_name}")
        print(f"   S3 key: {s3_key}")
        
        # Upload file
        s3_client.upload_file(
            local_model_path,
            bucket_name,
            s3_key,
            Callback=lambda bytes_transferred: print(f"   Uploaded: {bytes_transferred / (1024*1024):.2f} MB", end='\r')
        )
        
        s3_path = f"s3://{bucket_name}/{s3_key}"
        print(f"\n✅ Model uploaded successfully!")
        print(f"   S3 Path: {s3_path}")
        print(f"\n📝 Update your Lambda environment variable:")
        print(f"   CHECKPOINT_PATH={s3_path}")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Error: Bucket '{bucket_name}' does not exist.")
            print(f"   Create it first: aws s3 mb s3://{bucket_name}")
        elif error_code == 'AccessDenied':
            print(f"❌ Error: Access denied. Check your AWS credentials and permissions.")
        else:
            print(f"❌ Error uploading file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main function"""
    print("="*70)
    print("Upload Classifier Model to S3")
    print("="*70)
    
    # Get inputs
    if len(sys.argv) >= 3:
        local_path = sys.argv[1]
        bucket_name = sys.argv[2]
        s3_key = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        # Interactive mode
        print("\nEnter model details:")
        local_path = input("Local model path: ").strip()
        bucket_name = input("S3 bucket name: ").strip()
        s3_key_input = input("S3 key/path (press Enter for 'models/filename'): ").strip()
        s3_key = s3_key_input if s3_key_input else None
    
    # Validate inputs
    if not local_path or not bucket_name:
        print("❌ Error: Local path and bucket name are required")
        print("\nUsage:")
        print("  python upload_model_to_s3.py <local_path> <bucket_name> [s3_key]")
        print("\nExample:")
        print("  python upload_model_to_s3.py best_model.pth my-models-bucket models/best_model.pth")
        sys.exit(1)
    
    # Upload
    success = upload_model_to_s3(local_path, bucket_name, s3_key)
    
    if success:
        print("\n" + "="*70)
        print("✅ Upload completed successfully!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ Upload failed!")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()

