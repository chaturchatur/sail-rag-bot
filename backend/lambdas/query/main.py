# backend/lambdas/query/main.py

import os, json, tempfile
import numpy as np
from backend.shared import download_object, load_index, load_metadata, embed_texts, search_index

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
INDEX_PREFIX = f"{NAMESPACE}/index"

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
    sources = []                                                    
    # build sources for each (score, idx) 
    # looks up _meta[idx] and returns minimal citation info
    for score, idx in zip(dists, inds):
        md = _meta.get(str(int(idx)), {})
        sources.append({"source": md.get("source"), "page": md.get("page"), "score": float(score)})

    # for now just return nearest chunks
    # will add chat() to produce actual answer later lol
    return {"statusCode": 200, "body": json.dumps({"answer": None, "chunks": sources})}