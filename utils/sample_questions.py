import json
import os
import streamlit as st
from utils.constants import QUESTIONS_FILE, QUESTION_LIMIT
import numpy as np

# @st.cache_data(ttl=10)
def load_questions(limit=QUESTION_LIMIT):
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, "r") as f:
            question_list = json.load(f)
            question_list = np.random.choice(question_list, size=limit, replace=False).tolist()
            return question_list
    return []
