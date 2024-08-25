import streamlit as st

## Custom imports
from utils.response_processor import process_user_input
from utils.constants import MAX_MESSAGES
from utils.state import load_session_state
from components.sidebar import (
    setup_sidebar,
    load_agent_evaluator,
)
from components.chat_interface import (
    display_chat_history,
    clear_chat,
)


st.set_page_config(
    page_title="GTFS2CODE", page_icon="🚍", layout="wide", initial_sidebar_state="auto"
)

# Setup Session state variables at the beginning of your Streamlit app
load_session_state()
# Setup sidebar
setup_sidebar()

# Initialize agent, evaluator and prompt with default GTFS feed
if "agent" not in st.session_state:
    load_agent_evaluator()

# Chat interface
st.title("🚌GTFS2CODE")
# Display chat history
display_chat_history(st.session_state["fb_agent"], st.session_state.uuid)

# Check if the number of messages has reached the limit
if len(st.session_state.chat_history) >= MAX_MESSAGES:
    st.session_state["show_limit_popup"] = True

# Display dialog when message limit is reached
if st.session_state["show_limit_popup"]:
    st.session_state["is_chat_input_disabled"] = True
    clear_chat()

user_input = st.chat_input(
    "Type your query here...",
    disabled=st.session_state.is_processing or st.session_state.is_chat_input_disabled,
)
# Display sample questions above the message bar only if it's the first question
if not st.session_state.first_question_asked and not user_input:
    st.write("Sample Questions:")
    for i, question in enumerate(st.session_state.questions):
        if st.button(question, key=f"q_{i}"):
            st.session_state.selected_question = question
            # st.rerun()

js = f"""
        <script>
            function insertText(dummy_var_to_force_repeat_execution) {{
                var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeInputValueSetter.call(chatInput, "{st.session_state.selected_question}");
                var event = new Event('input', {{ bubbles: true}});
                chatInput.dispatchEvent(event);
            }}
            insertText({len(st.session_state.chat_history)});
        </script>
        """
st.components.v1.html(js)

# Process user input or selected question
if user_input:
    # Disable chat input after user input
    st.session_state["is_processing"] = True

    if st.session_state.selected_question:
        print(st.session_state.selected_question)
        user_input = st.session_state.selected_question
        st.session_state.selected_question = None

    st.session_state["user_input"] = user_input
    if not st.session_state.first_question_asked:
        st.session_state["first_question_asked"] = True
        st.session_state.selected_question = ""
        st.rerun()

if st.session_state.is_processing:
    user_input = st.session_state["user_input"]
    st.session_state.is_processing = True
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.write(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    process_user_input(user_input)
    # Clear the input box after processing
    st.session_state.user_input = ""
    st.session_state.is_processing = False

    st.rerun()
