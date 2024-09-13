import json
import streamlit as st

# Set timeout to 5 minutes
TIMEOUT_SECONDS = 5 * 60 

# File to store sample questions
QUESTIONS_FILE = "data/sample_questions.json"
QUESTION_LIMIT = 3

# File to store Logs
LOG_FILE = "logs/llm_agent.log"

# Few shot examples
FEW_SHOT_EXAMPLES_FILE = "data/few_shot.yaml"

## LLM HYPERPARAMETERS
# Define the maximum number of messages to keep in the chat history
MAX_MESSAGES = 16
MAIN_LLM_TEMPERATURE = 0.5
FINAL_LLM_TEMPERATURE = 0.7

TOP_P = 0.9
REPETITION_PENALTY = 1.1

FILE_MAPPING_LOC = "gtfs_data/file_mapping.json"
file_mapping = json.loads(open(FILE_MAPPING_LOC).read())

# Populate LLMs based on available API keys
LLMs = []

if "ANTHROPIC_API_KEY" in st.secrets:
    LLMs.extend(["claude-3-5-sonnet-20240620", "claude-3-haiku-20240307"])

if "OPENAI_API_KEY" in st.secrets:
    LLMs.extend(["gpt-4o-2024-08-06", "gpt-4o-mini"])

if "GROQ_API_KEY" in st.secrets:
    LLMs.extend(["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "gemma2-9b-it"])

disclaimer_text = """
This chatbot is an AI-powered tool designed to assist with GTFS data analysis and code generation. Please be aware of the following:

1. **AI Limitations:** The chatbot may occasionally provide inaccurate or incomplete information. Always verify critical information.
2. **Code Execution:** The code generated and executed is based on AI suggestions. Review all code before using it in any production environment.
3. **Data Privacy:** Do not input sensitive or personal information into the chatbot.
4. **Updates:** GTFS data and transit information may change. Ensure you're using the most up-to-date data for accurate results.

By using this chatbot, you acknowledge and agree to these terms.
"""

copyright_text = "Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)"
