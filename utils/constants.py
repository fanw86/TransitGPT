import json
import streamlit as st

# Set timeout to 5 minutes
TIMEOUT_SECONDS = 5 * 60

# File to store sample questions
QUESTIONS_FILE = "data/sample_questions.json"
QUESTION_LIMIT = 3

# File to store Logs
LOG_FILE = "logs/llm_agent.log"

# Prompt Output Location
PROMPT_OUTPUT_LOC = "prompts/generated_prompt.md"

# Few shot examples
FEW_SHOT_EXAMPLES_FILE = "data/few_shot.yaml"
FEW_SHOT_EXAMPLES_FILE_VIZ = "data/few_shot_viz.yaml"
FEW_SHOT_EXAMPLE_LIMIT = 3

## LLM HYPERPARAMETERS
# Define the maximum number of messages to keep in the chat history
MAX_MESSAGES = 16
MAIN_LLM_TEMPERATURE = 0.2  # Recommend using 0.2-0.5 for coding related tasks
MAIN_LLM_RETRY_TEMPERATURE = 0.4 # Recommend using 0.4-0.7 for retry tasks. Typically, the retry task is higher to avoid repeating the same mistakes.
SUMMARY_LLM = "deepseek/deepseek-r1-0528:free"
SUMMARY_LLM_TEMPERATURE = 0.7

MODERATION_LLM = "deepseek/deepseek-r1-0528:free"
MODERATION_LLM_TEMPERATURE = 0.5
MODERATION_LLM_MAX_TOKENS = 2

FILE_MAPPING_LOC = "gtfs_data/file_mapping.json"
file_mapping = json.loads(open(FILE_MAPPING_LOC).read())

# Enable Tracing
ENABLE_TRACING = True

# Only use OpenRouter LLMs
LLMs = [
    "deepseek/deepseek-r1-0528:free",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-8b-instruct",
    "google/gemini-2.0-flash-exp",
    "qwen/qwen-2.5-coder-32b-instruct"
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
