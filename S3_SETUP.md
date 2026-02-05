# S3 Model Upload Guide

This guide explains how to upload your classifier model to AWS S3 for Lambda deployment.

## Prerequisites

1. **AWS CLI installed and configured**
   ```bash
   aws --version
   aws configure
   ```

2. **Model file ready**
   - Your trained model checkpoint (`.pth` file)
   - Typically named `best_model.pth` or similar

## Method 1: Using Python Script (Recommended)

### Step 1: Install boto3
```bash
pip install boto3
```

### Step 2: Run the upload script
```bash
python upload_model_to_s3.py <local_model_path> <bucket_name> [s3_key]
```

**Example:**
```bash
python upload_model_to_s3.py C:/Users/user/Downloads/best_model.pth my-models-bucket models/best_model.pth
```

**Interactive mode:**
```bash
python upload_model_to_s3.py
# Follow prompts
```

## Method 2: Using AWS CLI

### Step 1: Create S3 Bucket
```bash
# Create bucket in ap-south-1 (Mumbai) region
aws s3 mb s3://size-recommendation-models --region ap-south-1
```

### Step 2: Upload Model
```bash
# Upload model
aws s3 cp "C:/Users/user/Downloads/best_model-size-recommendation" s3://size-recommendation-models/models/best_model.pth
```

### Step 3: Verify Upload
```bash
# List files in bucket
aws s3 ls s3://size-recommendation-models/models/
```

## Method 3: Using Setup Script (Linux/Mac)

```bash
chmod +x setup_s3_bucket.sh
./setup_s3_bucket.sh <bucket_name> <region> <model_path>
```

**Example:**
```bash
./setup_s3_bucket.sh size-recommendation-models us-east-1 best_model.pth
```

## After Upload

### 1. Update Lambda Environment Variable

Set in Lambda configuration:
```
CHECKPOINT_PATH=s3://your-bucket-name/models/best_model.pth
```

### 2. Update Local Config (Optional)

For local testing, update `app/config.py`:
```python
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "s3://your-bucket/models/best_model.pth")
```

### 3. Verify IAM Permissions

Lambda execution role needs S3 read permission:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::your-bucket-name/models/*"
    }
  ]
}
```

## S3 Path Format

The S3 path format is:
```
s3://<bucket-name>/<key/path>
```

Examples:
- `s3://my-models/models/best_model.pth`
- `s3://size-recommendation-models/checkpoints/best_model.pth`

## Troubleshooting

### Bucket doesn't exist
```bash
aws s3 mb s3://your-bucket-name --region us-east-1
```

### Access Denied
- Check AWS credentials: `aws configure list`
- Verify IAM permissions for S3 access
- Check bucket policy

### Model not downloading in Lambda
- Verify S3 path is correct
- Check Lambda execution role has S3 permissions
- Check CloudWatch logs for errors

## Cost Considerations

- **S3 Storage**: ~$0.023 per GB/month
- **S3 Requests**: GET requests are very cheap (~$0.0004 per 1000 requests)
- **Data Transfer**: Free within same region

For a typical model (50-500MB), costs are minimal.

