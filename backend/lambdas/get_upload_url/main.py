import json
import os

from backend.shared import generate_put_url

# get bucket name, namespace from env vars
BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default") # default to "default"
# session prefix path
SESSION_PREFIX = f"{NAMESPACE}/sessions"


def handler(event, context):
    # parse the request body from json str
    body = json.loads(event.get("body") or "{}")

    # get session id from body
    session_id = body.get("sessionId")
    # check if session id is provided
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }

    # get filename from body
    # default to "upload.bin"
    filename = body.get("filename", "upload.bin")
    # key path for the upload
    key = f"{SESSION_PREFIX}/{session_id}/uploads/{filename}"

    # generate presigned url for uploading file
    # url expires after 15 mins
    presigned = generate_put_url(BUCKET, key, expiration=900) 
    # add session id to response
    presigned["sessionId"] = session_id

    # return response with presigned url
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(presigned),
    }
