import streamlit as st
from datetime import datetime
from rich.traceback import install as install_rich_traceback
from prompts.all_prompts import (
    FINAL_LLM_SYSTEM_PROMPT,
    FINAL_LLM_USER_PROMPT,
    BASE_USER_PROMPT,
    RETRY_PROMPT,
)
from utils.constants import LOG_FILE, FINAL_LLM
from typing import List, Dict, Any, Tuple
from utils.helper import summarize_large_output
from gtfs_agent.llm_client import OpenAIClient, GroqClient, AnthropicClient
from utils.data_models import ChatInteraction
from evaluator.eval_code import GTFS_Eval
from prompts.generate_prompt import generate_dynamic_few_shot
from streamlit_folium import folium_static
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow, task
from utils.logger import setup_logger, reset_logger

Traceloop.init(disable_batch=True, api_key=st.secrets["TRACELOOP_API_KEY"])

class LLMAgent:
    def __init__(
        self,
        file_mapping,
        model: str,
        max_retry=3,
        max_chars=12000,
        max_rows=50,
    ):
        self.evaluator = GTFS_Eval(file_mapping)
        self.model = model
        # Initialize with first entry of file_mapping
        self.GTFS = list(file_mapping.keys())[0]
        self.distance_unit = file_mapping[self.GTFS]["distance_unit"]

        # Set Hyperparameters
        self.max_retry = max_retry
        self.max_chars = max_chars
        self.max_rows = max_rows

        ## Initialize the logger and clients
        self.logger = setup_logger(LOG_FILE)
        self.logger.info(
            f"\nInitializing LLMAgent with model: {model}, GTFS: {self.GTFS} and distance unit: {self.distance_unit}"
        )
        self.clients = {
            "gpt": OpenAIClient(),
            "llama": GroqClient(),
            "claude": AnthropicClient(),
        }

        # Set the logger for each client
        for client in self.clients.values():
            client.set_logger(self.logger)

        self.result = None
        self.last_response = None
        self.chat_history = []
        self.load_system_prompt()

    def load_system_prompt(self):
        ## Load system prompt
        self.system_prompt = self.evaluator.get_system_prompt(
            self.GTFS, self.distance_unit
        )
        self.logger.info(
            f"Loaded system prompt for GTFS: {self.GTFS} with distance unit: {self.distance_unit}"
        )

    @staticmethod
    def get_client_key(model):
        if model.startswith("claude"):
            return "claude"
        if model.startswith("gpt") or model.startswith("o1"):
            return "gpt"
        return "llama"

    def create_messages(
        self, system_prompt, user_prompt: str, model: str
    ) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            if interaction.user_prompt.strip():
                messages.append({"role": "user", "content": interaction.user_prompt})
            else:
                print(f"Empty user prompt: {interaction.user_prompt}")
                self.logger.warning(
                    f"Empty user prompt found at index {interaction}: {interaction.user_prompt!r}"
                )
                messages.append({"role": "user", "content": "..."})
            if interaction.assistant_response.strip():
                messages.append(
                    {"role": "assistant", "content": interaction.assistant_response}
                )
        if user_prompt.strip():
            messages.append({"role": "user", "content": user_prompt})
        if not model.startswith("claude"):
            messages.insert(0, {"role": "system", "content": system_prompt})
        return messages

    def update_chat_history(self, user_prompt: str, response: str, result: Any = None, success: bool = None, error: str = None, only_text: bool = None) -> None:
        if user_prompt.strip() or response.strip():
            interaction = ChatInteraction(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                assistant_response=response,
                evaluation_result=result,
                code_success=success,
                error_message=error,
                only_text=only_text,
            )
            self.chat_history.append(interaction)

    @task(name="Call LLM")
    def call_llm(self, query):
        model = self.model
        self.logger.info(f"User Query: {query}. Calling {model}...")
        few_shot_examples = generate_dynamic_few_shot(query, n=3)
        user_prompt = BASE_USER_PROMPT.format(
            user_query=query, examples=few_shot_examples
        )
        messages = self.create_messages(self.system_prompt, user_prompt, model)
        self.logger.info(f"Calling LLM with following messages:\n {messages}")
        client = self.clients[self.get_client_key(model)]
        response, call_success = client.call(model, messages, self.system_prompt)

        if not call_success:
            self.logger.error(f"LLM call failed: {response}")
        else:
            self.last_response = response
            self.logger.info(f"Response from LLM: {response}")

        return response, call_success

    @task(name="Execute Code")
    def execute(self, user_input: str, llm_response: str):
        self.logger.info("Evaluating code from LLM response")
        output = self.evaluator.evaluate(llm_response)
        result = output["code_output"]
        success = output["eval_success"]
        error = output["error_message"]
        only_text = output["only_text"]
        self.update_chat_history(
            user_input,
            llm_response,
            result,
            success,
            error,
            only_text
        )
        return result, success, error, only_text

    @task(name="Evaluate with Retry")
    def evaluate_with_retry(self, user_input: str, llm_response: str) -> Tuple[Any, bool, str, bool, str]:
        errors = []

        for attempt in range(1, self.max_retry + 1):
            result, success, error, only_text = self.execute(user_input, llm_response)
            
            if isinstance(result, dict) and 'map' in result:
                success, error = self._check_map_renderability(result['map'])

            if success or only_text or "TimeoutError" in error:
                return result, success, "\n".join(errors), only_text, llm_response

            errors.append(f"Attempt {attempt}: {error}")
            self._log_retry_attempt(attempt, error)

            if attempt < self.max_retry:
                llm_response, call_success = self.call_llm_retry(error)
                if not call_success:
                    errors.append(f"Attempt {attempt + 1}: LLM call failed")
                    break

        error_message = self._format_error_message(attempt, errors)
        return None, False, error_message, False, llm_response

    def _check_map_renderability(self, map_obj):
        try:
            with st.spinner("Checking map renderability..."):
                folium_static(map_obj)
            return True, None
        except Exception as e:
            return False, f"Error rendering Folium map: {str(e)}"

    def _log_retry_attempt(self, attempt, error):
        st.write(f"Something wasn't right, retrying: attempt {attempt}")
        self.logger.info(
            f"Evaluation failed with error: {error}. Retrying attempt {attempt}"
        )

    def _format_error_message(self, attempts, errors):
        call_str = "call" if attempts == 1 else "calls"
        return f"Evaluation failed after {attempts} {call_str}\nErrors:\n" + "\n".join(
            errors
        )

    def get_retry_messages(self, error: str) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            if interaction.user_prompt.strip():
                messages.append({"role": "user", "content": interaction.user_prompt})
            if interaction.assistant_response.strip():
                messages.append(
                       {"role": "assistant", "content": interaction.assistant_response}
            )

        # Add the error message as part of the last assistant's response
        if messages and messages[-1]["role"] == "assistant":
            messages[-1]["content"] += f"\n\nError: {error}"
        else:
            # If the last message was not from the assistant, add a new assistant message with the error
            messages.append({"role": "assistant", "content": f"Error: {error}"})

        # Add the retry prompt as a new user message
        messages.append({"role": "user", "content": RETRY_PROMPT.format(error=error)})

        return messages

    @task(name="Call LLM Retry")
    def call_llm_retry(self, error: str) -> str:
        model = self.model
        self.logger.info(f"Retrying LLM call with model: {model}")

        messages = self.get_retry_messages(error)
        client = self.clients[self.get_client_key(model)]
        response, call_success = client.call(model, messages, self.system_prompt)

        self.logger.info(f"LLM Response: {response}")
        return response, call_success

    @task(name="Final LLM Call")
    def call_final_llm(self, stream_placeholder):
        system_prompt = FINAL_LLM_SYSTEM_PROMPT
        last_interaction = self.chat_history[-1] if self.chat_history else None

        if not last_interaction:
            self.logger.warning("No interactions in chat history for final LLM call")
            return "No previous interaction available."
        # Additional check to ensure that large dataframes are not passed to the LLM
        summarized_evaluation = summarize_large_output(
            last_interaction.evaluation_result, self.max_rows, self.max_chars
        )
        # executable_pattern = r"```python\n(.*?)```"
        # code_response = re.findall(
        #     executable_pattern, last_interaction.assistant_response, re.DOTALL
        # )
        user_prompt = FINAL_LLM_USER_PROMPT.format(
            question=last_interaction.user_prompt,
            response=last_interaction.assistant_response,  # ATTENTION: Passing whole response instead of code response
            evaluation=summarized_evaluation,
            success=last_interaction.code_success,
            error=last_interaction.error_message,
        )
        # Hardcoded model for final LLM call
        model = FINAL_LLM
        messages = self.create_messages(system_prompt, user_prompt, model)
        self.logger.info(f"Final LLM message sent to {model} : {messages}")
        full_response = ""
        client = self.clients["gpt"]
        # Stream the response
        for chunk in client.stream_call(model, messages):
            full_response += chunk
            stream_placeholder.markdown(full_response + "▌")

        self.logger.info("Final response from LLM:\n %s", full_response)
        return full_response

    @task(name="Evaluate Code")
    def evaluate_code(self, user_input, llm_response, retry_code):
        with st.status("Evaluating code..."):
            if retry_code:
                return self.evaluate_with_retry(user_input, llm_response)
            else:
                result, success, error, only_text = self.execute(user_input, llm_response)
                return result, success, error, only_text, llm_response

    def reset(self):
        self.last_response = None
        self.chat_history = []
        self.result = None
        self._reset_logger()

    def _reset_logger(self):
        self.logger = reset_logger(self.logger, LOG_FILE)

        # Update logger for each client
        for client in self.clients.values():
            client.set_logger(self.logger)

    def update_agent(self, GTFS, model, distance_unit):
        self.reset()
        self.evaluator.reset()
        self.GTFS = GTFS
        self.model = model
        self.distance_unit = distance_unit
        self.logger.info(
            f"Updating LLMAgent with model: {model}, GTFS: {GTFS} and distance unit: {distance_unit}"
        )
        self.load_system_prompt()

    @workflow(name="LLM Agent Workflow")
    def run_workflow(self, user_input: str, retry_code: bool = False):
        llm_response, call_success = self.call_llm(user_input)
        if not call_success:
            return None, False, "LLM call failed", False, llm_response, None

        result, success, error, only_text, llm_response = self.evaluate_code(
            user_input, llm_response, retry_code=retry_code
        )
        
        # New step: Validate evaluation results
        validation_response = self.validate_evaluation(user_input, llm_response, result, success, error, only_text)
        
        if success or only_text:
            final_response = self.call_final_llm(st.empty())
        else:
            final_response = None

        return result, success, error, only_text, llm_response, final_response, validation_response

    @task(name="Validate Evaluation")
    def validate_evaluation(self, user_input: str, llm_response: str, result: Any, success: bool, error: str, only_text: bool):
        validation_prompt = f"""
        User Input: {user_input}
        
        Your Response:
        {llm_response}
        
        Evaluation Result:
        Success: {success}
        Error: {error}
        Only Text: {only_text}
        Result: {result}
        
        Please validate the evaluation results:
        Validate if the response to the user query is correct and if result is as expected.
        
        Return (True, None) if everything is correct, (False, "Reason for failure") if something is incorrect.
        """
        
        messages = self.create_messages(self.system_prompt, validation_prompt, self.model)
        client = self.clients["gpt"]
        validation_response, _ = client.call(FINAL_LLM, messages, self.system_prompt)
        
        self.logger.info(f"Validation response from LLM: {validation_response}")
        return validation_response