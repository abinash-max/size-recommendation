# Update Lambda function from S3 (faster for large packages)

$FunctionName = "size-recommendation-api-SizeRecommendationApi-aRdQfnKdLFy7"
$Region = "ap-south-1"
$S3Bucket = "size-recommendation-models"
$S3Key = "deployments/lambda-deployment.zip"

Write-Host "Updating Lambda function from S3..." -ForegroundColor Yellow
Write-Host "Function: $FunctionName" -ForegroundColor Cyan
Write-Host "S3: s3://$S3Bucket/$S3Key" -ForegroundColor Cyan

# Update function code from S3
$result = aws lambda update-function-code `
    --function-name $FunctionName `
    --s3-bucket $S3Bucket `
    --s3-key $S3Key `
    --region $Region `
    --output json 2>&1

if ($LASTEXITCODE -eq 0) {
    $result | ConvertFrom-Json | Select-Object FunctionArn, LastUpdateStatus, CodeSize
    Write-Host "`nUpdate initiated! Checking status..." -ForegroundColor Green
    
    # Wait and check status
    Start-Sleep -Seconds 10
    
    $status = aws lambda get-function --function-name $FunctionName --region $Region --query "Configuration.LastUpdateStatus" --output text
    Write-Host "Status: $status" -ForegroundColor Cyan
    
    if ($status -eq "InProgress") {
        Write-Host "Update is still in progress. This can take 2-5 minutes for large packages." -ForegroundColor Yellow
        Write-Host "Check status with: aws lambda get-function --function-name $FunctionName --region $Region" -ForegroundColor Gray
    } elseif ($status -eq "Successful") {
        Write-Host "Update completed successfully!" -ForegroundColor Green
    }
} else {
    Write-Host "Error: $result" -ForegroundColor Red
}

