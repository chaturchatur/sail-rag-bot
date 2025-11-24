# create main s3 bucket for document storage
resource "aws_s3_bucket" "docs" {
  bucket = local.bucket_name
}

# secure the bucket by blocking all public access
# ensures files are only accessible via authenticated aws mechanisms
resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# configure cors to allow frontend access
# needed for direct browser uploads to s3
resource "aws_s3_bucket_cors_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id

  cors_rule {
    allowed_origins = ["http://localhost:3000"]   # allow local frontend to access bucket
    allowed_methods = ["PUT", "GET", "HEAD"]      # allowed operations (put for upload, get for download)
    allowed_headers = ["*"]                       
    expose_headers  = ["ETag"]                    # expose etag header for upload verification
    max_age_seconds = 3000                        # cache preflight request for 3000s
  }
}