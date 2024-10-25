import streamlit as st

from utils.feedback import create_feedback_entry
from utils.data_models import ChatHistoryEntry


def process_user_input(user_input: str):
    agent = st.session_state.agent
    with st.chat_message("assistant", avatar="🚍"):
        with st.spinner("Processing your request..."):
            result = agent.run_workflow(user_input, st.session_state.retry_code)

        if not result["eval_success"] and not result["only_text"]:
            st.error(f"Error: {result['error_message']}")
            chat_entry = ChatHistoryEntry(
                role="assistant",
                eval_success=result["eval_success"],
                error_message=result["error_message"],
                main_response=result["main_response"],
                only_text=result["only_text"],
            )
        else:
            chat_entry = ChatHistoryEntry(
                role="assistant",
                summary_response=result["summary_response"],
                main_response=result["main_response"],
                code_output=result["code_output"],
                eval_success=result["eval_success"],
                error_message=result["error_message"],
                only_text=result["only_text"],
            )

        st.session_state.chat_history.append(chat_entry.dict())
        result["agent"] = agent
        result["user_input"] = user_input
        create_feedback_entry(result)


def process_cancellation():
    chat_entry = ChatHistoryEntry(
        role="assistant",
        final_response="The operation was cancelled.",
        only_text=True,
        is_cancelled=True,
    )
    st.session_state.chat_history.append(chat_entry.dict())
    st.info("The operation was cancelled.")
