import streamlit as st

from utils.feedback import create_feedback_entry
from utils.data_models import ChatHistoryEntry


def get_final_response(agent, eval_success: bool, code_output, stream_placeholder):
    if eval_success and code_output is not None:
        final_response = agent.call_final_llm(stream_placeholder)
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
            chat_entry = ChatHistoryEntry(
                role="assistant",
                final_response="Something went wrong. Please try again.",
                error_message=llm_response,
                code_response=None
            )
        else:
            code_output, eval_success, error_message, only_text, llm_response = agent.evaluate_code(
                retry_code, llm_response
            )
            final_response = llm_response
            stream_placeholder = st.empty()
            if not only_text:
                with st.spinner("Almost there..."):
                    final_response = get_final_response(agent, eval_success, code_output, stream_placeholder)
        
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

            # Add feedback for the new assistant message, including final_response
            create_feedback_entry(
                user_input, agent, llm_response, eval_success, code_output, error_message, final_response
            )

def process_cancellation():
    chat_entry = ChatHistoryEntry(
        role="assistant",
        final_response="The operation was cancelled.",
        only_text=True,
        is_cancelled=True
    )
    st.session_state.chat_history.append(chat_entry.dict())
    st.info("The operation was cancelled.")
