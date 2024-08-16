import streamlit as st
from utils.agent import LLMAgent
from utils.constants import file_mapping, LLMs, disclaimer_text
from utils.eval_code import GTFS_Eval
import time

@st.cache_resource(show_spinner="Setting up LLM Agent...")
def get_agent(_evaluator):
    return LLMAgent(_evaluator)


@st.cache_resource(show_spinner="Setting up GTFS Evaluator...")
def get_evaluator(file_mapping, distance_unit):
    return GTFS_Eval(file_mapping, distance_unit)


def initialize_agent_evaluator(distance_unit="m"):
    if distance_unit == "Meters" or distance_unit == "m":
        distance_unit = "m"
    else:
        distance_unit = "Km"
    evaluator = get_evaluator(file_mapping, distance_unit)
    agent = get_agent(evaluator)
    st.session_state["evaluator"] = evaluator
    st.session_state["agent"] = agent

# @st.cache_resource(show_spinner="Loading GTFS feed...")
def load_prompt_and_feed():
    st.session_state['call_count'] += 1
    print(f"Call count: {st.session_state['call_count']}, time: {time.ctime()}")
    with st.spinner("Loading GTFS feed..."):
        GTFS = st.session_state["GTFS"]
        st.session_state["SYSTEM_PROMPT"] = st.session_state[
            "agent"
        ].evaluator.load_system_prompt(GTFS)
        st.toast(f"Loaded GTFS feed: {GTFS}", icon="🚌")


def clear_chat_history():
    st.session_state.chat_history = []
    st.session_state.first_question_asked = False
    st.session_state.selected_question = None
    st.session_state.show_limit_popup = False
    st.session_state.is_chat_input_disabled= False
    st.rerun()

def set_distance_units():
    agent = st.session_state["agent"]
    agent.distance_units = st.session_state["distance_units"]
    initialize_agent_evaluator(agent.distance_units)


def setup_sidebar():
    # Sidebar for model selection and GTFS feed selection
    # st.sidebar.title("GTFS2CODE🚌")
    
    if "call_count" not in st.session_state:
        st.session_state['call_count'] = 0
    
    st.sidebar.markdown(
        "`GTFS2CODE` is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code."
    )

    st.sidebar.selectbox(
        "Select LLM",
        LLMs,
        key="model",
        help="Pick your LLM! In our experiments Claude seems to be the best!",
    )

    GTFS_feed_list = list(file_mapping.keys())
    st.sidebar.selectbox(
        "Select GTFS Feed",
        GTFS_feed_list,
        on_change=load_prompt_and_feed,
        key="GTFS",
        help="Select a GTFS feed to analyze.",
    )

    # Add toggle for code evaluation
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        # Ditance units
        st.sidebar.radio(
            "Select Distance Units",
            ["Meters", "Kilometers"],
            key="distance_units",
            help="GTFS allows both `m` and `Km` as distance units",
            on_change=set_distance_units,
        )
    with col2:
        st.sidebar.toggle(
            "Run Code",
            value=True,
            key="evaluate_code",
            help="Enable code evaluation to run code snippets in the chat.",
        )
        st.sidebar.toggle(
            "Allow Retry",
            value=False,
            key="retry_code",
            help="LLM will retry code generation if it fails.",
        )

    # Clear Chat History button
    if st.sidebar.button("Clear Chat History"):
        clear_chat_history()

    with st.sidebar.expander("⚠️ Disclaimer", expanded=False):
        st.markdown(disclaimer_text)

    with st.sidebar:
        st.write(
            "Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)"
        )