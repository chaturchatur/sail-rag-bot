import boto3
import json
import os
import openai
from typing import Any, Optional, Dict, List

# get openai key from aws secret manager
# gets the latest val and returns it as a string
def get_openai_key():
    # get secret arn from environment
    secret_arn = os.environ.get('OPENAI_SECRET_ARN')
    
    # check if arn is present
    if not secret_arn:
        raise ValueError("openai secret not set")
    
    try:
        # initialize secrets manager client
        sm_client = boto3.client('secretsmanager')
        # get secret value using arn
        response = sm_client.get_secret_value(SecretId=secret_arn)
        # return the secret string
        return response['SecretString']
    except Exception as e:
        # log error and raise
        print(f"error retrieving OpenAI key: {e}")
        raise
  
    
# get openai client instance
# for other utils to interact with openai 
def get_openai_client():
    # retrieve api key
    api_key = get_openai_key()
    # return configured client
    return openai.OpenAI(api_key=api_key)

# converts text into fixed size vectors
# maps text to numeric vectors for similarity search
# this will run the semnatic search in ingest/querying
def embed_texts(texts: List[str], model: str = None):
    # use default model if none provided
    if model is None:
        model = os.environ.get('EMBED_MODEL', 'text-embedding-3-small')
    
    # get openai client
    client = get_openai_client()
    
    try:
        # call embedding api
        response = client.embeddings.create(model=model, input=texts)
        # extract and return embeddings list
        return [item.embedding for item in response.data]
    except Exception as e:
        # log error and raise
        print(f"error creating embeddings: {e}")
        raise
   
    
# sends a chat completion request to gpt
# returns the reply from gpt
def chat(messages: List[Dict[str, str]], model: str = None, **kwargs):
    # use default model if none provided
    if model is None:
        model = os.environ.get('CHAT_MODEL', 'gpt-4o-mini')
    
    # get openai client
    client = get_openai_client()
    
    try:
        # call chat completion api
        response = client.chat.completions.create(model=model, messages=messages, **kwargs)
        # extract and return content from first choice
        return response.choices[0].message.content
    except Exception as e:
        # log error and raise
        print(f"error in chat: {e}")
        raise
