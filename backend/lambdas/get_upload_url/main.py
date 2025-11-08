import json
import os

from backend.shared import generate_put_url

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
SESSION_PREFIX = f"{NAMESPACE}/sessions"


def handler(event, context):
    body = json.loads(event.get("body") or "{}")

    session_id = body.get("sessionId")
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }

    filename = body.get("filename", "upload.bin")
    key = f"{SESSION_PREFIX}/{session_id}/uploads/{filename}"

    presigned = generate_put_url(BUCKET, key, expiration=900)
    presigned["sessionId"] = session_id

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(presigned),
    }