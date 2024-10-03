import streamlit as st

from utils.feedback import create_feedback_entry
from utils.data_models import ChatHistoryEntry


def process_user_input(user_input: str):
    agent = st.session_state.agent
    model = st.session_state.model
    with st.chat_message("assistant", avatar="🚍"):
        with st.spinner(f"Processing your request with {model}..."):
            retry_code = st.session_state.retry_code
            result, success, error, only_text, llm_response, final_response, validation_response = agent.run_workflow(user_input, retry_code)

        if not success and error == "LLM call failed":
            st.error("Something went wrong. Please try again.")
            chat_entry = ChatHistoryEntry(
                role="assistant",
                final_response="Something went wrong. Please try again.",
                error_message=error,
                code_response=None,
            )
        else:
            chat_entry = ChatHistoryEntry(
                role="assistant",
                final_response=final_response,
                code_response=llm_response,  # Using final_response as code_response
                code_output=result,
                eval_success=success,
                error_message=error,
                only_text=only_text,
            )
            st.session_state.chat_history.append(chat_entry.dict())

            # Add feedback for the new assistant message
            create_feedback_entry(
                user_input,
                agent,
                final_response,
                success,
                result,
                error,
                final_response,
            )


def process_cancellation():
    chat_entry = ChatHistoryEntry(
        role="assistant",
        final_response="The operation was cancelled.",
        only_text=True,
        is_cancelled=True,
    )
    st.session_state.chat_history.append(chat_entry.dict())
    st.info("The operation was cancelled.")
