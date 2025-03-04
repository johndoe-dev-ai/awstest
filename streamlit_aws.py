import streamlit as st
import boto3
import json

def call_bedrock_agent(prompt):
    """Calls the Amazon Bedrock agent with the given prompt."""
    client = boto3.client("bedrock-runtime")
    response = client.invoke_model(
        modelId="anthropic.claude-v2",  # Replace with the appropriate model
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"prompt": prompt, "max_tokens": 200})
    )
    
    response_body = json.loads(response["body"].read().decode("utf-8"))
    return response_body.get("completion", "Error: No response received.")

# Streamlit UI
st.title("Bedrock Chatbot")
st.write("Chat with an AI powered by Amazon Bedrock!")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Chat Input
user_input = st.text_input("You:", "", key="user_input")
if st.button("Send") and user_input:
    response = call_bedrock_agent(user_input)
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", response))

# Display Chat History
for speaker, text in st.session_state.chat_history:
    st.write(f"**{speaker}:** {text}")
