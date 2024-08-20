import uuid
import streamlit as st
from utils.feedback import get_feedback
from utils.sample_questions import load_questions


def load_session_state():
    default_values = {
        "chat_history": [],
        "first_question_asked": False,
        "current_message_id": None,
        "selected_question": None,
        "uuid": str(uuid.uuid4()),
        "questions": load_questions(),
        "fb_agent": get_feedback(),
        "show_limit_popup": False,
        "is_chat_input_disabled": False,
        "is_processing": False,
    }

    for key, default_value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_session_state():
    reset_keys = [
        "chat_history",
        "first_question_asked",
        "current_message_id",
        "selected_question",
        "uuid",
        "questions",
        "show_limit_popup",
        "is_chat_input_disabled",
        "is_processing",
    ]
    for key in reset_keys:
        del st.session_state[key]
    load_session_state()
