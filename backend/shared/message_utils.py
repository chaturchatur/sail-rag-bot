# message storage utilities for chat history
# functions: save and retrieve conversation messages from S3

import json
import datetime
from typing import List, Dict, Any, Optional
from .s3_utils import get_s3_client, if_object

# saves a new message to session's conversation history in S3
# appends to existing messages.json or creates new file
# message format: {role: 'user'|'assistant', content: str, timestamp: str, chunks: []}
def save_message(bucket: str, session_id: str, role: str, content: str, chunks: Optional[List[Dict]] = None, namespace: str = "default"):
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    s3_client = get_s3_client()
    
    # create new message
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_message = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
    }
    
    # only add chunks for assistant messages
    if role == "assistant" and chunks:
        new_message["chunks"] = chunks
    
    # load existing messages if they exist
    messages = []
    if if_object(bucket, messages_key):
        try:
            response = s3_client.get_object(Bucket=bucket, Key=messages_key)
            messages = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"error loading existing messages: {e}")
            # continue with empty list if load fails
            messages = []
    
    # append new message
    messages.append(new_message)
    
    # save back to S3
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=messages_key,
            Body=json.dumps(messages, indent=2).encode('utf-8'),
            ContentType='application/json',
        )
        return new_message
    except Exception as e:
        print(f"error saving message to s3: {e}")
        raise

# retrieves conversation history for a session from S3
# returns list of messages in chronological order
def get_messages(bucket: str, session_id: str, namespace: str = "default") -> List[Dict[str, Any]]:
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    s3_client = get_s3_client()
    
    # check if messages exist
    if not if_object(bucket, messages_key):
        return []
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=messages_key)
        messages = json.loads(response['Body'].read().decode('utf-8'))
        return messages
    except Exception as e:
        print(f"error retrieving messages from s3: {e}")
        raise

# builds OpenAI messages array from conversation history
# includes system prompt and formats for OpenAI API
def openai_messages(conversation_history: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in conversation_history:
        # only include role and content for OpenAI
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    return messages