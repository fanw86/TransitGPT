# GTFS2CODE 🚌

GTFS2CODE is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code.

## Features

- Interactive chat interface for querying GTFS data
- Code generation and execution for GTFS analysis
- Support for multiple LLM models
- Visualization of results using Matplotlib, Plotly, and Folium
- Feedback system for user interactions

## Setup

1. Install the required dependencies (Streamlit, Folium, Pandas, Matplotlib, Plotly)
2. Ensure you have the necessary GTFS data files and update the `file_mapping.json` accordingly
3. Run the Streamlit app: `streamlit run chat_app.py`

## Usage

1. Select an LLM model and GTFS feed from the sidebar
2. Type your query in the chat input or select a sample question
3. View the generated code, execution results, and visualizations
4. Provide feedback on the responses

## Configuration

- LLM models available: Claude 3.5 Sonnet, GPT-4, GPT-4 Mini, Llama 3.1 8B Instant
- Maximum chat history: 16 messages
- Timeout for code execution: 3 minutes

## Files
- `chat_app.py`: Main Streamlit application
- `components/sidebar.py`: Sidebar setup and configuration
- `components/chat_interface.py`: Chat interface and message display
- `utils/constants.py`: Constants and configuration values
- `utils/response_processor.py`: Processing user input and cancellations
- `utils/state.py`: Managing session state
- `utils/agent.py`: LLM Agent implementation
- `utils/feedback.py`: Feedback collection system

## Disclaimer

This chatbot is an AI-powered tool designed to assist with GTFS data analysis and code generation. Please be aware of its limitations, verify critical information, and review generated code before use in production environments.

## Copyright

Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)