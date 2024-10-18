import streamlit as st

from utils.feedback import create_feedback_entry
from utils.data_models import ChatHistoryEntry


def process_user_input(user_input: str):
    agent = st.session_state.agent
    with st.chat_message("assistant", avatar="🚍"):
        with st.spinner("Processing your request..."):
            (
                result,
                success,
                error_message,
                only_text,
                llm_response,
                summary_response,
                validation_response,
            ) = agent.run_workflow(user_input, st.session_state.retry_code)

        if not success and not only_text:
            st.error(f"Error: {error_message}")
            chat_entry = ChatHistoryEntry(
                role="assistant",
                eval_success=success,
                error_message=error_message,
                main_response=llm_response,
                only_text=only_text,
            )
        else:
            chat_entry = ChatHistoryEntry(
                role="assistant",
                summary_response=summary_response,
                main_response=llm_response,
                code_output=result,
                eval_success=success,
                error_message=error_message,
                only_text=only_text,
            )

        st.session_state.chat_history.append(chat_entry.dict())
        create_feedback_entry(
            user_input,
            agent,
            llm_response,
            success,
            result,
            error_message,
            summary_response,
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
