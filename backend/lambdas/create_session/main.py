import datetime
import json
import os
import uuid

from backend.shared import get_s3_client

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
SESSION_PREFIX = f"{NAMESPACE}/sessions"

def handler(event, context):
    body = json.loads(event.get("body") or "{}")

    user_id = body.get("userId")
    metadata = body.get("metadata") or {}
    explicitly_provided = body.get("sessionId")

    session_id = explicitly_provided or str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    manifest = {
        "sessionId": session_id,
        "userId": user_id,
        "createdAt": now_iso,
        "metadata": metadata,
    }

    s3 = get_s3_client()
    manifest_key = f"{SESSION_PREFIX}/{session_id}/manifest.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=manifest_key,
        Body=json.dumps(manifest).encode("utf-8"),
        ContentType="application/json",
    )

    response_body = {
        "sessionId": session_id,
        "manifestKey": manifest_key,
        "namespace": NAMESPACE,
        "createdAt": now_iso,
        "metadata": metadata,
    }

    status_code = 200 if explicitly_provided else 201

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }