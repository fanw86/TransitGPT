import streamlit as st
from prompts.generate_prompt import generate_system_prompt
from utils.agent import LLMAgent
from utils.constants import file_mapping, LLMs, disclaimer_text
from utils.eval_code import GTFS_Eval


@st.cache_resource(show_spinner="Setting up LLM Agent...")
def get_agent(_evaluator):
    return LLMAgent(_evaluator)


@st.cache_resource(show_spinner="Setting up GTFS Evaluator...")
def get_evaluator(file_mapping, distance_unit):
    return GTFS_Eval(file_mapping, distance_unit)


def initialize_agent_evaluator(distance_unit="m"):  
    if distance_unit == 'Meters' or distance_unit == 'm':
        distance_unit = 'm'
    else:
        distance_unit = 'Km'
    st.session_state["evaluator"] = get_evaluator(file_mapping, distance_unit)
    st.session_state["agent"] = get_agent(st.session_state["evaluator"])


def load_prompt_and_feed():
    with st.spinner("Loading GTFS feed..."):
        GTFS = st.session_state["GTFS"]
        st.session_state["agent"].evaluator.load_current_feed(GTFS)
        st.session_state["SYSTEM_PROMPT"] = st.session_state["agent"].evaluator.load_system_prompt()    
        st.toast(f"Loaded GTFS feed: {GTFS}", icon="🚌")
        
def set_distance_units():
    agent = st.session_state["agent"]
    agent.distance_units = st.session_state["distance_units"]
    initialize_agent_evaluator(agent.distance_units)


def setup_sidebar():
    # Sidebar for model selection and GTFS feed selection
    # st.sidebar.title("GTFS2CODE🚌")
    st.sidebar.markdown(
        "`GTFS2CODE` is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code."
    )

    st.sidebar.selectbox(
        "Select LLM",
        LLMs,
        key='model',
        help="Pick your LLM! In our experiments Claude seems to be the best!"
    )

    st.sidebar.selectbox(
        "Select GTFS Feed",
        file_mapping.keys(),
        on_change=load_prompt_and_feed,
        key="GTFS",
        help="Select a GTFS feed to analyze.",
    )

    # Initialize session state variables
    if st.session_state["agent"].evaluator.feed_main is None:
        load_prompt_and_feed()
        
    # Add toggle for code evaluation
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        # Ditance units
        st.sidebar.radio(
            "Select Distance Units", ["Meters", "Kilometers"], key="distance_units",
            help= "GTFS allows both `m` and `Km` as distance units",
            on_change=set_distance_units
        )
    with col2:
        st.sidebar.toggle("Run Code", value=True, key="evaluate_code", help="Enable code evaluation to run code snippets in the chat.")
        st.sidebar.toggle("Allow Retry", value=False, key="retry_code", help="LLM will retry code generation if it fails.")

    # Clear Chat History button
    if st.sidebar.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.first_question_asked = False
        st.session_state.selected_question = None
        st.rerun()

    with st.sidebar.expander("⚠️ Disclaimer", expanded=False):
        st.markdown(disclaimer_text)

    with st.sidebar:
        st.write(
            "Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)"
        )
