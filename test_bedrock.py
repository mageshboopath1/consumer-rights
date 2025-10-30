#!/usr/bin/env python3
"""
Test script to verify AWS Bedrock connectivity and Llama 3 70B access
Run this before deploying to ensure everything is configured correctly
"""

import boto3
import json
import os
import sys


def test_bedrock_connection():
    """Test AWS Bedrock connectivity and model access"""

    print("=" * 60)
    print("AWS Bedrock Connection Test")
    print("=" * 60)

    # Get credentials from environment or AWS CLI config
    region = os.getenv("AWS_REGION", "ap-south-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    print(f"\n[1] Configuration:")
    print(f"    Region: {region}")
    print(
        f"    Access Key: {access_key[:10]}..."
        if access_key
        else "    Access Key: Using AWS CLI credentials"
    )
    print(f"    Model: meta.llama3-70b-instruct-v1:0")

    try:
        # Initialize Bedrock client
        print(f"\n[2] Initializing Bedrock client...")
        if access_key and secret_key:
            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        else:
            # Use AWS CLI credentials
            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime", region_name=region
            )
        print("     Client initialized")

        # Test model invocation
        print(f"\n[3] Testing model invocation...")
        request_body = {
            "prompt": "Hello! Please respond with exactly: 'Bedrock connection successful'",
            "max_gen_len": 50,
            "temperature": 0.1,
            "top_p": 0.9,
        }

        print(f"    Sending test request...")
        response = bedrock_runtime.invoke_model(
            modelId="meta.llama3-70b-instruct-v1:0", body=json.dumps(request_body)
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        output = response_body.get("generation", "")

        print(f"     Model responded!")
        print(f"\n[4] Response:")
        print(f"    {output}")

        print(f"\n{'='*60}")
        print(" SUCCESS! AWS Bedrock is configured correctly!")
        print("=" * 60)
        print("\nYou can now proceed with deployment.")
        print("Run: cd live_inference_pipeline && docker-compose up -d")

        return True

    except bedrock_runtime.exceptions.AccessDeniedException as e:
        print(f"\n ERROR: Access Denied")
        print(f"   {e}")
        print(f"\n   Possible fixes:")
        print(f"   1. Check IAM permissions - need 'bedrock:InvokeModel' permission")
        print(f"   2. Request model access in AWS Bedrock console")
        print(f"   3. Verify you're using the correct AWS account")
        return False

    except bedrock_runtime.exceptions.ValidationException as e:
        print(f"\n ERROR: Validation Error")
        print(f"   {e}")
        print(f"\n   Possible fixes:")
        print(f"   1. Check if Llama 3 70B is available in {region}")
        print(f"   2. Try a different region (us-east-1, us-west-2)")
        return False

    except bedrock_runtime.exceptions.ResourceNotFoundException as e:
        print(f"\n ERROR: Model Not Found")
        print(f"   {e}")
        print(f"\n   Possible fixes:")
        print(f"   1. Llama 3 70B may not be available in {region}")
        print(f"   2. Try region: us-east-1 or us-west-2")
        print(f"   3. Check model ID: meta.llama3-70b-instruct-v1:0")
        return False

    except Exception as e:
        print(f"\n ERROR: {type(e).__name__}")
        print(f"   {e}")
        print(f"\n   Check:")
        print(f"   1. AWS credentials are correct")
        print(f"   2. Internet connection is working")
        print(f"   3. AWS Bedrock service is available")
        return False


if __name__ == "__main__":
    print("\nNote: This script will use AWS credentials from:")
    print("  1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
    print("  2. Or AWS CLI configuration (~/.aws/credentials)")
    print()

    success = test_bedrock_connection()
    sys.exit(0 if success else 1)
