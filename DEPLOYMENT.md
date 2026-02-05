# AWS Lambda Deployment Guide

This guide explains how to deploy the Size Recommendation API to AWS Lambda with API Gateway.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Python 3.11** (matching Lambda runtime)
4. **Docker** (for building packages with native dependencies)

## Option 1: Using AWS SAM (Recommended)

### 1. Install AWS SAM CLI

```bash
# macOS
brew install aws-sam-cli

# Linux
pip install aws-sam-cli

# Windows
# Download from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

### 2. Build and Deploy

```bash
# Build the application
sam build

# Deploy (guided mode for first time)
sam deploy --guided

# Or deploy with existing config
sam deploy
```

### 3. Configure Parameters

During guided deployment, you'll be asked for:
- **Stack Name**: `size-recommendation-api`
- **AWS Region**: `us-east-1` (or your preferred region)
- **GoogleApiKey**: Your Google AI API key
- **CheckpointPath**: S3 path to your model checkpoint (e.g., `s3://your-bucket/models/best_model.pth`)

## Option 2: Using Serverless Framework

### 1. Install Serverless Framework

```bash
npm install -g serverless
npm install --save-dev serverless-python-requirements
```

### 2. Configure

Edit `serverless.yml` and update:
- Region
- S3 bucket for model storage
- Environment variables

### 3. Deploy

```bash
# Set environment variables
export GOOGLE_API_KEY="your-api-key"
export CHECKPOINT_PATH="s3://your-bucket/models/best_model.pth"

# Deploy
serverless deploy
```

## Option 3: Manual Deployment

### 1. Create Deployment Package

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

### 2. Upload to Lambda

```bash
# Create Lambda function via AWS CLI
aws lambda create-function \
  --function-name size-recommendation-api \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://deployment.zip \
  --timeout 900 \
  --memory-size 3008 \
  --environment Variables="{GOOGLE_API_KEY=your-key,CHECKPOINT_PATH=s3://bucket/path}"

# Or update existing function
aws lambda update-function-code \
  --function-name size-recommendation-api \
  --zip-file fileb://deployment.zip
```

### 3. Create API Gateway

1. Go to AWS Console → API Gateway
2. Create new REST API
3. Create resource and method (ANY /{proxy+})
4. Set integration type to Lambda Function
5. Deploy API

## Important Considerations

### 1. Package Size

Lambda has a 250MB limit for deployment packages (unzipped). PyTorch and related packages are large. Consider:

- **Lambda Layers**: Create a Lambda Layer for PyTorch/torchvision/timm
- **S3 Storage**: Store model files in S3 and download on cold start
- **Container Images**: Use Lambda container images (10GB limit)

### 2. Model Storage

The classifier model should be stored in S3:

```python
# Update app/classifier.py to download from S3 on cold start
import boto3

def download_model_from_s3():
    s3 = boto3.client('s3')
    bucket = 'your-bucket'
    key = 'models/best_model.pth'
    local_path = '/tmp/best_model.pth'
    s3.download_file(bucket, key, local_path)
    return local_path
```

### 3. Cold Start Optimization

- Use Lambda Provisioned Concurrency
- Keep model in `/tmp` directory (persists between invocations)
- Consider using AWS Lambda Container Images

### 4. Memory and Timeout

- **Memory**: 3008 MB (maximum) for better CPU performance
- **Timeout**: 900 seconds (15 minutes maximum)
- PyTorch models need sufficient memory

### 5. Environment Variables

Set these in Lambda configuration:
- `GOOGLE_API_KEY`: Your Google AI API key
- `CHECKPOINT_PATH`: S3 path to model checkpoint

### 6. IAM Permissions

Lambda execution role needs:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Testing

After deployment, test the API:

```bash
# Get API endpoint from deployment output
API_URL="https://your-api-id.execute-api.region.amazonaws.com/prod"

# Test health endpoint
curl $API_URL/health

# Test recommendation endpoint
curl -X POST "$API_URL/recommend" \
  -F "image=@test_image.jpg" \
  -F "height_cm=170.0"
```

## Monitoring

- **CloudWatch Logs**: Monitor Lambda execution logs
- **CloudWatch Metrics**: Track invocations, errors, duration
- **X-Ray**: Enable for distributed tracing

## Cost Optimization

- Use Lambda Layers for shared dependencies
- Consider S3 for model storage (cheaper than Lambda package)
- Use Provisioned Concurrency only if needed
- Monitor and optimize memory allocation

## Troubleshooting

### Package Too Large
- Use Lambda Layers for PyTorch
- Or use container images

### Timeout Issues
- Increase timeout to 900 seconds
- Optimize model loading (cache in /tmp)
- Consider using Provisioned Concurrency

### Memory Issues
- Increase memory to 3008 MB
- Check model size
- Optimize batch processing

### Import Errors
- Ensure all dependencies are in package
- Check Python path
- Verify handler path

