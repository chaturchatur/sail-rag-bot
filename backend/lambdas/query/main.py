import json
import os
import tempfile

import numpy as np

from backend.shared import (
    chat,
    download_object,
    embed_texts,
    if_object,
    load_index,
    load_metadata,
    search_index,
    get_messages,
    save_message,
    openai_messages,
    get_etag
)

# get bucket namem namespace, message table from env vars
BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
MESSAGES_TABLE = os.environ["MESSAGES_TABLE"]
# session prefix path
SESSION_PREFIX = f"{NAMESPACE}/sessions"

# system prompt for the assistant
SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the provided documents. "
    "Use only the supplied context. If you cannot find the answer in the context, say you do not know."
)

# global cache for index and metadata
_cache = {}


def _load(session_id: str):
    # keys for index and metadata
    index_key = f"{SESSION_PREFIX}/{session_id}/index/faiss.index"
    meta_key = f"{SESSION_PREFIX}/{session_id}/index/meta.json"
    
    # get etag for the index file
    etag = get_etag(BUCKET, index_key)

    # check if session data is cached
    cached = _cache.get(session_id)
    if cached:
        cached_etag = cached.get("etag")
        # return cached data if etag matches
        if etag and cached_etag == etag:
            return cached["index"], cached["meta"]
        # return cached data if etag is missing in both
        if not etag and cached_etag is None:
            return cached["index"], cached["meta"]

    # download index and metadata to temporary files
    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        download_object(BUCKET, index_key, idxf.name)
        download_object(BUCKET, meta_key, mf.name)
        # load index and metadata from files
        index = load_index(idxf.name)
        meta = load_metadata(mf.name)

    # update cache with new data
    _cache[session_id] = {"etag": etag, "index": index, "meta": meta}
    return index, meta


def handler(event, context):
    # parse the request body from json string or default to empty dict
    body = json.loads(event.get("body") or "{}")
    # extract question and session id from body
    question = body.get("question", "")
    session_id = body.get("sessionId")
    # check if session id is provided
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }
    # check if question is provided
    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "question required"}),
        }

    # keys for index and metadata
    index_key = f"{SESSION_PREFIX}/{session_id}/index/faiss.index"
    meta_key = f"{SESSION_PREFIX}/{session_id}/index/meta.json"
    # check if index or metadata exists
    if not if_object(BUCKET, index_key) or not if_object(BUCKET, meta_key):
        return {
            "statusCode": 404,
            "body": json.dumps(
                {
                    "error": "No index found for session. Upload and ingest documents first.",
                    "sessionId": session_id,
                }
            ),
        }
    # load index for semantic search
    index, meta = _load(session_id)
    # embed question and search for relevant chunks
    qemb = np.array(embed_texts([question])[0], dtype="float32")
    dists, inds = search_index(index, qemb, k=int(body.get("k", 5)))

    # initialize lists for contexts and chunks
    contexts = []
    chunks = []
    # iterate over search results
    for score, idx in zip(dists, inds):
        # get metadata for the chunk
        md = meta.get(str(int(idx)), {})
        if not md:
            continue
        # extract text, source, and page from metadata
        chunk_text = md.get("text", "")
        source = md.get("source")
        page = md.get("page")
        label = source or "Unknown source"
        if page is not None:
            label = f"{label} (page {page})"
        # add formatted context and chunk details
        contexts.append(f"[{label}]\n{chunk_text}")
        chunks.append(
            {
                "text": chunk_text,
                "source": source,
                "page": page,
                "score": float(score),
            }
        )

     # load conversation history from dynamodb
    conversation_history = get_messages(BUCKET, session_id, NAMESPACE, table_name=MESSAGES_TABLE)
    # build question with context for current turn
    if contexts:
        current_question = f"Question: {question}\n\nContext:\n" + "\n\n".join(contexts)
    else:
        current_question = question
    # save user message to history
    save_message(
        bucket=BUCKET,
        session_id=session_id,
        role="user",
        content=question,
        namespace=NAMESPACE,
        table_name=MESSAGES_TABLE,
    )

    # build openai messages with conversation history + new question
    messages = openai_messages(conversation_history, SYSTEM_PROMPT)
    messages.append({"role": "user", "content": current_question})
    # get answer from openai
    if contexts:
        answer = chat(messages, temperature=0)
    else:
        answer = "I could not find relevant context in the indexed documents."
    # save assistant response to history
    save_message(
        bucket=BUCKET,
        session_id=session_id,
        role="assistant",
        content=answer,
        chunks=chunks,
        namespace=NAMESPACE,
        table_name=MESSAGES_TABLE,
    )

    # get updated conversation history
    updated_history = get_messages(BUCKET, session_id, NAMESPACE, table_name=MESSAGES_TABLE)
    # return successful response with answer and history
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "answer": answer,
                "chunks": chunks,
                "sessionId": session_id,
                "messages": updated_history,
            }
        ),
    }
