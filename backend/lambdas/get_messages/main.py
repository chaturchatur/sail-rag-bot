import json
import os

from backend.shared import get_messages

# get s3 bucket name, namespace, msg table name from env vars
BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default") # default is "default"
MESSAGES_TABLE = os.environ["MESSAGES_TABLE"]

def handler(event, context):
    # get session id from path params
    path_params = event.get("pathParameters") or {}
    session_id = path_params.get("sessionId")
    
    # check if session id is provided
    if not session_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "sessionId required in path"}),
        }
    
    try:
        # get conversation history from dynamodb
        messages = get_messages(BUCKET, session_id, NAMESPACE, table_name=MESSAGES_TABLE)
        
        # return successful response with messages
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "sessionId": session_id,
                "messages": messages,
                "count": len(messages),
            }),
        }
    
    except Exception as e:
        # log error and return 500 response
        print(f"error retrieving messages for session {session_id}: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to retrieve messages",
                "details": str(e),
            }),
        }
