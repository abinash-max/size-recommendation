# Lambda Model Deployment Guide

## How Models Work on AWS Lambda

### Current Implementation

The classifier model is handled in three ways depending on the deployment:

1. **Local Development**: Uses local file path from `CHECKPOINT_PATH`
2. **Lambda with S3**: Downloads from S3 to `/tmp` on first invocation
3. **Lambda with Package**: Includes model in deployment package (if small enough)

## Model Storage Options for Lambda

### Option 1: S3 Storage (Recommended) ⭐

**How it works:**
- Model stored in S3 bucket
- Lambda downloads to `/tmp` on cold start
- `/tmp` persists across invocations in same container (up to 10GB)
- Model cached in memory after first load

**Setup:**
```bash
# Upload model to S3
aws s3 cp best_model.pth s3://your-bucket/models/best_model.pth

# Set environment variable
CHECKPOINT_PATH=s3://your-bucket/models/best_model.pth
```

**Pros:**
- ✅ Keeps deployment package small
- ✅ Easy to update model without redeploying
- ✅ `/tmp` persists across invocations (cached)
- ✅ Model cached in memory after first load

**Cons:**
- ⚠️ Cold start downloads model (adds ~2-5 seconds)
- ⚠️ Uses Lambda /tmp space (512MB-10GB limit)

### Option 2: Lambda Layers

**How it works:**
- Model packaged in Lambda Layer
- Layer attached to function
- Model accessible at `/opt/python/` or `/opt/`

**Setup:**
```bash
# Create layer structure
mkdir -p python/lib/python3.11/site-packages/models
cp best_model.pth python/lib/python3.11/site-packages/models/

# Create layer zip
zip -r model-layer.zip python/

# Create layer
aws lambda publish-layer-version \
  --layer-name size-recommendation-model \
  --zip-file fileb://model-layer.zip \
  --compatible-runtimes python3.11

# Attach to function
aws lambda update-function-configuration \
  --function-name size-recommendation-api \
  --layers arn:aws:lambda:region:account:layer:size-recommendation-model:1
```

**Pros:**
- ✅ Model available immediately (no download)
- ✅ Can be shared across functions
- ✅ Updates without redeploying function code

**Cons:**
- ⚠️ Layer size limit: 250MB (unzipped)
- ⚠️ Total package + layers limit: 250MB

### Option 3: Container Image (Best for Large Models)

**How it works:**
- Package everything in Docker container
- Lambda runs container image
- 10GB image size limit

**Setup:**
```dockerfile
# Dockerfile
FROM public.ecr.aws/lambda/python:3.11

COPY requirements-lambda.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements-lambda.txt -t ${LAMBDA_TASK_ROOT}

COPY app ${LAMBDA_TASK_ROOT}/app
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}
COPY best_model.pth ${LAMBDA_TASK_ROOT}/models/

CMD [ "lambda_handler.lambda_handler" ]
```

**Pros:**
- ✅ 10GB size limit (vs 250MB)
- ✅ Can include large models
- ✅ More control over environment

**Cons:**
- ⚠️ Slower cold starts
- ⚠️ More complex deployment

### Option 4: EFS (Elastic File System)

**How it works:**
- Model stored on EFS mount
- Lambda accesses via mount point
- No download needed

**Setup:**
- Create EFS file system
- Mount to Lambda function
- Store model in EFS

**Pros:**
- ✅ No download time
- ✅ Can be very large
- ✅ Shared across functions

**Cons:**
- ⚠️ Additional AWS service cost
- ⚠️ More complex setup
- ⚠️ Network latency

## Current Implementation Details

### Model Loading Flow:

```
1. check_image_recommendation() called
   ↓
2. get_checkpoint_path() checks:
   - If Lambda + S3 path → Download to /tmp (if not exists)
   - Otherwise → Use local path
   ↓
3. get_or_load_model() checks:
   - If model cached in memory → Return cached
   - Otherwise → Load from checkpoint_path
   ↓
4. Model cached in memory for subsequent invocations
```

### Optimization Features:

1. **S3 Download Caching**: Model downloaded to `/tmp` only once per container
2. **Memory Caching**: Model loaded once and cached in memory
3. **Container Reuse**: Lambda containers reused for ~15 minutes, model stays loaded

## Recommended Approach

For your use case, **Option 1 (S3 Storage)** is recommended because:

1. ✅ Model can be large (PyTorch models are typically 50-500MB)
2. ✅ Easy to update without redeploying
3. ✅ `/tmp` caching reduces download overhead
4. ✅ Memory caching eliminates reload overhead after first invocation

## Performance Considerations

### Cold Start (First Invocation):
- S3 Download: ~2-5 seconds (depends on model size)
- Model Loading: ~1-3 seconds
- **Total**: ~3-8 seconds

### Warm Invocation (Subsequent):
- Model already in memory: **0 seconds**
- **Total**: Just inference time (~0.1-0.5 seconds)

### To Reduce Cold Starts:
1. Use **Provisioned Concurrency** (keeps containers warm)
2. Use **Lambda Layers** (if model < 250MB)
3. Use **Container Images** (if model > 250MB)

## Environment Variables for Lambda

Set these in Lambda configuration:

```
CHECKPOINT_PATH=s3://your-bucket/models/best_model.pth
GOOGLE_API_KEY=your-google-api-key
```

## IAM Permissions Required

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
      "Resource": "arn:aws:s3:::your-bucket/models/*"
    }
  ]
}
```

## Monitoring

Monitor these CloudWatch metrics:
- **Duration**: Should decrease after first invocation (cached)
- **Cold Starts**: Track with `InitDuration`
- **Memory Usage**: Model loading uses memory
- **Errors**: Check for S3 download failures

