import os, json
from backend.shared import generate_put_url

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")

def handler(event, context):
    # parse http req json body (if no body, use empty dict)
    body = json.loads(event.get("body") or "{}")
    # pulls desired filename from req
    filename = body.get("filename", "upload.bin")
    key = f"{NAMESPACE}/uploads/{filename}"                     # s3 object key/path where file gets uploaded
    presigned = generate_put_url(BUCKET, key, expiration=900)   # gets limited time put url (15 mins)
    return {"statusCode": 200, 
            "headers": {"Content-Type": "application/json"}, 
            "body": json.dumps(presigned)
            }