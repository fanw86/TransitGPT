# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup & Installation
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python utils/generate_feed_pickles.py  # Generate GTFS pickle files (required)
```

### Running the Application
```bash
streamlit run chat_app.py                    # Default port 8501
streamlit run chat_app.py --server.port 8080  # Custom port
```

### Docker Commands
```bash
docker build -t transitgpt .
docker run -p 8501:8501 -v $(pwd)/gtfs_data:/app/gtfs_data transitgpt
```

### Testing
```bash
pytest tests/                    # Run all tests
pytest tests/test_eval_code.py  # Run specific test file
pytest -v                       # Verbose output
```

## Architecture Overview

TransitGPT implements a **4-step LLM workflow** for analyzing GTFS (General Transit Feed Specification) data:

1. **Moderation** (`call_moderation_llm`) - Filters irrelevant queries
2. **Main LLM** (`call_main_llm`) - Generates Python code for GTFS analysis
3. **Code Execution** (`execute`) - Runs generated code in sandboxed environment with 5-minute timeout
4. **Summary** (`call_summary_llm`) - Formats results into chat response

### Core Components

**LLM Agent (`gtfs_agent/agent.py`)**
- Central orchestrator implementing the `@workflow` decorated `run_workflow()` method
- Manages state, retries, and error handling across all steps
- **Critical**: Always returns dictionary format from `run_workflow()`, never tuples

**LLM Clients (`gtfs_agent/llm_client.py`)**
- **Current Configuration**: Uses only OpenRouter client (`OpenRouterClient`) for all models
- All clients inherit from `LLMClient` abstract base class
- Client selection via `get_client_key()` method (currently always returns "openrouter")

**Code Evaluator (`evaluator/eval_code.py`)**
- Executes LLM-generated Python code in isolated thread environment
- Timeout handling (5 minutes default)
- Expects code to assign results to `result` variable
- Returns structured dictionary: `{"code_output", "eval_success", "error_message", "only_text"}`

**GTFS Data Management**
- GTFS feeds stored in `gtfs_data/` directory
- Configuration in `gtfs_data/file_mapping.json`
- Pickled feeds in `gtfs_data/feed_pickles/` for performance
- Loader classes in `gtfs_agent/gtfs_loader.py`

### Configuration System (`utils/constants.py`)

**LLM Configuration**:
- `SUMMARY_LLM`: Currently "deepseek/deepseek-r1-0528:free"  
- `MODERATION_LLM`: Currently "deepseek/deepseek-r1-0528:free"
- `LLMs`: List of available models in UI dropdown
- Temperature settings per role (Main: 0.2, Retry: 0.4, Summary: 0.7)

**System Limits**:
- `TIMEOUT_SECONDS`: 300 (5 minutes for code execution)
- `MAX_MESSAGES`: 16 (chat history limit)
- `FEW_SHOT_EXAMPLE_LIMIT`: 3

## Critical Implementation Details

### API Key Configuration
```toml
# .streamlit/secrets.toml
[general]
OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
```
Access via: `st.secrets.general.OPENROUTER_API_KEY` (NOT `st.secrets["OPENROUTER_API_KEY"]`)

### Error Handling Requirements
- `run_workflow()` must **always** return a dictionary, never tuples
- Failed LLM calls should return properly formatted dictionary with `eval_success: False`
- The `evaluate_code_with_retry()` function returns 6-element tuple, properly unpacked in workflow

### Dynamic Prompt Generation
- System prompts generated dynamically per GTFS feed in `prompts/generate_prompt.py`
- Few-shot examples loaded from `data/few_shot.yaml` and `data/few_shot_viz.yaml`
- Examples selected using sentence transformers for semantic similarity

### Visualization Support
- Supports matplotlib, plotly, and folium visualizations
- Map renderability checked via `_check_map_renderability()`
- Visualization toggle affects prompt generation and system behavior

## Data Flow Architecture

```
User Query → Moderation → Main LLM → Code Execution → Summary → UI Response
           ↓            ↓         ↓              ↓
       Block Invalid   Generate   Execute in     Format for
       Queries         Python     Sandbox       Chat Display
```

**State Management**:
- Streamlit session state manages chat history, agent instances, user preferences
- Chat history stored as `ChatInteraction` objects with success/failure tracking
- Agent maintains internal state for current GTFS feed, distance units, visualization settings

## Adding New GTFS Feeds

1. Add GTFS zip file to `gtfs_data/[Agency Name]/gtfs.zip`
2. Update `gtfs_data/file_mapping.json`:
   ```json
   "Agency Name": {
     "file_loc": "gtfs_data/Agency Name/gtfs.zip",
     "distance_unit": "m|km|ft",
     "pickle_loc": "gtfs_data/feed_pickles/Agency_Name_gtfs_loader.pkl"
   }
   ```
3. Run `python utils/generate_feed_pickles.py`

## Few-Shot Example System

**Structure**: Examples in YAML format with `feed`, `question`, `answer`, and `additional_info` fields
- `data/few_shot.yaml`: Non-visualization examples
- `data/few_shot_viz.yaml`: Examples generating plots/maps

**Selection**: Uses sentence transformers to find 3 most semantically similar examples to user query

## Current LLM Provider Setup

**OpenRouter Integration**: All workflow steps now route through OpenRouter API
- Models configured in `utils/constants.py` LLMs list
- Single client initialization: `self.clients = {"openrouter": OpenRouterClient()}`
- Supports multiple model providers through OpenRouter's unified API

## Testing Strategy

Tests use pytest framework with test data in `tests/test_pickle_feed/`:
- `test_eval_code.py`: Code execution and evaluation
- `test_gtfs_loader.py`: GTFS data loading
- `test_llm_client.py`: LLM client functionality
- `test_data_models.py`: Data structure validation

## Known Issues & Solutions

### OpenRouter Integration Problems Fixed

**1. API Key Access Issue**
- **Problem**: `KeyError: 'st.secrets has no key "OPENROUTER_API_KEY"`
- **Root Cause**: Code accessed `st.secrets["OPENROUTER_API_KEY"]` but key was nested under `[general]` section
- **Fix**: Changed to `st.secrets.general.OPENROUTER_API_KEY` in `gtfs_agent/llm_client.py:200`

**2. Hardcoded Client References**
- **Problem**: Functions still referenced specific clients like `self.clients["gpt"]` after switching to OpenRouter-only
- **Locations**: `call_summary_llm()` (line 345), `validate_evaluation()` (line 499)
- **Fix**: Replaced with dynamic lookup: `client = self.clients[self.get_client_key(model)]`

**3. Critical Tuple vs Dictionary Bug**
- **Problem**: `TypeError: tuple indices must be integers or slices, not str`
- **Root Cause**: When LLM calls failed, `run_workflow()` returned tuple `(None, False, error_message, True, None, None, None)` instead of expected dictionary
- **Location**: `gtfs_agent/agent.py:430` 
- **Fix**: Return properly formatted dictionary:
  ```python
  return {
      "task": task,
      "code_output": None,
      "eval_success": False,
      "error_message": llm_response,
      "only_text": True,
      "main_response": llm_response,
      "summary_response": None,
      "token_usage": main_llm_usage,
      "execution_time": execution_time,
  }
  ```

**4. Client Selection Logic**
- **Problem**: `get_client_key()` method didn't handle OpenRouter model formats
- **Fix**: Updated to always return "openrouter" since we use single provider
- **Previous logic**: Checked model prefixes (claude, gpt, gemini)
- **Current logic**: `return "openrouter"` for all models

**5. Model Configuration Mismatch**
- **Problem**: System configured for multiple providers but only OpenRouter initialized
- **Fix**: Updated `utils/constants.py`:
  - Removed conditional API key checks
  - Set all models to use OpenRouter format (`"provider/model-name"`)
  - Configured all workflow steps to use same provider

### General Debugging Approach

**For Tuple vs Dictionary Errors**:
1. Add debug prints to check return types: `print(f"result type = {type(result)}")`
2. Verify all `run_workflow()` code paths return dictionaries
3. Check that no internal functions leak tuples to the main workflow

**For LLM Client Issues**:
1. Verify API key format matches provider requirements
2. Check that `get_client_key()` returns valid keys from `self.clients`
3. Ensure all workflow steps use consistent client selection logic

**For Configuration Problems**:
1. Verify `st.secrets` structure matches TOML file format
2. Check that model names in UI match those configured in `LLMs` list
3. Ensure temperature and timeout settings are appropriate for each workflow step