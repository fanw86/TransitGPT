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
    st.rerun()

# Display dialog when message limit is reached
if st.session_state["show_limit_popup"]:
    st.session_state["is_chat_input_disabled"] = True
    clear_chat()

# User input
user_input = st.chat_input(
    "Type your message here...",
    disabled=st.session_state.is_processing,
    key="chat_input",
)

# Display sample questions above the message bar only if it's the first question
if not st.session_state.first_question_asked and not user_input:
    st.write("Sample Questions:")
    for i, question in enumerate(st.session_state.questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            st.session_state.first_question_asked = True
            st.rerun()

# Process user input or selected question
if user_input or st.session_state.selected_question:
    # Disable chat input after user input
    st.session_state["is_processing"] = True

    if st.session_state.selected_question:
        print(st.session_state.selected_question)
        user_input = st.session_state.selected_question
        st.session_state.selected_question = None

    st.session_state.first_question_asked = True
    # st.rerun()

if st.session_state.is_processing:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.write(user_input)

    # Initialize local variables
    model = st.session_state["model"]
    agent = st.session_state["agent"]
    fb_agent = st.session_state["fb_agent"]
    retry_code_toggle = st.session_state["retry_code"]

    with st.chat_message("assistant", avatar="🚍"):
        with st.spinner(f"Getting response from {model}..."):
            system_prompt = st.session_state["SYSTEM_PROMPT"]
            llm_response, call_success = agent.call_llm(
                system_prompt, user_input, st.session_state["model"]
            )

        if not call_success:
            st.error("Something went wrong with the model. Please try again or try another model.")
            st.session_state.is_processing = False
            st.rerun()

        code_output, eval_success, error_message, only_text, final_response = (
            None,
            False,
            None,
            False,
            llm_response,
        )
        with st.status("Evaluating code..."):
            if retry_code_toggle:
                (
                    code_output,
                    eval_success,
                    error_message,
                    only_text,
                    new_llm_response,
                ) = agent.evaluate_with_retry(st.session_state["model"], llm_response)
                llm_response = new_llm_response
            else:
                code_output, eval_success, error_message, only_text = agent.evaluate(
                    llm_response
                )

        if eval_success and (code_output is not None):
            final_response, call_success = agent.call_final_llm()  # Call final LLM

    chat_entry = ChatHistoryEntry(
        role="assistant",
        final_response=final_response,
        code_response=llm_response,
        code_output=code_output,
        eval_success=eval_success,
        error_message=error_message,
        only_text=only_text,
    )
    # Add the new assistant message to the chat history
    st.session_state.chat_history.append(chat_entry.dict())

    # Add feedback for the new assistant message
    message_id = f"{st.session_state.uuid}_{len(st.session_state.chat_history) - 1}"
    st.session_state.current_message_id = message_id

    feedback_entry = create_feedback_entry(
        user_input, llm_response, eval_success, code_output, error_message
    )
    # Store comprehensive feedback
    fb_agent.db.collection(fb_agent.collection_name).document(message_id).set(
        feedback_entry.dict()
    )
    # agent.reset()
    # Set processing state back to False
    st.session_state.is_processing = False
    st.rerun()
