import streamlit as st
import sys
import asyncio
import os
from os.path import join
from dotenv import load_dotenv
from typing import Literal

# load OllamaClient
def init_client():
    current_dir = os.path.dirname(__file__)
    load_dotenv(join(current_dir, '..', '.env'))
    
    for dir in ["retrieval", "LLM"]:
        sys.path.append(join(current_dir, "..", dir))

    from retrieval import SolrHandler
    from LLM import OllamaClient

    solr_handler = SolrHandler(
        os.environ.get("SOLR_SERVER"),
        os.environ.get("CORE_NAME")
    )

    client = OllamaClient(
        os.environ.get("OLLAMA_SERVER"), 
        os.environ.get("OLLAMA_MODEL"),
        solr_handler
    )

    st.session_state["client"] = client

# State handling
if 'initialized' not in st.session_state:
    init_client()

    st.session_state["assistants"] = list(st.session_state.client.assistants)
    st.session_state["selected_assistant"] = "Tutor"
    st.session_state["messages"] = []
    st.session_state["initialized"] = True

# Communication
def add_message(prompt : str, sender : Literal["user", "assistant", "ai", "human"]):
    st.session_state.messages.append({ 'content': prompt, 'sender':  sender })

def reset_context():
    st.session_state.client.new_chat(st.session_state.selected_assistant)
    st.session_state.messages = []

# UI
st.set_page_config(
    page_title="db_bot",
    # TODO set favicon here
)

selected_option = st.selectbox(
    "Bot:", 
    key="selected_assistant", 
    options=st.session_state.assistants,
    on_change=lambda: reset_context()
)

for message in st.session_state.messages:
    with st.chat_message(message['sender']):
        st.markdown(message["content"])

if prompt := st.chat_input("Say something"):
    prompt = prompt.strip()

    if prompt.lower() == "/clear":
        reset_context()
    elif len(prompt) > 0:
        add_message(prompt, "user")

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            print('xd')
            response = st.write_stream(st.session_state.client.new_message(prompt))

        add_message(response, "ai")
