import folium
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from utils.feedback import FeedbackAgent
from streamlit_folium import folium_static
from components.sidebar import clear_chat_history
from pydantic import BaseModel
from typing import Literal, Any, Optional, Union


@st.dialog("Maximum number of messages reached!")
def clear_chat():
    st.write("The chat history will be cleared.")
    if st.button("OK"):
        clear_chat_history()


class ChatHistoryEntry(BaseModel):
    role: Literal["assistant"]  # Since this is always "assistant" in the given context
    final_response: Union[str, None]
    content: str
    output: Any = (None,)
    eval_success: bool
    error_info: Optional[str] = None


def add_chat_history_entry(
    final_response: Union[str, None],
    llm_response: str,
    output: Any,
    success: bool,
    error_info: Optional[str] = None,
) -> ChatHistoryEntry:
    entry = ChatHistoryEntry(
        role="assistant",
        final_response=final_response,
        content=llm_response,
        output=output
        if success
        else str(output),  # Convert to string if it's an error message
        eval_success=success,
        error_info=error_info,
    )
    return entry


def display_chat_history(fb_agent: FeedbackAgent, uuid: str):
    for i, message in enumerate(st.session_state.chat_history):
        avatar = "🚍" if message["role"] == "assistant" else "🙋‍♂️"
        with st.chat_message(message["role"], avatar=avatar):
            ## Display user message
            if message["role"] == "user":
                st.write(message["content"])
            ## Display assistant message
            else:
                # Display Code if final response is different from the initial LLM response
                only_text = message["final_response"] == message["content"]
                if not only_text:
                    with st.expander("👨‍💻Code", expanded=False):
                        # with st.expander("LLM Response", expanded=False):
                        st.write(message["content"])

                col1, col2, col3 = st.columns([6, 2, 1])

                with col1:
                    if "output" in message and only_text is False:
                        st.write("Code Evaluation Result:")
                        if message.get("eval_success", False):  # Default to False
                            if isinstance(message["output"], plt.Figure):
                                st.pyplot(message["output"])
                            elif isinstance(message["output"], folium.Map):
                                folium_static(message["output"])
                            elif isinstance(message["output"], pd.Series):
                                st.write(message["output"].to_dict())
                            else:
                                st.write(message["output"])
                        else:
                            st.error(
                                f"Code evaluation failed:\n {message['error_info']}"
                            )

                message_id = f"{uuid}_{i}"
                st.session_state.current_message_id = message_id

                with col3:
                    st.feedback(
                        key=f"{message_id}_feedback",
                        on_change=fb_agent.on_feedback_change,
                        options="thumbs",
                    )
                with col2:
                    st.text_input(
                        "Comment:",
                        label_visibility="collapsed",
                        placeholder="Comment (optional):",
                        key=f"{message_id}_comment",
                        on_change=fb_agent.on_feedback_change,
                    )

                if message.get("final_response"):
                    st.write(message["final_response"])
