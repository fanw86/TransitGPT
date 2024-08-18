from utils.feedback import get_feedback
import uuid
from utils.sample_questions import load_questions
import streamlit as st


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
        "is_processing": False,
    }

    for key, default_value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
