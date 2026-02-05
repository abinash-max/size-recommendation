# PowerShell script to deploy to AWS Lambda

$FunctionName = "size-recommendation-api"
$Region = "ap-south-1"
$Runtime = "python3.11"
$Handler = "lambda_handler.lambda_handler"
$Timeout = 900
$Memory = 3008

Write-Host "Deploying to AWS Lambda..." -ForegroundColor Green

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "deployment.zip" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "package" | Out-Null

# Install dependencies (isolated to avoid conflicts)
Write-Host "Installing dependencies (this may take 5-10 minutes for PyTorch)..." -ForegroundColor Yellow
Write-Host "Installing: fastapi, mangum, google-genai..." -ForegroundColor Cyan
pip install fastapi mangum google-genai python-multipart pydantic Pillow boto3 -t package/ --no-warn-script-location --no-deps --ignore-installed

Write-Host "Installing: torch, torchvision (this is slow, ~5-10 min)..." -ForegroundColor Cyan
pip install torch torchvision -t package/ --no-warn-script-location --index-url https://download.pytorch.org/whl/cpu --no-deps

Write-Host "Installing: timm..." -ForegroundColor Cyan
pip install timm -t package/ --no-warn-script-location --no-deps

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Path "app" -Destination "package\app" -Recurse
Copy-Item -Path "lambda_handler.py" -Destination "package\lambda_handler.py"

# Create zip
Write-Host "Creating deployment zip (this may take a few minutes)..." -ForegroundColor Yellow
Compress-Archive -Path "package\*" -DestinationPath "deployment.zip" -Force

$zipSize = (Get-Item deployment.zip).Length / 1MB
Write-Host "Package created: deployment.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green

# Check zip size
$zipSize = (Get-Item deployment.zip).Length / 1MB
Write-Host "Zip size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Cyan

if ($zipSize -gt 50) {
    Write-Host "Warning: Zip is large. Consider uploading to S3 first, then updating from S3." -ForegroundColor Yellow
}

# Check if function exists
Write-Host "Checking if function exists..." -ForegroundColor Yellow
$functionExists = aws lambda get-function --function-name $FunctionName --region $Region 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Updating Lambda function..." -ForegroundColor Yellow
    
    # Try direct upload first
    try {
        $result = aws lambda update-function-code `
            --function-name $FunctionName `
            --zip-file fileb://deployment.zip `
            --region $Region `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $result | ConvertFrom-Json | Select-Object -ExpandProperty FunctionArn
            Write-Host "Function updated successfully!" -ForegroundColor Green
        } else {
            Write-Host "Direct upload failed. Trying S3 upload method..." -ForegroundColor Yellow
            # Upload to S3 first, then update from S3
            $s3Bucket = "size-recommendation-models"
            $s3Key = "deployments/deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
            
            Write-Host "Uploading to S3: s3://$s3Bucket/$s3Key" -ForegroundColor Cyan
            aws s3 cp deployment.zip "s3://$s3Bucket/$s3Key" --region $Region
            
            Write-Host "Updating function from S3..." -ForegroundColor Cyan
            aws lambda update-function-code `
                --function-name $FunctionName `
                --s3-bucket $s3Bucket `
                --s3-key $s3Key `
                --region $Region `
                --output json | ConvertFrom-Json | Select-Object -ExpandProperty FunctionArn
            Write-Host "Function updated successfully from S3!" -ForegroundColor Green
        }
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Function doesn't exist. Create it first using:" -ForegroundColor Red
    Write-Host "  sam deploy --guided --region $Region" -ForegroundColor Yellow
    Write-Host "Or create manually in AWS Console" -ForegroundColor Yellow
}

Write-Host "Done!" -ForegroundColor Green

