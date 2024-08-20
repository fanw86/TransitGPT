import json
import folium
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from utils.feedback import FeedbackAgent
from streamlit_folium import folium_static
from components.sidebar import clear_chat_history
import plotly.graph_objects as go
from folium import Map


@st.dialog("Maximum number of messages reached!")
def clear_chat():
    st.write("The chat history will be cleared.")
    if st.button("🧹Clear Chat!"):
        clear_chat_history()
        st.rerun()


def is_json_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def safe_folium_display(folium_map):
    if isinstance(folium_map, Map):
        try:
            folium_static(folium_map, width=600, height=400)
        except Exception as e:
            st.error(f"Error displaying Folium map: {str(e)}")
            st.write("Map data (non-rendered):")
            st.json(
                {
                    k: v
                    for k, v in folium_map.__dict__.items()
                    if is_json_serializable(v)
                }
            )
    else:
        st.error("Expected a Folium Map object, but received a different type.")
        st.write(f"Received object of type: {type(folium_map)}")


def display_code_output(message, only_text=False):
    if "code_output" not in message or only_text:
        return

    code_output = message["code_output"]

    if not message.get("eval_success", False):
        st.write("Evaluation failed.")
        return

    display_functions = {
        plt.Figure: lambda x: st.pyplot(x, use_container_width=True),
        go.Figure: lambda x: st.plotly_chart(x, use_container_width=True),
        folium.Map: safe_folium_display,
        pd.Series: lambda x: st.write(x.to_dict()),
    }

    possible_alt_keys = {
        "map": safe_folium_display,
        "plot": lambda x: st.pyplot(x, use_container_width=True),
        "figure": lambda x: st.plotly_chart(x, use_container_width=True),
    }

    if isinstance(code_output, tuple(display_functions.keys())):
        display_functions[type(code_output)](code_output)
    else:
        with st.expander("✅Code Evaluation Result:", expanded=True):
            st.write(code_output)
        if isinstance(code_output, dict):
            specific_keys = ["map", "plot", "figure"]
            check_keys = [key in code_output for key in specific_keys]
            if sum(check_keys) == 1:
                key = specific_keys[check_keys.index(True)]
                possible_alt_keys[key](code_output[key])


def display_figure(fig):
    if isinstance(fig, go.Figure):
        st.plotly_chart(fig, use_container_width=True)
    elif isinstance(fig, plt.Figure):
        st.pyplot(fig, use_container_width=True)


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
            if message.get("eval_success", False):  # Default to False
                display_code_output(message)
            else:
                with st.expander("❌ :red[Code evaluation failed]", expanded=False):
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
