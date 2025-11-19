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

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
SESSION_PREFIX = f"{NAMESPACE}/sessions"
MESSAGES_TABLE = os.environ["MESSAGES_TABLE"]

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the provided documents. "
    "Use only the supplied context. If you cannot find the answer in the context, say you do not know."
)

_cache = {}


def _load(session_id: str):
    index_key = f"{SESSION_PREFIX}/{session_id}/index/faiss.index"
    meta_key = f"{SESSION_PREFIX}/{session_id}/index/meta.json"
    etag = get_etag(BUCKET, index_key)

    cached = _cache.get(session_id)
    if cached:
        cached_etag = cached.get("etag")
        if etag and cached_etag == etag:
            return cached["index"], cached["meta"]
        if not etag and cached_etag is None:
            return cached["index"], cached["meta"]

    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        download_object(BUCKET, index_key, idxf.name)
        download_object(BUCKET, meta_key, mf.name)
        index = load_index(idxf.name)
        meta = load_metadata(mf.name)

    _cache[session_id] = {"etag": etag, "index": index, "meta": meta}
    return index, meta


def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    question = body.get("question", "")
    session_id = body.get("sessionId")

    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }

    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "question required"}),
        }

    index_key = f"{SESSION_PREFIX}/{session_id}/index/faiss.index"
    meta_key = f"{SESSION_PREFIX}/{session_id}/index/meta.json"

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

    # Load conversation history from S3
    conversation_history = get_messages(BUCKET, session_id, NAMESPACE, table_name=MESSAGES_TABLE)

    # Load index for semantic search
    index, meta = _load(session_id)

    # Embed question and search for relevant chunks
    qemb = np.array(embed_texts([question])[0], dtype="float32")
    dists, inds = search_index(index, qemb, k=int(body.get("k", 5)))

    contexts = []
    chunks = []

    for score, idx in zip(dists, inds):
        md = meta.get(str(int(idx)), {})
        if not md:
            continue

        chunk_text = md.get("text", "")
        source = md.get("source")
        page = md.get("page")
        label = source or "Unknown source"
        if page is not None:
            label = f"{label} (page {page})"

        contexts.append(f"[{label}]\n{chunk_text}")
        chunks.append(
            {
                "text": chunk_text,
                "source": source,
                "page": page,
                "score": float(score),
            }
        )

    # Build question with context for current turn
    if contexts:
        current_question = f"Question: {question}\n\nContext:\n" + "\n\n".join(contexts)
    else:
        current_question = question

    # Save user message
    save_message(
        bucket=BUCKET,
        session_id=session_id,
        role="user",
        content=question,
        namespace=NAMESPACE,
        table_name=MESSAGES_TABLE,
    )

    # Build OpenAI messages with conversation history + new question
    messages = openai_messages(conversation_history, SYSTEM_PROMPT)
    messages.append({"role": "user", "content": current_question})

    # Get answer from OpenAI
    if contexts:
        answer = chat(messages, temperature=0)
    else:
        answer = "I could not find relevant context in the indexed documents."

    # Save assistant response
    save_message(
        bucket=BUCKET,
        session_id=session_id,
        role="assistant",
        content=answer,
        chunks=chunks,
        namespace=NAMESPACE,
        table_name=MESSAGES_TABLE,
    )

    # Get updated conversation history (includes the messages we just saved)
    updated_history = get_messages(BUCKET, session_id, NAMESPACE, table_name=MESSAGES_TABLE)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "answer": answer,
                "chunks": chunks,
                "sessionId": session_id,
                "messages": updated_history,  # Return full conversation history
            }
        ),
    }