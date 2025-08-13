import streamlit as st
from chat_module import embed_query, search_pinecone, generate_gpt_reply, OpenAIError
 
# ---- Streamlit Page Config ----
# st.set_page_config(page_title="Softsquare AI Chatbot", layout="centered")
# st.title("Softsquare AI Chatbot")
# st.title("AI Chatbot")
st.markdown("""
    <h1 id="chat-header" style="position: fixed;
                   top: 0;
                   left: 0;
                   width: 100%;
                   text-align: center;
                   background-color: #f1f1f1;
                   z-index: 9
                  ">
        AI Chatbot
    </h1>
    
""", unsafe_allow_html=True)

 
# ---- CSS ----
st.markdown("""
    <style>
    .fixed-title {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background: rgba(240, 242, 246, 1);
        border-bottom: 1px solid #ddd;
        padding: 1rem;
        z-index: 999;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: Black;
        text-shadow:
            -1px -1px 0 White,
            1px -1px 0 White,
            -1px  1px 0 White,
            1px  1px 0 White;
    }
    .user-message { display: flex; justify-content: flex-end; }
    .bot-message { display: flex; justify-content: flex-start; }
    .chat-bubble {
        max-width: 70%;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        word-wrap: break-word;
    }
    .user-bubble { background-color: #0084ff; color: white; }
    .bot-bubble { background-color: #f1f0f0; color: black; }
    </style>
""", unsafe_allow_html=True)
 
# st.markdown('<div class="fixed-title">AI Chatbot</div>', unsafe_allow_html=True)
 
 
# ---- Custom Avatars ----
USER_AVATAR = "pages/userlogo.jpeg"        # Local file or full URL
BOT_AVATAR = "pages/chatbotlogo.jpeg"      # Local file or full URL
 
# ---- Session State ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_bot_reply" not in st.session_state:
    st.session_state.pending_bot_reply = None
 
 
# ---- Display chat ----
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.chat_history:
        css_class = "user-message" if msg["role"] == "user" else "bot-message"
        bubble_class = "user-bubble" if msg["role"] == "user" else "bot-bubble"
        st.markdown(f"""
            <div class="{css_class}">
                <div class="chat-bubble {bubble_class}">
                    {msg["content"]}
                </div>
            </div>
        """, unsafe_allow_html=True)
 
    if st.session_state.pending_bot_reply:
        st.markdown("""
            <div class="bot-message">
                <div class="chat-bubble bot-bubble">
                    <em>Processing...</em>
                </div>
            </div>
        """, unsafe_allow_html=True)
 
# ---- User input ----
user_input = st.chat_input("Type your message here...")
if user_input:
    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
    # Set pending bot reply
    st.session_state.pending_bot_reply = user_input.strip()
    st.rerun()  # <-- Forces UI update to show "Processing..."
 
# ---- Generate reply after rerun ----
if st.session_state.pending_bot_reply and not user_input:
    try:
        query_embedding = embed_query(st.session_state.pending_bot_reply)
        results = search_pinecone(query_embedding, top_k=5)
        context = "\n\n".join([m['metadata']['text'] for m in results])
        bot_reply = generate_gpt_reply(
            st.session_state.chat_history,
            context,
            st.session_state.pending_bot_reply
        )
    except OpenAIError as e:
        bot_reply = f"OpenAI Error: {e}"
    except Exception as ex:
        bot_reply = f"Error: {ex}"
 
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    st.session_state.pending_bot_reply = None
    st.rerun()  # <-- Updates UI with final reply