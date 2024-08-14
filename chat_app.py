import streamlit as st
import json
import folium
import os
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from streamlit_folium import folium_static
## Custom imports
from utils.helper import jumble_list, fig_to_base64
from utils.feedback import FeedbackAgent
from utils.constants import file_mapping
from components.sidebar import setup_sidebar, initialize_agent_evaluator
from prompts.generate_prompt import generate_system_prompt
from components.chat_interface import display_chat_history

# Set the page to wide mode
# st.set_page_config(layout="wide")

@st.cache_resource(show_spinner="Loading feedback...")
def get_feedback():
    fb_agent = FeedbackAgent()
    return fb_agent

# File to store sample questions
QUESTIONS_FILE = "data/sample_questions.json"
QUESTION_LIMIT = 3

fb_agent = get_feedback()
initialize_agent_evaluator()
setup_sidebar()

@st.cache_data(ttl=60)
def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, "r") as f:
            question_list = json.load(f)
            question_list = jumble_list(question_list)
            question_list = question_list[:QUESTION_LIMIT]
            return question_list
    return []

if "SYSTEM_PROMPT" not in st.session_state:
    st.session_state["SYSTEM_PROMPT"] = st.session_state["agent"].evaluator.load_system_prompt()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "first_question_asked" not in st.session_state:
    st.session_state.first_question_asked = False
if "current_message_id" not in st.session_state:
    st.session_state.current_message_id = None
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None
if "uuid" not in st.session_state:
    st.session_state.uuid = str(uuid.uuid4()) 
    
questions = load_questions()

# Chat interface
st.title("GTFS2CODE🚌")

# Display chat history
display_chat_history(fb_agent, st.session_state.uuid)

# Display sample questions above the message bar only if it's the first question
if not st.session_state.first_question_asked:
    st.write("Sample Questions:")
    for i, question in enumerate(questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            st.session_state.first_question_asked = True
            st.rerun()

# User input
user_input = st.chat_input("Type your message here...")

# Process user input or selected question
if user_input or st.session_state.selected_question:
    if st.session_state.selected_question:
        print(st.session_state.selected_question)
        user_input = st.session_state.selected_question
        st.session_state.selected_question = None
    
    st.session_state.first_question_asked = True
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    model = st.session_state["model"]
    agent = st.session_state["agent"]
    evaluate_code_toggle = st.session_state["evaluate_code"]
    retry_code_toggle = st.session_state["retry_code"]
    
    with st.chat_message("assistant"):
        with st.spinner(f"Getting response from {model}..."):
            system_prompt = st.session_state["SYSTEM_PROMPT"]
            llm_response = agent.call_llm(system_prompt, user_input, st.session_state["model"])
            
        if evaluate_code_toggle:
            with st.status("Evaluating code..."):
                if retry_code_toggle:
                    output, success, error_message, new_llm_response = agent.evaluate_with_retry(
                        st.session_state['model'], llm_response
                    )
                    llm_response = new_llm_response
                else:
                    output, success, error_message = agent.evaluate(llm_response)

            if success:
                final_response = agent.call_final_llm()
                st.write("Code Evaluation Result:")
                if isinstance(output, plt.Figure):
                    st.pyplot(output)
                elif isinstance(output,folium.Map):
                    folium_static(output)
                elif isinstance(output, pd.DataFrame) or isinstance(output, pd.Series):
                    st.dataframe(output)
                else:
                    st.write(output)
                
                st.write(f"Final Response: {final_response}")
            else:
                final_response = None
                st.error(f"Code evaluation failed:\n {error_message}")

        with st.expander("👨‍💻Code", expanded=False):
            st.write(llm_response)
        
        st.session_state.chat_history.append({
            "role": "assistant",
            "final_response": final_response,
            "content": llm_response,
            "output": output if success else error_message
        })

        # Add feedback for the new assistant message
        message_id = f"{st.session_state.uuid}_{len(st.session_state.chat_history) - 1}"
        st.session_state.current_message_id = message_id
        st.feedback(
            key=f"{message_id}_feedback",
            on_change=fb_agent.on_feedback_change,
            options="thumbs",
        )

        # Store comprehensive feedback
        feedback_entry = {
            "timestamp": datetime.now(),
            "question": user_input,
            "response": llm_response,
            "code_eval_success": success,
            "GTFS": st.session_state["GTFS"],
            "llm_model": st.session_state["model"],
            "system_prompt": system_prompt,
            "user_rating": None,  # This will be updated when the user provides feedback
            "user_comment": None  # This will be updated when the user provides a comment
        }

        if success:
            if isinstance(output, plt.Figure):
                feedback_entry["code_eval_result"] = "Figure generated"
                feedback_entry["figure"] = fig_to_base64(output)
            elif isinstance(output,folium.Map):
                feedback_entry["code_eval_result"] = "Map generated"
            elif isinstance(output, pd.DataFrame) or isinstance(output, pd.Series):
                feedback_entry["code_eval_result"] = output.to_dict()
            else:
                feedback_entry["code_eval_result"] = str(output)
        else:
            feedback_entry["code_eval_result"] = error_message

        fb_agent.db.collection(fb_agent.collection_name).document(message_id).set(feedback_entry)
        agent.reset()
        st.rerun()