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
    extract_txt,
    get_s3_client,
    list_objects,
    save_index,
    save_metadata,
    upload_file,
)

BUCKET = os.environ["BUCKET"]
NAMESPACE = os.environ.get("NAMESPACE", "default")
SESSION_PREFIX = f"{NAMESPACE}/sessions"


def handler(event, context):
    body = json.loads(event.get("body") or "{}")

    session_id = body.get("sessionId")
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sessionId required"}),
        }

    upload_prefix = f"{SESSION_PREFIX}/{session_id}/uploads/"
    index_prefix = f"{SESSION_PREFIX}/{session_id}/index"

    keys = [
        k
        for k in list_objects(BUCKET, upload_prefix)
        if k.endswith(".txt")
    ]

    all_chunks = []
    for key in keys:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            download_object(BUCKET, key, tf.name)
            with open(tf.name, "rb") as f:
                text = extract_txt(f.read())

        chunks = chunk_text(text, chunk_size=1000, overlap=150)
        for c in chunks:
            c["source"] = key.rsplit("/", 1)[-1]
        all_chunks.extend(chunks)

    if not all_chunks:
        stats = {
            "sessionId": session_id,
            "chunks": 0,
            "lastIngestedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        get_s3_client().put_object(
            Bucket=BUCKET,
            Key=f"{index_prefix}/stats.json",
            Body=json.dumps(stats).encode("utf-8"),
            ContentType="application/json",
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True, "stats": stats}),
        }

    embeddings = embed_texts([c["text"] for c in all_chunks])
    vecs = np.array(embeddings, dtype="float32")
    index = create_index(vecs.shape[1])
    add_vectors(index, vecs)

    meta = create_metadata(all_chunks)

    with tempfile.NamedTemporaryFile(delete=False) as idxf, tempfile.NamedTemporaryFile(delete=False) as mf:
        save_index(index, idxf.name)
        save_metadata(meta, mf.name)
        upload_file(idxf.name, BUCKET, f"{index_prefix}/faiss.index")
        upload_file(mf.name, BUCKET, f"{index_prefix}/meta.json")

    stats = {
        "sessionId": session_id,
        "chunks": len(all_chunks),
        "lastIngestedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sources": sorted({c["source"] for c in all_chunks if c.get("source")}),
    }

    get_s3_client().put_object(
        Bucket=BUCKET,
        Key=f"{index_prefix}/stats.json",
        Body=json.dumps(stats).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "stats": stats}),
    }