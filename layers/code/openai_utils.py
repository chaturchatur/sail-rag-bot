import boto3
import json
import os
import openai
from typing import Any, Optional, Dict, List

# get openai key from aws secret manager
# gets the latest val and returns it as a string
def get_openai_key():
    secret_arn = os.environ.get('OPEN_SECRET_ARN')
    
    if not secret_arn:
        raise ValueError("openai secret not set")
    
    try:
        sm_client = boto3.client('secretsmanager')
        response = sm_client.get_secret_value(SecretId=secret_arn)
        return response['SecretString']
    except Exception as e:
        print(f"error retrieving OpenAI key: {e}")
        raise
    
# get openai client instance
# for other utils to interact with openai 
def get_openai_client():
    api_key = get_openai_key()
    return openai.OpenAI(api_key=api_key)

# converts text into fixed size vectors
# maps text to numeric vectors for similarity search
# this will run the semnatic search in ingest/querying
def embed_texts(texts: List[str], model: str = None):
    if model is None:
        model = os.environ.get('EMBED_MODEL', 'text-embedding-3-small')
    
    client = get_openai_client()
    
    try:
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"error creating embeddings: {e}")
        raise
    
# sends a chat completion request to gpt
# returns the reply from gpt
def chat(messages: List[Dict[str, str]], model: str = None, **kwargs):
    if model is None:
        model = os.environ.get('CHAT_MODEL', 'gpt-4o-mini')
    
    client = get_openai_client()
    
    try:
        response = client.chat.completions.create(model=model, messages=messages, **kwargs)
        return response.choices[0].message.content
    except Exception as e:
        print(f"error in chat: {e}")
        raise
    


    