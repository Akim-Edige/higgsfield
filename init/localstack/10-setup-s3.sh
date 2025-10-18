#!/usr/bin/env bash
set -euo pipefail
: "${AWS_DEFAULT_REGION:=us-east-1}"
: "${S3_BUCKET:=media}"

echo "Creating S3 bucket ${S3_BUCKET}..."
awslocal s3api create-bucket --bucket "${S3_BUCKET}" --region "${AWS_DEFAULT_REGION}"

echo "Applying CORS..."
awslocal s3api put-bucket-cors --bucket "${S3_BUCKET}" --cors-configuration file:///etc/localstack/init/cors.json

echo "S3 bucket ${S3_BUCKET} setup complete!"

