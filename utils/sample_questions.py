import json
import os
import streamlit as st
from utils.helper import jumble_list
from utils.constants import QUESTIONS_FILE, QUESTION_LIMIT

st.cache_data(ttl=60)
def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, "r") as f:
            question_list = json.load(f)
            question_list = jumble_list(question_list)
            question_list = question_list[:QUESTION_LIMIT]
            return question_list
    return []
