# backend/shared/__init__.py
# for stable packaging
# for lambda to import shared code reliably

from .s3_utils import (
    get_s3_client,
    generate_put_url,
    download_object,
    upload_file,
    list_objects,
    if_object,
    get_etag
)

from .openai_utils import (
    get_openai_key,
    get_openai_client,
    embed_texts,
    chat,
)

from .chunking import (
    count_tokens,
    chunk_text,
    extract_pdf,
    extract_txt,
)

from .faiss_utils import (
    create_index,
    add_vectors,
    search_index,
    save_index,
    load_index,
    create_metadata,
    save_metadata,
    load_metadata,
    merge_indexes,
)

from .message_utils import (
    save_message,
    get_messages,
    openai_messages,
)

__all__ = [
    # s3_utils
    "get_s3_client",
    "generate_put_url",
    "download_object",
    "upload_file",
    "list_objects",
    "if_object",
    "get_etag",
    # openai_utils
    "get_openai_key",
    "get_openai_client",
    "embed_texts",
    "chat",
    # chunking
    "count_tokens",
    "chunk_text",
    "extract_pdf",
    "extract_txt",
    # faiss_utils
    "create_index",
    "add_vectors",
    "search_index",
    "save_index",
    "load_index",
    "create_metadata",
    "save_metadata",
    "load_metadata",
    "merge_indexes",
    # message_utils
    "save_message",
    "get_messages",
    "openai_messages",
]