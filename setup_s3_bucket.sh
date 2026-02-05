#!/bin/bash

# Script to create S3 bucket and upload model for Lambda deployment

set -e

echo "=========================================="
echo "S3 Bucket Setup for Lambda Model Storage"
echo "=========================================="

# Configuration
BUCKET_NAME="${1:-size-recommendation-models}"
REGION="${2:-ap-south-1}"
MODEL_PATH="${3:-best_model.pth}"

echo ""
echo "Configuration:"
echo "  Bucket Name: $BUCKET_NAME"
echo "  Region: $REGION"
echo "  Model Path: $MODEL_PATH"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed."
    echo "   Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if model file exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  Warning: Model file not found: $MODEL_PATH"
    echo "   Please provide the correct path to your model file"
    read -p "   Enter model path (or press Enter to skip): " MODEL_PATH
    if [ -z "$MODEL_PATH" ] || [ ! -f "$MODEL_PATH" ]; then
        echo "   Skipping model upload. You can upload it later."
        MODEL_PATH=""
    fi
fi

# Create S3 bucket
echo "📦 Creating S3 bucket..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "   ✅ Bucket already exists: $BUCKET_NAME"
else
    echo "   Creating bucket: $BUCKET_NAME in region: $REGION"
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
    echo "   ✅ Bucket created successfully"
fi

# Upload model if path provided
if [ -n "$MODEL_PATH" ] && [ -f "$MODEL_PATH" ]; then
    echo ""
    echo "📤 Uploading model to S3..."
    S3_KEY="models/$(basename $MODEL_PATH)"
    aws s3 cp "$MODEL_PATH" "s3://$BUCKET_NAME/$S3_KEY"
    echo "   ✅ Model uploaded successfully"
    echo ""
    echo "S3 Path: s3://$BUCKET_NAME/$S3_KEY"
    echo ""
    echo "📝 Set this in your Lambda environment variable:"
    echo "   CHECKPOINT_PATH=s3://$BUCKET_NAME/$S3_KEY"
else
    echo ""
    echo "📝 To upload model later, run:"
    echo "   aws s3 cp <model_path> s3://$BUCKET_NAME/models/"
fi

echo ""
echo "=========================================="
echo "✅ Setup completed!"
echo "=========================================="

