import time
import streamlit as st
from rich import print as rprint
from gtfs_agent.agent import LLMAgent
from utils.constants import file_mapping, LLMs, disclaimer_text, copyright_text
from components.state import reset_session_state, load_session_state


# @st.cache_resource(show_spinner=False)
def initialize_agent(model, allow_viz):
    return LLMAgent(file_mapping, model, allow_viz=allow_viz)


def load_agent_evaluator():
    # Clear chat history on change of model or GTFS feed
    if len(st.session_state.chat_history) > 0:
        clear_chat_history()
    rprint("[bold yellow]<<<==================Initializing Chat App=====================>>>[/bold yellow]")
    rprint(f"[blue]Call count:[/blue] {st.session_state['call_count']}, [blue]time:[/blue] {time.ctime()}")
    GTFS = st.session_state["GTFS"]
    with st.status(f"Loading `{GTFS}` GTFS Feed and setting up LLM Agent...") as status:
        model = st.session_state["model"]
        allow_viz = st.session_state["allow_viz"]
        distance_unit = file_mapping[GTFS]["distance_unit"]
        if "agent" not in st.session_state:
            agent = initialize_agent(model, allow_viz)
            st.session_state["agent"] = agent
        else:
            agent = st.session_state["agent"]
        agent.update_agent(GTFS, model, distance_unit, allow_viz)
        st.session_state["call_count"] += 1
        status.update(
            label=f"Loaded GTFS feed: {GTFS} ({distance_unit})", state="complete"
        )
    # Loaded GTFS feed
    st.toast(f"Loaded GTFS feed: {GTFS} ({distance_unit})", icon="🚌")


def clear_chat_history():
    st.session_state.agent.reset()
    reset_session_state()
    load_session_state()


def update_agent_settings():
    if "agent" in st.session_state:
        st.session_state.agent.update_agent(
            st.session_state.agent.GTFS,
            st.session_state.model,
            st.session_state.agent.distance_unit,
            st.session_state.allow_viz,
        )
    st.toast(
        f"Using Model: {st.session_state.model} with Visualization: {st.session_state.allow_viz}",
        icon="🚌",
    )


def setup_sidebar():
    # Sidebar for model selection and GTFS feed selection
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
        on_change=update_agent_settings,
    )

    GTFS_feed_list = list(file_mapping.keys())
    st.sidebar.selectbox(
        "Select GTFS Feed",
        GTFS_feed_list,
        on_change=load_agent_evaluator,
        key="GTFS",
        help="Select a GTFS feed to analyze.",
    )

    st.sidebar.toggle(
        "Allow Visualization",
        value=True,
        key="allow_viz",
        help="LLM will generate visualization along with code.",
        on_change=update_agent_settings,
    )

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

    # Initialize agent, evaluator and prompt with default GTFS feed

    if "agent" not in st.session_state:
        load_agent_evaluator()