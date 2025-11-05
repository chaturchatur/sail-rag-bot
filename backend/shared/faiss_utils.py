# efficient approx nearest neighbour search with indexes (cosine similarity)
# build and search vector indexes for fast semantic search
import faiss
import numpy as np
from typing import List, Tuple, Dict, Any
import json
import os

# creates FAISS index
# exact search via inner product on normalized vectors
def create_index(dimension: int):
    # IndexFlatIP = inner product on normalized vectors (cosine similarity)
    index = faiss.IndexFlatIP(dimension)
    return index

# add vectors to FAISS index
# normalizes vectors and adds them to the index for cosine similarity
def add_vectors(index: faiss.Index, vectors: np.ndarray):
    # FAISS needs contiguous data
    if not vectors.flags['C_CONTIGUOUS']:
        vectors = np.ascontiguousarray(vectors)
    
    # normalize for cosine similarity
    faiss.normalize_L2(vectors)
    index.add(vectors)

# find the nearest k vectors to a query
def search_index(index: faiss.Index, query_vector: np.ndarray, k: int = 5):
    # normalize query vector
    query_vector = query_vector.reshape(1, -1)
    faiss.normalize_L2(query_vector)
    
    distances, indices = index.search(query_vector, k)
    
    return distances[0], indices[0]

# save FAISS index to the disk
def save_index(index: faiss.Index, path: str):
    faiss.write_index(index, path)

# loads FAISS index from disk
def load_index(path: str) -> faiss.Index:
    return faiss.read_index(path)

# maps vector indices to chunk metadata 
# to source for retrieval and citations
def create_metadata(chunks: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    metadata = {}
    for i, chunk in enumerate(chunks):
        metadata[i] = {
            'text': chunk.get('text', ''),
            'source': chunk.get('source', ''),
            'page': chunk.get('page', None),
            'start_index': chunk.get('start_index', 0)
        }
    return metadata

# save metadata to json
def save_metadata(metadata: Dict[int, Dict[str, Any]], path: str):
    with open(path, 'w') as f:
        json.dump(metadata, f, indent=2)

# loads metadata from json
def load_metadata(path: str):
    with open(path, 'r') as f:
        return json.load(f)

# loads an existing index and adds new vectors in place
# in case of new uploads, ingest adds new chunks without any rebuild
def merge_indexes(existing_index_path: str, new_vectors: np.ndarray, 
                  new_metadata: Dict[int, Dict[str, Any]],
                  dimension: int):

    # load existing
    if os.path.exists(existing_index_path):
        index = load_index(existing_index_path)
        metadata = load_metadata(existing_index_path.replace('faiss.index', 'meta.json'))
        next_id = max(metadata.keys()) + 1 if metadata else 0
    else:
        index = create_index(dimension)
        metadata = {}
        next_id = 0
    
    # add new vectors
    add_vectors(index, new_vectors)
    
    # update metadata
    for i, item in new_metadata.items():
        metadata[next_id] = item
        next_id += 1
    
    return index, metadata