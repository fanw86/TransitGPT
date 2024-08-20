import streamlit as st

## Custom imports
from utils.feedback import create_feedback_entry
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
from utils.data_models import ChatHistoryEntry


def get_final_response(agent, eval_success: bool, code_output):
    if eval_success and code_output is not None:
        final_response, call_success = agent.call_final_llm()
        if call_success:
            return final_response
    return "Something went wrong. Please try again."


def process_user_input(user_input: str):
    agent = st.session_state.agent
    retry_code = st.session_state.retry_code
    model = st.session_state.model
    with st.chat_message("assistant", avatar="🚍"):
        with st.spinner(f"Getting response from {model}..."):
            llm_response, call_success = agent.call_llm(user_input)
            if not call_success:
                st.error("Something went wrong. Please try again.")
                return

        code_output, eval_success, error_message, only_text, llm_response = agent.evaluate_code(
            retry_code, llm_response
        )
        with st.spinner("Almost there..."):
            final_response = get_final_response(agent, eval_success, code_output)

    chat_entry = ChatHistoryEntry(
        role="assistant",
        final_response=final_response,
        code_response=llm_response,
        code_output=code_output,
        eval_success=eval_success,
        error_message=error_message,
        only_text=only_text,
    )
    st.session_state.chat_history.append(chat_entry.dict())

    # Add feedback for the new assistant message
    create_feedback_entry(
        user_input, agent, llm_response, eval_success, code_output, error_message
    )


# Set the page to wide mode
st.set_page_config(layout="wide")

# Call this function at the beginning of your Streamlit app
load_session_state()
# Setup sidebar
setup_sidebar()

# Initialize agent, evaluator and prompt with default GTFS feed
if "agent" not in st.session_state:
    print("Initializing Chat App...")
    load_agent_evaluator()

# Chat interface
st.title("🚌GTFS2CODE")
# Display chat history
display_chat_history(st.session_state["fb_agent"], st.session_state.uuid)

# Check if the number of messages has reached the limit
if len(st.session_state.chat_history) >= MAX_MESSAGES:
    st.session_state.show_limit_popup = True

# Display dialog when message limit is reached
if st.session_state["show_limit_popup"]:
    st.session_state["is_chat_input_disabled"] = True
    clear_chat()


# User input
user_input = st.chat_input(
    "Type your message here...",
    disabled=st.session_state.is_processing or st.session_state.is_chat_input_disabled,
)

# Display sample questions above the message bar only if it's the first question
if not st.session_state.first_question_asked and not user_input:
    st.write("Sample Questions:")
    for i, question in enumerate(st.session_state.questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            st.session_state.first_question_asked = True

# Process user input or selected question
if user_input or st.session_state.selected_question:
    # Disable chat input after user input
    st.session_state["is_processing"] = True

    if st.session_state.selected_question:
        print(st.session_state.selected_question)
        user_input = st.session_state.selected_question
        st.session_state.selected_question = None

    st.session_state.first_question_asked = True
    st.session_state["user_input"] = user_input
    st.rerun()

if st.session_state.is_processing:
    user_input = st.session_state["user_input"]
    st.session_state.is_processing = True
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.write(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    process_user_input(user_input)
    st.session_state.is_processing = False
    st.rerun()
