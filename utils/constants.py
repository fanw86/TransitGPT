file_mapping = {
    "CUMTD": "gtfs_data/Urbana-Champaign Urbana Mass Transit District (MTD)-IL/gtfs.zip",
    "SFMTA": "gtfs_data/San Francisco-San Francisco Municipal Transportation Agency (SFMTA, Muni)-CA/gtfs.zip",
}

LLMs = [
    "llama-3.1-70b-versatile",
    "claude-3-5-sonnet-20240620",
    "gpt-4o-mini",
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