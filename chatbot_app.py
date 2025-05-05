import streamlit as st
import requests

st.set_page_config(page_title="Chatbot", layout="centered")

# query_params = st.experimental_get_query_params()
token = st.query_params.get("token")

if not token:
    st.markdown(f'<meta http-equiv="refresh" content="0;URL=http://localhost:8000/login">', unsafe_allow_html=True)
    st.stop()

#st.write(f"Token being sent: {token}")
verify_response = requests.get("http://localhost:8000/verify", params={"token": token})
print("Verify response:", verify_response)  # Debug: print the response

try:
    verify_json = verify_response.json()
except Exception:
    st.error("Authentication failed. Please try again.")
    st.stop()

if not verify_response.ok or not verify_json.get("valid"):
    st.error("Authentication failed. Please try again.")
    st.stop()

user = verify_json.get("user")
st.success(f"Welcome {user['email']} 👋")
st.title("🤖 Chatbot Interface")

# Placeholder chatbot UI
user_input = st.text_input("Say something to the bot")
if user_input:
    st.write(f"Bot says: I heard you say '{user_input}'")

