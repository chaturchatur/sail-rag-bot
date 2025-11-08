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
)

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
SESSION_PREFIX = f"{NAMESPACE}/sessions"

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the provided documents. "
    "Use only the supplied context. If you cannot find the answer in the context, say you do not know."
)

_cache = {}


def _load(session_id: str):
    cached = _cache.get(session_id)
    if cached:
        return cached

    index_key = f"{SESSION_PREFIX}/{session_id}/index/faiss.index"
    meta_key = f"{SESSION_PREFIX}/{session_id}/index/meta.json"

    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        download_object(BUCKET, index_key, idxf.name)
        download_object(BUCKET, meta_key, mf.name)
        index = load_index(idxf.name)
        meta = load_metadata(mf.name)

    _cache[session_id] = (index, meta)
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

    index, meta = _load(session_id)

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

    if contexts:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nContext:\n" + "\n\n".join(contexts),
            },
        ]
        answer = chat(messages, temperature=0)
    else:
        answer = "I could not find relevant context in the indexed documents."

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "answer": answer,
                "chunks": chunks,
                "sessionId": session_id,
            }
        ),
    }