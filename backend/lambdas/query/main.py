# backend/lambdas/query/main.py

import os, json, tempfile
import numpy as np
from backend.shared import download_object, load_index, load_metadata, embed_texts, search_index, chat

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
INDEX_PREFIX = f"{NAMESPACE}/index"
SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the provided documents. "
    "Use only the supplied context. If you cannot find the answer in the context, say you do not know."
)

# warm cache global vars
_index = None
_meta = None

# check if _index, _meta are loaded (return warm path)
def _load():
    global _index, _meta
    # check if cache is warm
    if _index is not None and _meta is not None:
        return
    # load two temp files for index and metadata
    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        download_object(BUCKET, f"{INDEX_PREFIX}/faiss.index", idxf.name)   # pull index file from s3
        download_object(BUCKET, f"{INDEX_PREFIX}/meta.json", mf.name)       # pull metadata file from s3
        _index = load_index(idxf.name)                                      # load faiss index 
        _meta = load_metadata(mf.name)                                      # load metadata 

def handler(event, context):
    body = json.loads(event.get("body") or "{}")
    question = body.get("question", "") # get the question/query
    k = int(body.get("k", 5))  
    # if no question return 400         
    if not question:
        return {"statusCode": 400, "body": json.dumps({"error": "question required"})}

    # call load to warm cache (_index/_meta are ready)
    _load() 
    
    qemb = np.array(embed_texts([question])[0], dtype="float32")    # get embedding for question
    dists, inds = search_index(_index, qemb, k=k)                   # cosine similarity search (return top k)
    
    contexts = [] 
    chunks = []
                                                       
    # build sources for each (score, idx) 
    # looks up _meta[idx] and returns minimal citation info
    for score, idx in zip(dists, inds):
        md = _meta.get(str(int(idx)), {})
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
            }
        ),
    }