import time
import streamlit as st
from utils.agent import LLMAgent
from utils.constants import file_mapping, LLMs, disclaimer_text, copyright_text
from utils.state import reset_session_state, load_session_state


@st.cache_resource(show_spinner=False)
def initialize_agent(model):
    return LLMAgent(file_mapping, model)


def load_agent_evaluator():
    # Clear chat history on change of model or GTFS feed or units
    if len(st.session_state.chat_history) > 0:
        clear_chat_history()
    print("<<<==================Initializing Chat App=====================>>>")
    print(f"Call count: {st.session_state['call_count']}, time: {time.ctime()}")
    GTFS = st.session_state["GTFS"]
    with st.spinner(f"Loading `{GTFS}` GTFS Feed and setting up LLM Agent..."):
        model = st.session_state["model"]
        distance_unit = file_mapping[GTFS]["distance_unit"]
        if "agent" not in st.session_state:
            agent = initialize_agent(model)
            st.session_state["agent"] = agent
        else:
            agent = st.session_state["agent"]
            agent.update_agent(GTFS, model, distance_unit)
        st.session_state["call_count"] += 1
    # Loaded GTFS feed
    st.toast(f"Loaded GTFS feed: {GTFS} ({distance_unit})", icon="🚌")


def clear_chat_history():
    st.session_state.agent.reset()
    reset_session_state()
    load_session_state()


def setup_sidebar():
    # Sidebar for model selection and GTFS feed selection
    # st.sidebar.title("GTFS2CODE🚌")
    st.sidebar.json(st.session_state, expanded=False)

    if "call_count" not in st.session_state:
        st.session_state["call_count"] = 0

    st.sidebar.markdown(
        "`GTFS2CODE` is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code."
    )

    st.sidebar.selectbox(
        "Select LLM",
        LLMs,
        key="model",
        help="Pick your LLM! In our experiments Claude seems to be the best!",
        on_change=load_agent_evaluator,
    )

    GTFS_feed_list = list(file_mapping.keys())
    st.sidebar.selectbox(
        "Select GTFS Feed",
        GTFS_feed_list,
        on_change=load_agent_evaluator,
        key="GTFS",
        help="Select a GTFS feed to analyze.",
    )

    # Ditance units
    # st.sidebar.radio(
    #     "Select Distance Units",
    #     ["Meters (m)", "Kilometers (km)"],
    #     key="distance_units",
    #     help="GTFS allows both `m` and `km` as distance units",
    #     on_change=load_agent_evaluator,
    # )
    st.sidebar.toggle(
        "Allow Retry",
        value=True,
        key="retry_code",
        help="LLM will retry code generation if it fails.",
    )

    # Clear Chat History button
    if st.sidebar.button("🧹Clear Chat History"):
        clear_chat_history()

    with st.sidebar.expander("⚠️ Disclaimer", expanded=False):
        st.markdown(disclaimer_text)

    st.sidebar.write(copyright_text)
