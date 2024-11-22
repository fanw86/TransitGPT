# TransitGPT 🚌

TransitGPT is a specialized chatbot that helps transit enthusiasts retrieve transit information and analyze GTFS feeds via code.


<p align="center">
  <img src="images/Viz_cap.png" alt="GTFS2CODE Visualization Capabilities" style="max-width: 60%; width : 600px;">
</p>

## Architecture Overview

<p align="center">
  <img src="images/transitGPTArch.png" alt="GTFS2CODE Architecture" style="max-width: 60%; width : 600px">
</p>

This diagram illustrates the high-level architecture of the GTFS2CODE system, showing how different components interact.

## Features

- Interactive chat interface for querying GTFS data
- Code generation and execution for GTFS analysis
- Support for multiple LLM models
- Visualization of results using Matplotlib, Plotly, and Folium
- Feedback system for user interactions

## Setup

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure you have the necessary GTFS data files and update the `gtfs_data/file_mapping.json` accordingly
4. Generate pickled GTFS feeds for faster loading:
   ```bash
   python utils/generate_feed_pickles.py
   ```
5. Set up your environment variables for API keys and other sensitive information:
   - Create a `.streamlit/secrets.toml` file in your project directory.
   - Add your API keys in the following format:
     ```toml
     [general]
     OPENAI_API_KEY = "your_openai_api_key"
     GROQ_API_KEY = "your_groq_api_key"
     ANTHROPIC_API_KEY = "your_anthropic_api_key"
     GMAP_API = "your_google_maps_api_key"
     ```
   - Ensure that this file is not included in version control by adding it to your `.gitignore`.

6. Run the Streamlit app:
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
- `utils/`: Utility functions and helper methods
- `prompts/`: LLM prompts and examples
- `data/`: Sample questions and few-shot examples
- `gtfs_data/`: GTFS feed files and mappings
- `gtfs_agent/`: GTFS data loading, processing, and LLM agent
- `evaluator/`: Code execution and evaluation
- `tests/`: Unit tests for various components

## Key Files

- `gtfs_agent/gtfs_loader.py`: GTFS data loading and processing
- `gtfs_agent/agent.py`: LLM Agent implementation
- `evaluator/eval_code.py`: Code execution and evaluation
- `utils/feedback.py`: Feedback collection system
- `prompts/generate_prompt.py`: Dynamic prompt generation
- `utils/generate_feed_pickles.py`: Generate pickled GTFS feeds
- `utils/constants.py`: Constant values used across the project
- `utils/helper.py`: Helper functions for various tasks
- `gtfs_agent/llm_client.py`: LLM API clients for different models

## Disclaimer

This chatbot is an AI-powered tool designed to assist with GTFS data analysis and code generation. Please be aware of its limitations, verify critical information, and review generated code before use in production environments.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Copyright

Copyright © 2024 [Urban Traffic & Economics Lab (UTEL)](https://github.com/UTEL-UIUC)
