#!/bin/bash

# AWS Lambda Deployment Script
# This script packages and deploys the FastAPI application to AWS Lambda

set -e

echo "🚀 Starting AWS Lambda deployment..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if required environment variables are set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Warning: GOOGLE_API_KEY environment variable is not set"
fi

# Create deployment package directory
echo "📦 Creating deployment package..."
rm -rf package
mkdir -p package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements-lambda.txt -t package/

# Copy application code
echo "📋 Copying application code..."
cp -r app package/
cp lambda_handler.py package/

# Create deployment zip
echo "🗜️  Creating deployment zip..."
cd package
zip -r ../deployment.zip . -q
cd ..

echo "✅ Deployment package created: deployment.zip"
echo ""
echo "📤 To deploy to Lambda:"
echo "   1. Upload deployment.zip to S3 or directly to Lambda"
echo "   2. Set handler to: lambda_handler.lambda_handler"
echo "   3. Set runtime to: Python 3.11"
echo "   4. Set timeout to: 900 seconds"
echo "   5. Set memory to: 3008 MB"
echo ""
echo "Or use AWS SAM/Serverless Framework:"
echo "   sam deploy --guided"
echo "   serverless deploy"

