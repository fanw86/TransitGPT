# GTFS2CODE 🚌

GTFS2CODE is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code.

## Features

- Interactive chat interface for querying GTFS data
- Code generation and execution for GTFS analysis
- Support for multiple LLM models
- Visualization of results using Matplotlib, Plotly, and Folium
- Feedback system for user interactions

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure you have the necessary GTFS data files and update the `gtfs_data/file_mapping.json` accordingly
3. Generate pickled GTFS feeds for faster loading:
   ```bash
   python utils/generate_feed_pickles.py
   ```
4. Set up your environment variables for API keys and other sensitive information
5. Run the Streamlit app:
   ```bash
   streamlit run chat_app.py
   ```

## Usage

1. Select an LLM model and GTFS feed from the sidebar
2. Type your query in the chat input or select a sample question
3. View the generated code, execution results, and visualizations
4. Provide feedback on the responses

## Configuration

- LLM models available: Claude 3.5 Sonnet, GPT-4o, GPT-4o-mini, Llama 3.1 8B Instant
- Maximum chat history: 16 messages
- Timeout for code execution: 3 minutes

## Project Structure

- `chat_app.py`: Main Streamlit application
- `components/`: UI components and interface setup
- `utils/`: Utility functions and core logic
- `prompts/`: LLM prompts and examples
- `data/`: Sample questions and few-shot examples
- `gtfs_data/`: GTFS feed files and mappings

## Key Files

- `utils/gtfs_loader.py`: GTFS data loading and processing
- `utils/agent.py`: LLM Agent implementation
- `utils/eval_code.py`: Code execution and evaluation
- `utils/feedback.py`: Feedback collection system
- `prompts/generate_prompt.py`: Dynamic prompt generation

## Disclaimer

This chatbot is an AI-powered tool designed to assist with GTFS data analysis and code generation. Please be aware of its limitations, verify critical information, and review generated code before use in production environments.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Copyright

Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)