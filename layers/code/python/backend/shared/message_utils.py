# message storage utilities for chat history
# functions: save and retrieve conversation messages from s3
import json
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

from boto3.dynamodb.conditions import Key

from .dynamodb_utils import get_table
from .s3_utils import get_s3_client, if_object


# saves a new message to session's conversation history in s3
# appends to existing messages.json or creates new file
# message format: {role: 'user'|'assistant', content: str, timestamp: str, chunks: []}
def _session_key(namespace: str, session_id: str) -> str:
    # construct the session key for dynamodb
    return f"{(namespace or 'default')}#{session_id}"

# serialize scores to decimal for dynamodb
# dynamodb requires decimals for numbers, not floats
def _serialize_chunks_for_dynamo(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # initialize list for serialized chunks
    serialized = []
    # loop through each chunk
    for chunk in chunks:
        # copy chunk dictionary
        entry = dict(chunk)
        # get score value
        score = entry.get("score")
        # convert float score to decimal if present
        if isinstance(score, float):
            entry["score"] = Decimal(str(score))
        # add to list
        serialized.append(entry)
    # return processed chunks
    return serialized

# deserialize scores from decimal for python use
# convert decimal back to float for normal use
def _deserialize_chunks_from_dynamo(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # initialize list for deserialized chunks
    deserialized = []
    # loop through each chunk
    for chunk in chunks:
        # copy chunk dictionary
        entry = dict(chunk)
        # get score value
        score = entry.get("score")
        # convert decimal score to float if present
        if isinstance(score, Decimal):
            entry["score"] = float(score)
        # add to list
        deserialized.append(entry)
    # return processed chunks
    return deserialized

# internal helper to save message to s3
def _save_message_s3(bucket: str, session_id: str, namespace: str, message: Dict[str, Any]):
    # define s3 key for messages file
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    # get s3 client
    s3_client = get_s3_client()

    # initialize empty messages list
    messages = []
    # check if messages file exists
    if if_object(bucket, messages_key):
        try:
            # get existing file from s3
            response = s3_client.get_object(Bucket=bucket, Key=messages_key)
            # parse json content
            messages = json.loads(response["Body"].read().decode("utf-8"))
        except Exception as e:
            # log error on failure
            print(f"error loading existing messages: {e}")
            messages = []

    # append new message
    messages.append(message)

    # save updated list to s3
    s3_client.put_object(
        Bucket=bucket,
        Key=messages_key,
        Body=json.dumps(messages, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    # return saved message
    return message


# internal helper to save message to dynamodb
def _save_message_dynamo(table_name: str, session_id: str, namespace: str, message: Dict[str, Any]):
    # get dynamodb table
    table = get_table(table_name)
    # construct item dictionary
    item = {
        "sessionKey": _session_key(namespace, session_id),
        "sessionId": session_id,
        "namespace": namespace,
        "timestamp": message["timestamp"],
        "role": message["role"],
        "content": message["content"],
    }
    # add chunks if they exist
    if "chunks" in message:
        item["chunks"] = _serialize_chunks_for_dynamo(message["chunks"])
    # save item to table
    table.put_item(Item=item)
    # return saved message
    return message

# internal helper to retrieve messages from s3
def _get_messages_s3(bucket: str, session_id: str, namespace: str) -> List[Dict[str, Any]]:
    # define s3 key
    messages_key = f"{namespace}/sessions/{session_id}/messages.json"
    # get s3 client
    s3_client = get_s3_client()

    # return empty if file missing
    if not if_object(bucket, messages_key):
        return []

    # get object from s3
    response = s3_client.get_object(Bucket=bucket, Key=messages_key)
    # parse and return json
    return json.loads(response["Body"].read().decode("utf-8"))


# internal helper to retrieve messages from dynamodb
def _get_messages_dynamo(table_name: str, session_id: str, namespace: str) -> List[Dict[str, Any]]:
    # get table resource
    table = get_table(table_name)
    # define key condition
    key_expr = Key("sessionKey").eq(_session_key(namespace, session_id))
    # query table sorted by timestamp
    response = table.query(KeyConditionExpression=key_expr, ScanIndexForward=True)

    # get initial items
    items = response.get("Items", [])
    # handle pagination
    while "LastEvaluatedKey" in response:
        # fetch next page
        response = table.query(
            KeyConditionExpression=key_expr,
            ScanIndexForward=True,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        # append items
        items.extend(response.get("Items", []))

    # format messages for return
    messages: List[Dict[str, Any]] = []
    for item in items:
        # create message entry
        entry: Dict[str, Any] = {
            "role": item["role"],
            "content": item["content"],
            "timestamp": item["timestamp"],
        }
        # add deserialized chunks if present
        if "chunks" in item:
            entry["chunks"] = _deserialize_chunks_from_dynamo(item["chunks"])
        messages.append(entry)
    return messages

# save a message to either dynamodb (if provided) or s3
def save_message(
    bucket: str,
    session_id: str,
    role: str,
    content: str,
    chunks: Optional[List[Dict]] = None,
    namespace: str = "default",
    table_name: Optional[str] = None,
):
    # get current timestamp
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # create message object
    new_message: Dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
    }

    # add chunks for assistant responses
    if role == "assistant" and chunks:
        new_message["chunks"] = chunks

    # save to dynamodb if configured
    if table_name:
        return _save_message_dynamo(table_name, session_id, namespace, new_message)

    # default to s3 storage
    return _save_message_s3(bucket, session_id, namespace, new_message)

# retrieve all messages for a session from dynamodb or s3
def get_messages(
    bucket: str,
    session_id: str,
    namespace: str = "default",
    table_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # use dynamodb if table name provided
    if table_name:
        return _get_messages_dynamo(table_name, session_id, namespace)
    # default to s3
    return _get_messages_s3(bucket, session_id, namespace)


# builds openai messages array from conversation history
# includes system prompt and formats for openai api
def openai_messages(conversation_history: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, str]]:
    # start with system prompt
    messages = [{"role": "system", "content": system_prompt}]
    
    # loop through history
    for msg in conversation_history:
        # format message for openai
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # return final list
    return messages
