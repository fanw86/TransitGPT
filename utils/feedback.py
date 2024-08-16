import json
import pytz
import streamlit as st
from google.oauth2 import service_account
from google.cloud import firestore
from datetime import datetime
from typing import Optional, Any
from utils.helper import fig_to_base64
import matplotlib.pyplot as plt
import pandas as pd
import folium
from pydantic import BaseModel, Field

def get_current_time():
    # Get the timezone for Chicago
    chicago_tz = pytz.timezone('America/Chicago')
    # Get the current time in Chicago
    current_time_chicago = datetime.now(chicago_tz)
    return current_time_chicago
class FeedbackEntry(BaseModel):
    timestamp: datetime = Field(default_factory=get_current_time)
    question: str
    response: str
    code_eval_success: bool
    GTFS: Optional[str] = None
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    user_rating: Optional[int] = None
    user_comment: Optional[str] = None
    code_eval_result: Optional[str] = None
    figure: Optional[str] = None

def create_feedback_entry(
    user_input: str,
    llm_response: str,
    success: bool,
    output: Any = None,
    error_message: Optional[str] = None
) -> FeedbackEntry:
    feedback_entry = FeedbackEntry(
        question=user_input,
        response=llm_response,
        code_eval_success=success,
        GTFS=st.session_state["GTFS"],
        llm_model=st.session_state["model"],
        system_prompt=st.session_state["SYSTEM_PROMPT"]
    )

    if success:
        if isinstance(output, plt.Figure):
            feedback_entry.code_eval_result = "Figure generated"
            feedback_entry.figure = fig_to_base64(output)
        elif isinstance(output, folium.Map):
            feedback_entry.code_eval_result = "Map generated"
        elif isinstance(output, (pd.DataFrame, pd.Series)):
            feedback_entry.code_eval_result = output.to_string()
        else:
            feedback_entry.code_eval_result = str(output)
    else:
        feedback_entry.code_eval_result = str(error_message)

    return feedback_entry
class FeedbackAgent:
    def __init__(self, collection_name='feedback'):
        key_dict = json.loads(st.secrets["firestore_key"])
        credentials = service_account.Credentials.from_service_account_info(key_dict)
        self.db = firestore.Client(credentials=credentials, project="gtfs2code")
        self.collection_name = collection_name

    def load_feedback(self):
        feedback = {}
        docs = self.db.collection(self.collection_name).stream()
        for doc in docs:
            feedback[doc.id] = doc.to_dict()
        return feedback

    def save_feedback(self, feedback):
        for message_id, data in feedback.items():
            self.db.collection(self.collection_name).document(message_id).set(data)

    def on_feedback_change(self):
        feedback_value = st.session_state[f"{st.session_state.current_message_id}_feedback"]
        comment = st.session_state[f"{st.session_state.current_message_id}_comment"]
        message_id = st.session_state.current_message_id

        doc_ref = self.db.collection(self.collection_name).document(message_id)
        doc_ref.set({
            "user_rating": feedback_value,
            "user_comment": comment,
            "timestamp": datetime.now()
        }, merge=True)

        st.toast(f"Thank you for your feedback!", icon="👍" if feedback_value else "👎")
        
@st.cache_resource(show_spinner="Loading feedback...")
def get_feedback():
    fb_agent = FeedbackAgent()
    return fb_agent
