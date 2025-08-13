import streamlit as st
from chat_module import embed_query, search_pinecone, generate_gpt_reply, OpenAIError
 
# ---- Streamlit Page Config ----
st.set_page_config(page_title="Softsquare AI Chatbot", layout="centered")
st.title("Softsquare AI Chatbot")
 
# ---- Custom CSS for Fixed Input ----
st.markdown("""
    <style>
    .stTextInput {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        max-width: 800px;
        width: 100%;
        border-top: 1px solid #ddd;
        z-index: 999;
    }
    .block-container {
        padding-bottom: 90px;
    }
    .st-emotion-cache-1mph9ef {
        flex-direction: row-reverse;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)
 
# ---- Custom Avatars ----
USER_AVATAR = "pages/userlogo.jpeg"        # Local file or full URL
BOT_AVATAR = "pages/chatbotlogo.jpeg"      # Local file or full URL
 
# ---- Initialize Session State ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
 
# ---- Chat Input Box Callback ----
def on_send(user_input):
    if user_input.strip() == "":
        st.warning("Please type a question.")
        return
 
    # Append user message
    st.session_state.chat_history.append({"role": "user", "content": user_input})
 
    # Process bot reply
    with st.spinner("Processing..."):
        try:
            query_embedding = embed_query(user_input)
            results = search_pinecone(query_embedding, top_k=5)
            context = "\n\n".join([m['metadata']['text'] for m in results])
            bot_reply = generate_gpt_reply(st.session_state.chat_history, context, user_input)
        except OpenAIError as e:
            bot_reply = f"OpenAI Error: {e}"
        except Exception as ex:
            bot_reply = f"Error: {ex}"
 
    # Append bot reply
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
 
    # Clear input box after sending
    st.session_state.user_input = ""
 
# ---- Display Chat History (Left Bot, Right User) ----
for msg in st.session_state.chat_history:
    avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
    # role = "user" if msg["role"] == "user" else "assistant"
    # with st.chat_message(role, avatar=avatar):
    #     st.write(msg["content"])
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
 
# ---- Fixed Input Box at Bottom ----
st.text_input(
    "Your Message",
    value=st.session_state.user_input,
    placeholder="Type your message here...",
    label_visibility="collapsed",
    key="user_input",
    on_change=lambda: on_send(st.session_state.user_input)
)