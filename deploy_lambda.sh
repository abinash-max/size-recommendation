#!/bin/bash

# Deploy to AWS Lambda with API Gateway

set -e

echo "Deploying to AWS Lambda..."

# Configuration
FUNCTION_NAME="size-recommendation-api"
REGION="ap-south-1"
RUNTIME="python3.11"
HANDLER="lambda_handler.lambda_handler"
TIMEOUT=900
MEMORY=3008

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not installed"
    exit 1
fi

# Create deployment package
echo "Creating deployment package..."
rm -rf package deployment.zip
mkdir -p package

# Install dependencies
echo "Installing dependencies (this may take 5-10 minutes for PyTorch)..."
echo "Installing: fastapi, mangum, google-genai..."
pip install fastapi mangum google-genai python-multipart pydantic Pillow boto3 -t package/ --no-warn-script-location

echo "Installing: torch, torchvision, timm (this is slow, ~5-10 min)..."
pip install torch torchvision timm -t package/ --no-warn-script-location --index-url https://download.pytorch.org/whl/cpu

# Copy application code
echo "Copying application code..."
cp -r app package/
cp lambda_handler.py package/

# Create zip
echo "Creating deployment zip..."
cd package
zip -r ../deployment.zip . -q
cd ..

echo "Package created: deployment.zip"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://deployment.zip \
        --region $REGION \
        --output json | jq -r '.FunctionArn'
else
    echo "Creating new function..."
    echo "Note: You need to create the function first with proper IAM role"
    echo "Or use AWS SAM/Serverless Framework"
fi

echo "Done!"

