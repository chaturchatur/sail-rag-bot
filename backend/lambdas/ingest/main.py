# backend/lambdas/ingest/main.py
# only .txt for now

import os, json, tempfile
import numpy as np
from backend.shared import list_objects, download_object, extract_txt, chunk_text, embed_texts, create_index, add_vectors, save_index, create_metadata, save_metadata, upload_file

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
INDEX_PREFIX = f"{NAMESPACE}/index"

def handler(event, context):
    # list all objects under /uploads and only keep .txt (for now)
    keys = [k for k in list_objects(BUCKET, f"{NAMESPACE}/uploads/") if k.endswith(".txt")]
    all_chunks = [] # storing chunks
    # for each upload key
    for key in keys:
        # reserve temp file path in /tmp
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            download_object(BUCKET, key, tf.name)               # pull s3 object to temp path
            with open(tf.name, "rb") as f:                      # read .txt file
                text = extract_txt(f.read())                    # decode text 
        chunks = chunk_text(text, chunk_size=1000, overlap=150) # split token sized chunks w overlap
        for c in chunks:
            c["source"] = key.rsplit("/", 1)[-1]                # attach filename as citation
        all_chunks.extend(chunks)                               # collect chunks

    # if nothing to ingest 
    if not all_chunks:
        return {"statusCode": 200, "body": json.dumps({"ok": True, "stats": {"chunks": 0}})}

    # embeddings + faiss
    embeddings = embed_texts([c["text"] for c in all_chunks])   # list[list[float]] = call openai embeddings for all chunks
    vecs = np.array(embeddings, dtype="float32")                # faiss needs float32 
    index = create_index(vecs.shape[1])                         # build indexflatip (brute force over all vec w inner product)
    add_vectors(index, vecs)                                    # normalize + add vectors

    meta = create_metadata(all_chunks)                          # dict mapping vector ids into chunk info (text, source)
    # allocates two real temp files on lmabda for faiss and metadata
    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        save_index(index, idxf.name)                                    # write into faiss.index
        save_metadata(meta, mf.name)                                    # write meta.json
        upload_file(idxf.name, BUCKET, f"{INDEX_PREFIX}/faiss.index")   # upload index to s3 bucket
        upload_file(mf.name, BUCKET, f"{INDEX_PREFIX}/meta.json")       # upload metadata to s3 bucket

    return {"statusCode": 200, 
            "body": json.dumps({"ok": True, "stats": {"chunks": len(all_chunks)}})
            }
    