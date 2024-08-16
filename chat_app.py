import streamlit as st
import json
import folium
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from streamlit_folium import folium_static

## Custom imports
from utils.feedback import create_feedback_entry
from utils.constants import MAX_MESSAGES
from utils.state import load_session_state
from components.sidebar import (
    setup_sidebar,
    initialize_agent_evaluator,
    load_prompt_and_feed,
)
from components.chat_interface import display_chat_history, clear_chat, add_chat_history_entry


# Set the page to wide mode
st.set_page_config(layout="wide")

# Call this function at the beginning of your Streamlit app
load_session_state()
# Setup sidebar
setup_sidebar()

# Initialize agent, evaluator and prompt with default GTFS feed
if "agent" not in st.session_state:
    print("Initializing agent and evaluator...")
    initialize_agent_evaluator()
    load_prompt_and_feed()

# Chat interface
st.title("GTFS2CODE🚌")
# Display chat history
display_chat_history(st.session_state["fb_agent"], st.session_state.uuid)

# Check if the number of messages has reached the limit
if len(st.session_state.chat_history) >= MAX_MESSAGES:
    st.session_state.show_limit_popup = True
    st.rerun()

# Display dialog when message limit is reached
if st.session_state["show_limit_popup"]:
    st.session_state["is_chat_input_disabled"] = True
    clear_chat()

# Display sample questions above the message bar only if it's the first question
if not st.session_state.first_question_asked:
    st.write("Sample Questions:")
    for i, question in enumerate(st.session_state.questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            st.session_state.first_question_asked = True
            st.rerun()

# User input
user_input = st.chat_input(
    "Type your message here...", disabled= not st.chat_input, key="chat_input"
)

# Process user input or selected question
if user_input or st.session_state.selected_question:
    # Disable chat input after user input
    st.session_state.is_chat_input_disabled = True
    
    if st.session_state.selected_question:
        print(st.session_state.selected_question)
        user_input = st.session_state.selected_question
        st.session_state.selected_question = None

    st.session_state.first_question_asked = True
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Initialize local variables
    model = st.session_state["model"]
    agent = st.session_state["agent"]
    fb_agent = st.session_state["fb_agent"]
    evaluate_code_toggle = st.session_state["evaluate_code"]
    retry_code_toggle = st.session_state["retry_code"]

    with st.chat_message("assistant"):
        with st.spinner(f"Getting response from {model}..."):
            system_prompt = st.session_state["SYSTEM_PROMPT"]
            llm_response = agent.call_llm(
                system_prompt, user_input, st.session_state["model"]
            )

        if evaluate_code_toggle:
            with st.status("Evaluating code..."):
                if retry_code_toggle:
                    output, success, error_message, new_llm_response = (
                        agent.evaluate_with_retry(st.session_state["model"], llm_response)
                    )
                    llm_response = new_llm_response
                else:
                    output, success, error_message = agent.evaluate(llm_response)

            final_response = None
            if success:
                if output is not None:
                    final_response = agent.call_final_llm() # Call final LLM
                else:
                    final_response = llm_response

        chat_entry = add_chat_history_entry(final_response, llm_response, output, success, error_message)
        # Add the new assistant message to the chat history
        st.session_state.chat_history.append(chat_entry.dict())

        # Add feedback for the new assistant message
        message_id = f"{st.session_state.uuid}_{len(st.session_state.chat_history) - 1}"
        st.session_state.current_message_id = message_id
        
        feedback_entry = create_feedback_entry(
            user_input, llm_response, success, output, error_message
        )
        # Store comprehensive feedback
        fb_agent.db.collection(fb_agent.collection_name).document(message_id).set(
            feedback_entry.dict()
        )
        agent.reset()
        st.session_state.is_chat_input_disabled = False
        st.rerun()
