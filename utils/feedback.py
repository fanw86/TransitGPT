import json
from datetime import datetime

import folium
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

from utils.data_models import FeedbackEntry
from utils.helper import fig_to_base64, plotly_fig_to_base64
import plotly.graph_objs as go


def create_feedback_entry(
    user_input,
    agent,
    llm_response,
    eval_success,
    code_output,
    error_message,
    final_response=None,
):
    message_id = f"{st.session_state.uuid}_{len(st.session_state.chat_history) - 1}"
    st.session_state.current_message_id = message_id

    feedback_entry = FeedbackEntry(
        question=user_input,
        response=llm_response,
        code_eval_success=eval_success,
        GTFS=agent.GTFS,
        llm_model=agent.model,
        system_prompt=agent.system_prompt,
        final_response=final_response,
    )

    if eval_success:
        if isinstance(code_output, plt.Figure):
            feedback_entry.code_eval_result = "Matplotlib Figure generated"
            feedback_entry.figure = fig_to_base64(code_output)
        elif isinstance(code_output, go.Figure):
            feedback_entry.code_eval_result = "Plotly Figure generated"
            feedback_entry.figure = plotly_fig_to_base64(code_output)
        elif isinstance(code_output, folium.Map):
            feedback_entry.code_eval_result = "Map generated"
        elif isinstance(code_output, (pd.DataFrame, pd.Series)):
            feedback_entry.code_eval_result = code_output.to_string()
        else:
            feedback_entry.code_eval_result = str(code_output)[:5000]
    else:
        feedback_entry.code_eval_result = str(error_message)[:5000]

    collection_name = st.session_state["fb_agent"].collection_name
    st.session_state["fb_agent"].db.collection(collection_name).document(
        message_id
    ).set(feedback_entry.dict())


class FeedbackAgent:
    def __init__(self, collection_name="feedback"):
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
        feedback_value = st.session_state[
            f"{st.session_state.current_message_id}_feedback"
        ]
        comment = st.session_state[f"{st.session_state.current_message_id}_comment"]
        message_id = st.session_state.current_message_id

        doc_ref = self.db.collection(self.collection_name).document(message_id)
        doc_ref.set(
            {
                "user_rating": feedback_value,
                "user_comment": comment,
                "timestamp": datetime.now(),
            },
            merge=True,
        )

        st.toast("Thank you for your feedback!", icon="👍" if feedback_value else "👎")


@st.cache_resource(show_spinner="Loading feedback...")
def get_feedback():
    fb_agent = FeedbackAgent()
    return fb_agent
