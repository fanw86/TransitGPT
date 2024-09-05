import re
import json
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
            folium_static(folium_map, height=400)
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
        st.error(
            f"Expected a Folium Map object, but received a different type. Received object of type: {type(folium_map)}"
        )


def safe_fig_display(fig):
    if isinstance(fig, plt.Figure):
        try:
            st.pyplot(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying Matplotlib figure: {str(e)}")
            st.write("Figure data (non-rendered):")
    elif isinstance(fig, go.Figure):
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying Plotly figure: {str(e)}")
            st.write("Figure data (non-rendered):")
    else:
        st.error(
            f"Expected a Matplotlib or Plotly Figure object, but received a different type. Received object of type: {type(fig)}"
        )


def apply_color_codes(text):
    def color_replacer(match):
        color = match.group(1)
        return f'<span style="color: {color}">{color}</span>'

    # Replace color codes with HTML spans
    colored_text = re.sub(r"(#[0-9A-Fa-f]{6})", color_replacer, text)

    # Wrap the entire text in a paragraph tag to ensure inline HTML is rendered
    return colored_text


def display_code_output(message, only_text=False):
    if "code_output" not in message or only_text:
        return

    if not message.get("eval_success", False):
        st.write("Evaluation failed.")
        return

    code_output = message["code_output"]
    with st.expander("✅Code Evaluation Result:", expanded=False):
        st.write(code_output)


def display_fig_map(code_output):
    if "plot" in code_output and code_output["plot"] is not None:
        safe_fig_display(code_output["plot"])
    if "map" in code_output and code_output["map"] is not None:
        safe_folium_display(code_output["map"])


def display_figure(fig):
    if isinstance(fig, go.Figure):
        st.plotly_chart(fig, use_container_width=True)
    elif isinstance(fig, plt.Figure):
        st.pyplot(fig, use_container_width=True)


def display_feedback_ui(fb_agent, message_id, col2, col3):
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
            placeholder="Comment",
            key=f"{message_id}_comment",
            on_change=fb_agent.on_feedback_change,
        )


def display_llm_response(fb_agent, uuid, message, i):
    # Display Code if final response is different from the initial LLM response
    only_text = message["only_text"]
    if not only_text:
        with st.expander("👨‍💻Code", expanded=False):
            # with st.expander("LLM Response", expanded=False):
            executable_pattern = r"```python\n(.*?)```"
            executable_code = re.findall(
                executable_pattern, message["code_response"], re.DOTALL
            )
            code_block = "```python\n" + executable_code[0] + "\n```"
            st.markdown(code_block)

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

    if only_text or message["final_response"] != message["code_response"]:
        colored_response = apply_color_codes(message["final_response"])
        if message["is_cancelled"]:
            with col1:
                st.info(message["final_response"])
        else:
            display_feedback_ui(fb_agent, message_id, col2, col3)
            if len(colored_response) <= 500:
                with col1:
                    st.markdown(colored_response, unsafe_allow_html=True)
            else:
                st.markdown(colored_response, unsafe_allow_html=True)
    if isinstance(message["code_output"], dict):
        display_fig_map(message["code_output"])


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
