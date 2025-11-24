import datetime
import json
import os
import uuid

from backend.shared import get_s3_client

# get s3 bucket name, namespace from env vars
BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default") # default is "default"

# define the session prefix path
SESSION_PREFIX = f"{NAMESPACE}/sessions"


def handler(event, context):
    # parse the request body from json str
    body = json.loads(event.get("body") or "{}")

    # extract user id, metadata, session id from body
    user_id = body.get("userId")
    metadata = body.get("metadata") or {}
    explicitly_provided = body.get("sessionId")

    # use provided session id if provided
    # or generate a new unique id
    session_id = explicitly_provided or str(uuid.uuid4())
    
    # current timestamp utc iso format
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # manifest dict with session details
    manifest = {
        "sessionId": session_id,
        "userId": user_id,
        "createdAt": now_iso,
        "metadata": metadata,
    }

    # initialize s3 client
    s3 = get_s3_client()
    
    # path for the manifest file
    manifest_key = f"{SESSION_PREFIX}/{session_id}/manifest.json"
    # upload manifest json to s3 bucket
    s3.put_object(
        Bucket=BUCKET,
        Key=manifest_key,
        Body=json.dumps(manifest).encode("utf-8"),
        ContentType="application/json",
    )

    # prepare the response body dict
    response_body = {
        "sessionId": session_id,
        "manifestKey": manifest_key,
        "namespace": NAMESPACE,
        "createdAt": now_iso,
        "metadata": metadata,
    }

    # set status code to 200 if session exists
    # else 201
    status_code = 200 if explicitly_provided else 201

    # return response 
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
