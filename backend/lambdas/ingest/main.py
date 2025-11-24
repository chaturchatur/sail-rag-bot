import datetime
import json
import os
import tempfile

import numpy as np

from backend.shared import (
    add_vectors,
    chunk_text,
    create_index,
    create_metadata,
    download_object,
    embed_texts,
    extract_pdf,
    extract_txt,
    get_s3_client,
    list_objects,
    save_index,
    save_metadata,
    upload_file,
)

# get bucket name, namespace from env vars
BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default") # default to "default"
# session prefix path
SESSION_PREFIX = f"{NAMESPACE}/sessions"


def handler(event, context):
    # parse the request body from json str
    body = json.loads(event.get("body") or "{}")

    # get session id from body
    session_id = body.get("sessionId")
    # check if session id is provided
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }

    # prefixes for uploads and index
    upload_prefix = f"{SESSION_PREFIX}/{session_id}/uploads/"
    index_prefix = f"{SESSION_PREFIX}/{session_id}/index"

    # list all text and pdf files in the upload directory
    keys = [
        k
        for k in list_objects(BUCKET, upload_prefix)
        if k.endswith((".txt", ".pdf"))
    ]

    # list to store all text chunks
    all_chunks = []
    for key in keys:
        # temporary file to download object
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            download_object(BUCKET, key, tf.name)
            # read and extract text from downloaded file
            with open(tf.name, "rb") as f:
                content = f.read()
                if key.endswith(".pdf"):
                    text = extract_pdf(content)
                else:
                    text = extract_txt(content)

        # split text into chunks with overlap (for context)
        chunks = chunk_text(text, chunk_size=1000, overlap=150)
        # add source info to each chunk
        for c in chunks:
            c["source"] = key.rsplit("/", 1)[-1]
        # add chunks to the main list
        all_chunks.extend(chunks)

    # check if no chunks were found
    if not all_chunks:
        # stats dict with zero chunks
        stats = {
            "sessionId": session_id,
            "chunks": 0,
            "lastIngestedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # upload stats to s3
        get_s3_client().put_object(
            Bucket=BUCKET,
            Key=f"{index_prefix}/stats.json",
            Body=json.dumps(stats).encode("utf-8"),
            ContentType="application/json",
        )

        # return success response with stats
        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True, "stats": stats}),
        }

    # generate embeddings for all chunks
    embeddings = embed_texts([c["text"] for c in all_chunks])
    vecs = np.array(embeddings, dtype="float32") # to numpy array
    # create faiss index
    index = create_index(vecs.shape[1])
    # add vectors to the index
    add_vectors(index, vecs)

    # create metadata for the chunks
    meta = create_metadata(all_chunks)

    # save index and metadata to temporary files
    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        save_index(index, idxf.name)
        save_metadata(meta, mf.name)
        # upload index and metadata to s3
        upload_file(idxf.name, BUCKET, f"{index_prefix}/faiss.index")
        upload_file(mf.name, BUCKET, f"{index_prefix}/meta.json")

    # updated stats dict
    stats = {
        "sessionId": session_id,
        "chunks": len(all_chunks),
        "lastIngestedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sources": sorted({c["source"] for c in all_chunks if c.get("source")}),
    }

    # upload updated stats to s3
    get_s3_client().put_object(
        Bucket=BUCKET,
        Key=f"{index_prefix}/stats.json",
        Body=json.dumps(stats).encode("utf-8"),
        ContentType="application/json",
    )

    # return success response with stats
    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "stats": stats}),
    }
