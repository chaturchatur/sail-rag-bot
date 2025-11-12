import json
import os

from backend.shared import get_messages

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")

def handler(event, context):
    """
    GET endpoint to retrieve conversation history for a session.
    Expected path: GET /sessions/{sessionId}/messages
    """
    
    # Extract sessionId from path parameters
    path_params = event.get("pathParameters") or {}
    session_id = path_params.get("sessionId")
    
    if not session_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "sessionId required in path"}),
        }
    
    try:
        # Retrieve conversation history from S3
        messages = get_messages(BUCKET, session_id, NAMESPACE)
        
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
        print(f"error retrieving messages for session {session_id}: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to retrieve messages",
                "details": str(e),
            }),
        }