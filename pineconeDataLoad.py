import os
import json
import time
from tqdm import tqdm
import dotenv
from openai import OpenAI, OpenAIError, RateLimitError
from pinecone import Pinecone
import json
import re
import textwrap

# ---- Load environment variables ----
dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")

# ---- Initialize Pinecone ----
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(pinecone_index_name)

# ---- Initialize OpenAI client ----
openai_client = OpenAI(api_key=openai_api_key)


def clean_text(obj):
    if isinstance(obj, dict):
        return {k: clean_text(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_text(item) for item in obj]
    elif isinstance(obj, str):
        # Replace all types of whitespace (space, tab, newline) with a single space
        cleaned = re.sub(r'\s+', ' ', obj)
        return cleaned.strip()  # Remove leading/trailing spaces
    else:
        return obj
 

def uploadFileOnPonecone(input_path):
    print(f"📥 Uploading file to Pinecone: {input_path}")
    
    # ---- Load the chunked JSON ----
    with open(input_path, "r", encoding="utf-8") as f:
        raw_docs = json.load(f)
        
    print(f"📦 Loaded {len(raw_docs)} chunks for embedding.")
    
    cleaned_data = clean_text(raw_docs)
    
    with open('cleaned_file.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print("Cleaned JSON saved as cleaned_file.json")
    
    with open("cleaned_file.json", "r", encoding="utf-8") as f:
        raw_dict = json.load(f)

    chunked_docs = []
    chunk_size = 1000
    for url, content in raw_dict.items():
        chunks = textwrap.wrap(content, width=chunk_size, break_long_words=False)
        for i, chunk in enumerate(chunks):
            chunked_docs.append({
                "id": f"{url}#chunk-{i}",
                "url": url,
                "text": chunk
            })
            
        
    
    # ---- Prepare vectors for Pinecone ----
    vectors = []
    MAX_CHARS = 8000
    print("🔄 Generating embeddings...")
    for doc in tqdm(chunked_docs, desc="Embedding chunks"):
        # print("Processing chunk: ", doc)
        vector_id = doc["id"]  # Unique ID like url#chunk-0
        embedding = get_embedding(doc["text"])  # 1536-dim vector
        metadata = {
            "url": doc["url"],  # Store original URL
            "text": doc["text"][:500]  # Store partial text (limit size in metadata)
        }
        vectors.append((vector_id, embedding, metadata))
    
    # ---- Upsert in Batches ----
    batch_size = 100  # Recommended batch size
    print("⬆️ Upserting vectors to Pinecone...")
    for i in tqdm(range(0, len(vectors), batch_size), desc="Upserting batches"):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
    
    print("✅ All embeddings successfully upserted to Pinecone.")
    
    # ---- Function: Get OpenAI Embedding ----
def get_embedding(text, model="text-embedding-ada-002", max_retries=5):
    """Fetch embedding for a given text using OpenAI API."""
    for attempt in range(max_retries):
        try:
            response = openai_client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except RateLimitError:
            print("⚠️ OpenAI rate limit hit. Retrying in 5 seconds...")
            time.sleep(5)
        except OpenAIError as e:
            print(f"❌ OpenAI error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
    raise RuntimeError("Failed to get embedding after retries.")
