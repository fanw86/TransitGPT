import json
import streamlit as st
from google.oauth2 import service_account
from google.cloud import firestore
from datetime import datetime

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