# message storage utilities for chat history
# functions: save and retrieve conversation messages from S3
import json
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

from boto3.dynamodb.conditions import Key

from .dynamodb_utils import get_table
from .s3_utils import get_s3_client, if_object


# saves a new message to session's conversation history in S3
# appends to existing messages.json or creates new file
# message format: {role: 'user'|'assistant', content: str, timestamp: str, chunks: []}
def _session_key(namespace: str, session_id: str) -> str:
    return f"{(namespace or 'default')}#{session_id}"

def _serialize_chunks_for_dynamo(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized = []
    for chunk in chunks:
        entry = dict(chunk)
        score = entry.get("score")
        if isinstance(score, float):
            entry["score"] = Decimal(str(score))
        serialized.append(entry)
    return serialized

def _deserialize_chunks_from_dynamo(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deserialized = []
    for chunk in chunks:
        entry = dict(chunk)
        score = entry.get("score")
        if isinstance(score, Decimal):
            entry["score"] = float(score)
        deserialized.append(entry)
    return deserialized

def _save_message_s3(bucket: str, session_id: str, namespace: str, message: Dict[str, Any]):
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    s3_client = get_s3_client()

    messages = []
    if if_object(bucket, messages_key):
        try:
            response = s3_client.get_object(Bucket=bucket, Key=messages_key)
            messages = json.loads(response["Body"].read().decode("utf-8"))
        except Exception as e:
            print(f"error loading existing messages: {e}")
            messages = []

    messages.append(message)

    s3_client.put_object(
        Bucket=bucket,
        Key=messages_key,
        Body=json.dumps(messages, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return message


def _save_message_dynamo(table_name: str, session_id: str, namespace: str, message: Dict[str, Any]):
    table = get_table(table_name)
    item = {
        "sessionKey": _session_key(namespace, session_id),
        "sessionId": session_id,
        "namespace": namespace,
        "timestamp": message["timestamp"],
        "role": message["role"],
        "content": message["content"],
    }
    if "chunks" in message:
        item["chunks"] = _serialize_chunks_for_dynamo(message["chunks"])
    table.put_item(Item=item)
    return message

def _get_messages_s3(bucket: str, session_id: str, namespace: str) -> List[Dict[str, Any]]:
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    s3_client = get_s3_client()

    if not if_object(bucket, messages_key):
        return []

    response = s3_client.get_object(Bucket=bucket, Key=messages_key)
    return json.loads(response["Body"].read().decode("utf-8"))


def _get_messages_dynamo(table_name: str, session_id: str, namespace: str) -> List[Dict[str, Any]]:
    table = get_table(table_name)
    key_expr = Key("sessionKey").eq(_session_key(namespace, session_id))
    response = table.query(KeyConditionExpression=key_expr, ScanIndexForward=True)

    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=key_expr,
            ScanIndexForward=True,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    messages: List[Dict[str, Any]] = []
    for item in items:
        entry: Dict[str, Any] = {
            "role": item["role"],
            "content": item["content"],
            "timestamp": item["timestamp"],
        }
        if "chunks" in item:
            entry["chunks"] = _deserialize_chunks_from_dynamo(item["chunks"])
        messages.append(entry)
    return messages

def save_message(
    bucket: str,
    session_id: str,
    role: str,
    content: str,
    chunks: Optional[List[Dict]] = None,
    namespace: str = "default",
    table_name: Optional[str] = None,
):
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_message: Dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
    }

    if role == "assistant" and chunks:
        new_message["chunks"] = chunks

    if table_name:
        return _save_message_dynamo(table_name, session_id, namespace, new_message)

    return _save_message_s3(bucket, session_id, namespace, new_message)

def get_messages(
    bucket: str,
    session_id: str,
    namespace: str = "default",
    table_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if table_name:
        return _get_messages_dynamo(table_name, session_id, namespace)
    return _get_messages_s3(bucket, session_id, namespace)


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