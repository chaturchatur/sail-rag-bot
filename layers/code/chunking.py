# breaking docs int manageable pieces for vector search and retrieval
from typing import List, Dict
import tiktoken
import pypdf
from io import BytesIO

# counts tokens in text for chunking sizing and api limits
# using gpt-4 tokenzier
def count_tokens(text: str, model: str = "gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

# splits into sentences (sentences first for semantic coherence)
# build chunks within size limits
# duplicates overlaps at boundaries (to preserve context across chunks)
# remaining text becomes final chunk
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150):
    enc = tiktoken.encoding_for_model("gpt-4")
    
    # split by sentences first for better chunks
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_tokens = 0
    start_idx = 0
    
    for sentence in sentences:
        sentence_tokens = len(enc.encode(sentence))
        
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            # save current chunk
            chunk_text = '. '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'start_index': start_idx,
                'tokens': current_tokens
            })
            
            # start new chunk with overlap
            overlap_sentences = []
            overlap_tokens = 0
            for s in reversed(current_chunk):
                t = len(enc.encode(s))
                if overlap_tokens + t <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            
            current_chunk = overlap_sentences
            current_tokens = overlap_tokens
            start_idx += len(chunk_text) - sum(len(s) for s in overlap_sentences)
        
        current_chunk.append(sentence)
        current_tokens += sentence_tokens
    
    # add final chunk
    if current_chunk:
        chunks.append({
            'text': '. '.join(current_chunk),
            'start_index': start_idx,
            'tokens': current_tokens
        })
    
    return chunks

# extracts text from pdf files
# gets text per page and joins it
def extract_pdf(pdf_bytes: bytes):
    try:
        # turn pdf into in memory file object
        # mimics open() without a real file
        # lets pdf reader read without the actual file
        # bytesio creates readable stream from which pdfreader reads from = extracts text
        pdf_file = BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(pdf_file)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise

# decodes utf-8 bytes into a string
# utf-8 cover (ascii/english/unicode)
def extract_txt(text_bytes: bytes):
    try:
        return text_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error decoding text: {e}")
        raise