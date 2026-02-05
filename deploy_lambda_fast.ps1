# Fast deployment - excludes PyTorch (use Lambda Layer instead)
# Use this if PyTorch installation is too slow

$FunctionName = "size-recommendation-api"
$Region = "ap-south-1"

Write-Host "Fast deployment (without PyTorch)..." -ForegroundColor Green
Write-Host "Note: PyTorch should be in a Lambda Layer" -ForegroundColor Yellow

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "deployment.zip" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "package" | Out-Null

# Install only essential dependencies (no PyTorch)
Write-Host "Installing essential dependencies..." -ForegroundColor Yellow
pip install fastapi mangum google-genai python-multipart pydantic Pillow boto3 -t package/ --no-warn-script-location --quiet

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Path "app" -Destination "package\app" -Recurse
Copy-Item -Path "lambda_handler.py" -Destination "package\lambda_handler.py"

# Create zip
Write-Host "Creating deployment zip..." -ForegroundColor Yellow
Compress-Archive -Path "package\*" -DestinationPath "deployment.zip" -Force

Write-Host "Package created: deployment.zip" -ForegroundColor Green
Write-Host "Size: $((Get-Item deployment.zip).Length / 1MB) MB" -ForegroundColor Cyan

# Update function
Write-Host "Updating Lambda function..." -ForegroundColor Yellow
try {
    $result = aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file fileb://deployment.zip `
        --region $Region `
        --output json | ConvertFrom-Json
    Write-Host "Function updated: $($result.FunctionArn)" -ForegroundColor Green
} catch {
    Write-Host "Function doesn't exist. Create it first." -ForegroundColor Red
}

Write-Host "Done!" -ForegroundColor Green

