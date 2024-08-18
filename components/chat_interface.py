import folium
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from utils.feedback import FeedbackAgent
from streamlit_folium import folium_static
from components.sidebar import clear_chat_history


@st.dialog("Maximum number of messages reached!")
def clear_chat():
    st.write("The chat history will be cleared.")
    if st.button("OK"):
        clear_chat_history()
        st.rerun()


def display_llm_response(fb_agent, uuid, message, i):
    # Display Code if final response is different from the initial LLM response
    only_text = message["only_text"]
    if not only_text:
        with st.expander("👨‍💻Code", expanded=False):
            # with st.expander("LLM Response", expanded=False):
            st.write(message["code_response"])

    col1, col2, col3 = st.columns([6, 2, 1])

    with col1:
        if "code_output" in message and only_text is False:
            code_output = message["code_output"]
            st.write("Code Evaluation Result:")
            if message.get("eval_success", False):  # Default to False
                if isinstance(code_output, plt.Figure):
                    st.pyplot(code_output)
                elif isinstance(code_output, folium.Map):
                    folium_static(code_output)
                elif isinstance(code_output, pd.Series):
                    st.write(code_output.to_dict())
                else:
                    st.write(code_output)
                if isinstance(code_output, dict):
                    if "map" in code_output:
                        folium_static(code_output["map"])
                    if "plot" in code_output:
                        st.pyplot(code_output["plot"])
            else:
                with st.expander("❌Code evaluation failed", expanded=False):
                    st.error(f"\n {message['error_message']}")
                st.warning(
                    "Something went wrong with running the code. Please edit your prompt or toggle `🔘Allow Retry`.",
                    icon="⚠",
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

    if only_text or message["final_response"] != message["code_response"]:
        st.write(message["final_response"])


def display_chat_history(fb_agent: FeedbackAgent, uuid: str):
    for index, message in enumerate(st.session_state.chat_history):
        avatar = "🚍" if message["role"] == "assistant" else "🙋‍♂️"
        with st.chat_message(message["role"], avatar=avatar):
            ## Display user message
            if message["role"] == "user":
                st.write(message["content"])
            ## Display assistant message
            else:
                display_llm_response(fb_agent, uuid, message, index)
