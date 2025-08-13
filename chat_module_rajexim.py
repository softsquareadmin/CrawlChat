import os
import dotenv
from pinecone import Pinecone
from openai import OpenAI, OpenAIError
 
# ---- Load environment variables ----
dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = 'pcsk_2zFtu7_CCrzdNi1kDibn3o2X7ibk3mmzQ7dginSGvrLnuB82ExXobsVHqiB8v5uxpkT156'
pinecone_index_name = 'rajexim'
 
# ---- Initialize clients ----
openai_client = OpenAI(api_key=openai_api_key)
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(pinecone_index_name)
 
# ---- Functions ----
def embed_query(text):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding
 
def search_pinecone(query_embedding, top_k=5):
    return index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )['matches']
 
def generate_gpt_reply(chat_history, context, user_input):
    system_prompt = (
        "You are a helpful assistant. "
        "Use the provided context from their website to answer questions. "
        "If the context doesn't have enough info, say you don't know."
        "Respond in clear, professional language. "
        "Use markdown formatting where appropriate: "
        "- Bold important words\n"
        "- Use bullet points for lists\n"
        "- Keep answers concise and uniform\n"
        "- Add line breaks between paragraphs for readability\n"
        "Respond only within the context of the provided information."
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages += chat_history
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_input}"})
 
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content.strip()
 
 