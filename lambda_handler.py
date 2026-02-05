"""
AWS Lambda handler for FastAPI application
"""
from mangum import Mangum
from app.main import app

# Create Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")

# Lambda entry point
def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    This is the entry point for Lambda invocations.
    """
    return handler(event, context)

