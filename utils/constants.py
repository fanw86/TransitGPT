# File to store sample questions
QUESTIONS_FILE = "data/sample_questions.json"
QUESTION_LIMIT = 3

# File to store Logs
LOG_FILE = "logs/llm_agent.log"

# Define the maximum number of messages to keep in the chat history
MAX_MESSAGES = 10

file_mapping = {
    "DART": {
        "file_loc": "gtfs_data/Dallas-Dallas Area Rapid Transit (DART)-TX/gtfs.zip",
        "distance_unit": "km",
    },
    "SFMTA": {
        "file_loc": "gtfs_data/San Francisco-San Francisco Municipal Transportation Agency (SFMTA, Muni)-CA/gtfs.zip",
        "distance_unit": "km",
    },
    "MBTA": {
        "file_loc": "gtfs_data/Boston-Massachusetts Bay Transportation Authority (MBTA)-MA/gtfs.zip",
        "distance_unit": None,
    },
    "CUMTD": {
        "file_loc": "gtfs_data/Urbana-Champaign Urbana Mass Transit District (MTD)-IL/gtfs.zip",
        "distance_unit": "m",
    },
    "VTA": {
        "file_loc": "gtfs_data/San Jose-Santa Clara Valley Transportation Authority (VTA)-CA/gtfs.zip",
        "distance_unit": "km",
    },
    "AC Transit": {
        "file_loc": "gtfs_data/Oakland-Alameda-Contra Costa Transit District (AC Transit)-CA/gtfs.zip",
        "distance_unit": "m",
    },
    "samTrans": {
        "file_loc": "gtfs_data/San Mateo-San Mateo County Transit District (samTrans)-CA/gtfs.zip",
        "distance_unit": None,
    },
    "Caltrain": {
        "file_loc": "gtfs_data/San Francisco-Caltrain-CA/gtfs.zip",
        "distance_unit": "m",
    },
}

LLMs = [
    "claude-3-5-sonnet-20240620",
    "gpt-4o-mini",
    "llama-3.1-70b-versatile",
    "gpt-3.5-turbo",
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
