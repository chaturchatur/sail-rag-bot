# exposes shared utilities for lambda functions
# simplifies imports by grouping modules

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

from .dynamodb_utils import (
    get_resource,
    get_table,
)

from .message_utils import (
    save_message,
    get_messages,
    openai_messages,
)

# define what is available when importing * from this package
__all__ = [
    # s3 utils
    "get_s3_client",
    "generate_put_url",
    "download_object",
    "upload_file",
    "list_objects",
    "if_object",
    "get_etag",
    
    # openai utils
    "get_openai_key",
    "get_openai_client",
    "embed_texts",
    "chat",
    
    # text processing utils
    "count_tokens",
    "chunk_text",
    "extract_pdf",
    "extract_txt",
    
    # vector search utils
    "create_index",
    "add_vectors",
    "search_index",
    "save_index",
    "load_index",
    "create_metadata",
    "save_metadata",
    "load_metadata",
    "merge_indexes",
    
    # message history utils
    "save_message",
    "get_messages",
    "openai_messages",
    
    # database utils
    "get_resource",
    "get_table",
]
