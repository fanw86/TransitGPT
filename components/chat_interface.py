import folium
import streamlit as st
import matplotlib.pyplot as plt
from utils.feedback import FeedbackAgent
from streamlit_folium import folium_static

def display_chat_history(fb_agent: FeedbackAgent,uuid: str):    
    for i, message in enumerate(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(message["content"])
            else:
                with st.expander("👨‍💻Code", expanded=False):
                # with st.expander("LLM Response", expanded=False):
                    st.write(message["content"])
                
                col1, col2, col3 = st.columns([6, 3, 1])
                
                with col1:    
                    if "output" in message:
                        st.write("Code Evaluation Result:")
                        if isinstance(message["output"], plt.Figure):
                            st.pyplot(message["output"])
                        elif isinstance(message["output"], folium.Map):
                            folium_static(message["output"])
                        else:
                            st.write(message["output"])
                
                message_id = f"{uuid}_{i}"
                st.session_state.current_message_id = message_id
                
                with col3:
                    st.feedback(
                        key=f"{message_id}_feedback",
                        on_change=fb_agent.on_feedback_change,
                        options="thumbs",
                    )
                with col2:
                    st.text_input("Comment:", label_visibility='collapsed', placeholder="Comment (optional):", key=f"{message_id}_comment", on_change=fb_agent.on_feedback_change)
                
                if message.get("final_response"):
                    st.write(message["final_response"])