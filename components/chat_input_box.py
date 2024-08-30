import streamlit as st

chat_box_js = """
<div id="chat-input-injector" style="display:none;">
    <script>
        function insertText(dummy_var_to_force_repeat_execution) {{
            var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeInputValueSetter.call(chatInput, "{query}");
            var event = new Event('input', {{ bubbles: true}});
            chatInput.dispatchEvent(event);
        }}
        insertText({input});
    </script>
</div>
"""

def set_chat_box(query, input):
    js = chat_box_js.format(query=query, input=input)
    st.components.v1.html(js, height=0)