import os
import json
import streamlit as st
from utils.helper import NpEncoder
from datetime import datetime, date

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return str(obj)
    # raise TypeError ("Type %s not serializable" % type(obj))

class FeedbackAgent:
    def __init__(self,feedback_file):
        self.feedback_file = feedback_file
        
    def load_feedback(self):# -> Any | dict[Any, Any]:
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, "r") as f:
                    content = f.read()
                    if content.strip():  # Check if the file is not empty
                        return json.loads(content)
                    else:
                        return {}  # Return an empty dict if the file is empty
            except json.JSONDecodeError:
                st.warning("The feedback file contains invalid JSON. Starting with an empty feedback dictionary.")
                return {}
        return {}


    def save_feedback(self, feedback):
        with open(self.feedback_file, "w") as f:
            json.dump(feedback, f, indent=2, cls=NpEncoder, default=json_serial)
            
    def on_feedback_change(self):
        feedback_value = st.session_state[f"{st.session_state.current_message_id}_feedback"]
        comment = st.session_state[f"{st.session_state.current_message_id}_comment"]
        message_id = st.session_state.current_message_id
        feedback = self.load_feedback()
        
        if message_id in feedback:
            feedback[message_id]["user_rating"] = feedback_value
            feedback[message_id]["user_comment"] = comment
        
        self.save_feedback(feedback)
        st.toast(f"Thank you for your feedback!", icon="👍" if feedback_value else "👎")