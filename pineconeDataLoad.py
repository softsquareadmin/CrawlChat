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
 
    # ---- Reset Pinecone Index ----
    try:
        print("🧹 Checking Pinecone index before clearing...")

        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index(pinecone_index_name)

        # Get current stats
        stats = index.describe_index_stats()
        total_vectors = stats.get("total_vector_count", 0)

        if total_vectors == 0:
            print("ℹ️ Index is already empty. No deletion needed.")
        else:
            print(f"📦 Found {total_vectors} vectors. Proceeding to clear...")
            try:
                # Loop through all namespaces to delete
                for namespace in stats.get("namespaces", {}).keys():
                    print(f"🗑 Deleting namespace: '{namespace or 'default'}' ...")
                    index.delete(delete_all=True, namespace=namespace)
                print("✅ Pinecone index cleared.")
            except Exception as e:
                print(f"⚠️ Failed to clear index: {e}")

        # Show stats after action
        print(index.describe_index_stats())
    except Exception as e:
        print(f"⚠️ Failed to clear index: {e}")
        return
 
    # ---- Load & clean the JSON ----
    with open(input_path, "r", encoding="utf-8") as f:
        raw_docs = json.load(f)
    print(f"📦 Loaded {len(raw_docs)} chunks for embedding.")
   
    cleaned_data = clean_text(raw_docs)
    with open('cleaned_file.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    print("✅ Cleaned JSON saved as cleaned_file.json")
   
    # ---- Load cleaned data ----
    with open("cleaned_file.json", "r", encoding="utf-8") as f:
        raw_dict = json.load(f)
 
    # ---- Chunk content ----
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
 
    # ---- Prepare vectors ----
    vectors = []
    print("🔄 Generating embeddings...")
    for doc in tqdm(chunked_docs, desc="Embedding chunks"):
        vector_id = doc["id"]
        embedding = get_embedding(doc["text"])
        metadata = {
            "url": doc["url"],
            "text": doc["text"][:500]
        }
        vectors.append((vector_id, embedding, metadata))
 
    # ---- Upsert in Batches ----
    batch_size = 100
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
