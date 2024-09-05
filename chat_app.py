import streamlit as st

## Custom imports
from utils.response_processor import process_user_input, process_cancellation
from utils.constants import MAX_MESSAGES
from utils.state import load_session_state
from components.sidebar import (
    setup_sidebar,
    load_agent_evaluator,
)
from components.chat_interface import (
    display_chat_history,
    clear_chat,
)
from components.chat_input_box import set_chat_box

st.set_page_config(
    page_title="GTFS2CODE", page_icon="🚍", layout="wide", initial_sidebar_state="auto"
)

# Setup Session state variables at the beginning of your Streamlit app
load_session_state()
# Setup sidebar
setup_sidebar()

# Initialize agent, evaluator and prompt with default GTFS feed
if "agent" not in st.session_state:
    load_agent_evaluator()

# Chat interface
st.title("🚌GTFS2CODE")
# Display chat history
display_chat_history(st.session_state["fb_agent"], st.session_state.uuid)

# Check if the number of messages has reached the limit
if len(st.session_state.chat_history) >= MAX_MESSAGES:
    st.session_state["show_limit_popup"] = True

# Display dialog when message limit is reached
if st.session_state["show_limit_popup"]:
    st.session_state["is_chat_input_disabled"] = True
    clear_chat()

# Display sample questions only if it's the first question and no question has been selected
if not st.session_state.first_question_asked and not st.session_state.selected_question:
    st.write("Sample Questions:")
    for i, question in enumerate(st.session_state.questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            st.session_state.user_input = (
                question  # Set user_input when a question is selected
            )
            st.session_state.first_question_asked = (
                True  # Mark that a question has been selected
            )
            st.rerun()  # Rerun to remove the sample questions

if st.session_state.user_input:
    set_chat_box(st.session_state.user_input, len(st.session_state.chat_history))
elif st.session_state.selected_question:
    set_chat_box(st.session_state.selected_question, len(st.session_state.chat_history))
else:
    set_chat_box("", len(st.session_state.chat_history))

# Process user input
user_input = st.chat_input(
    "Type your query here...",
    disabled=st.session_state.is_processing or st.session_state.is_chat_input_disabled,
)
# Process user input or selected question
if user_input:
    # Use the edited input from the chat box
    st.session_state.user_input = user_input
    st.session_state.is_processing = True
    st.session_state.selected_question = None  # Clear the selected question

    if not st.session_state.first_question_asked:
        st.session_state.first_question_asked = True
    st.rerun()

if st.session_state.is_processing:
    user_input = st.session_state["user_input"]

    # Check if this input hasn't been added to chat history yet
    if not st.session_state.chat_history or (
        "final_response" in st.session_state.chat_history[-1]
    ):
        with st.chat_message("user", avatar="🙋‍♂️"):
            st.write(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Add a cancel button
    col1, col2 = st.columns([8, 1])
    with col2:
        cancel_button = st.button("⏹Stop")

    with col1:
        if cancel_button:
            st.session_state.is_processing = False
            st.session_state.user_input = None
            process_cancellation()
            st.rerun()
        else:
            process_user_input(user_input)
            # Clear the input box after processing
            st.session_state.user_input = None
            st.session_state.is_processing = False
            st.rerun()
