import json

# Set timeout to 3 minutes
TIMEOUT_SECONDS = 3 *60

# File to store sample questions
QUESTIONS_FILE = "data/sample_questions.json"
QUESTION_LIMIT = 3

# File to store Logs
LOG_FILE = "logs/llm_agent.log"

# Few shot examples
FEW_SHOT_EXAMPLES_FILE = "data/few_shot.yaml"


# Define the maximum number of messages to keep in the chat history
MAX_MESSAGES = 16

FILE_MAPPING_LOC = "gtfs_data/file_mapping.json"
file_mapping = json.loads(open(FILE_MAPPING_LOC).read())

LLMs = [
    "claude-3-5-sonnet-20240620",
    "gpt-4o",
    "gpt-4o-mini",
    "llama-3.1-8b-instant",
    # "gpt-3.5-turbo",
]

disclaimer_text = """
This chatbot is an AI-powered tool designed to assist with GTFS data analysis and code generation. Please be aware of the following:

1. **AI Limitations:** The chatbot may occasionally provide inaccurate or incomplete information. Always verify critical information.
2. **Code Execution:** The code generated and executed is based on AI suggestions. Review all code before using it in any production environment.
3. **Data Privacy:** Do not input sensitive or personal information into the chatbot.
4. **Updates:** GTFS data and transit information may change. Ensure you're using the most up-to-date data for accurate results.

By using this chatbot, you acknowledge and agree to these terms.
"""

copyright_text = "Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)"
