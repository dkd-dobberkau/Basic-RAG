
from dotenv import load_dotenv
import streamlit as st
from typing import Literal
import os

# Loading assistants 
def load_assistants() -> dict[str, str]:
    dirname = os.path.dirname(__file__)
    contexts_dir = os.path.join(dirname, "contexts")
    assistants = {}

    for file in os.listdir(contexts_dir):
        name = str(os.path.basename(file)).removesuffix(".txt")
        with open(os.path.join(contexts_dir, file)) as context:
            assistants[name] = context.read()
    return assistants

# State handling
if 'initialized' not in st.session_state:
    load_dotenv()
    # api_key = os.environ.get('API_KEY') if needed
    st.session_state["assistants"] = load_assistants()
    st.session_state["selected_assistant"] = "Tutor"
    st.session_state["messages"] = []
    st.session_state["initialized"] = True

# Communication
def send_prompt():
    if st.session_state.prompt:
        prompt = str(st.session_state.prompt).strip()

        if prompt.lower() == "/clear":
            reset_context()
        elif len(prompt) > 0:
            add_message(prompt, "user")
            # TODO API call
            add_message("Maga hogy ballagott el a kiscsoportból?", "ai")

def add_message(prompt : str, sender : Literal["user", "assistant", "ai", "human"] | str,):
    st.session_state.messages.append({ 'content': prompt, 'sender':  sender })

def reset_context():
    st.session_state.messages = []
    # TODO API call

def set_assistant():
    reset_context()

    assistant_context = st.session_state.assistants[st.session_state.selected_assistant]
    #print(assistant_context)
    # TODO API call

# UI
st.set_page_config(
    page_title="db_bot"
    # set favicon here
)

selected_option = st.selectbox(
    "Bot:", 
    key="selected_assistant", 
    options=list(st.session_state.assistants.keys()),
    on_change=lambda: set_assistant()
)

for message in st.session_state.messages:
    with st.chat_message(message['sender']):
        st.write(message["content"])

prompt = st.chat_input(
    "Say something", 
    key="prompt",
    on_submit=lambda: send_prompt()
)

# st.connection()
# with st.status("Downloading data..."):
#    st.write("Searching for data...")
#    time.sleep(2)
#    st.write("Downloading data...")
#    time.sleep(1)

# def stream_data():
#    _LOREM_IPSUM = "Lorem ipsum dolor sit amet, **consectetur adipiscing** elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
#    for word in _LOREM_IPSUM.split(" "):
#        yield word + " "
#        time.sleep(0.02)

# if st.button("Stream data"):
#    st.write_stream(stream_data)
