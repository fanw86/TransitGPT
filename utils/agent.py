import streamlit as st
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from prompts.all_prompts import (
    FINAL_LLM_SYSTEM_PROMPT,
    FINAL_LLM_USER_PROMPT,
    BASE_USER_PROMPT,
    RETRY_PROMPT,
)
from utils.constants import LOG_FILE
from typing import List, Dict, Any, Tuple
from utils.helper import summarize_large_output
from utils.llm_client import OpenAIClient, GroqClient, AnthropicClient
from utils.data_models import ChatInteraction
from utils.eval_code import GTFS_Eval
from prompts.generate_prompt import generate_dynamic_few_shot


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
        self.logger = self._setup_logger(LOG_FILE)
        self.logger.info(
            f"\nInitializing LLMAgent with model: {model}, GTFS: {self.GTFS} and distance unit: {self.distance_unit}"
        )
        self.clients = {
            "gpt": OpenAIClient(),
            "llama": GroqClient(),
            "claude": AnthropicClient(),
        }
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

    def _setup_logger(self, log_file):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create file handler which logs even debug messages
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        # Create console handler with a higher severity log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def get_client_key(model):
        if model.startswith("claude"):
            return "claude"
        if model.startswith("gpt"):
            return "gpt"
        return "llama"

    def create_messages(
        self, system_prompt, user_prompt: str, model: str
    ) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            messages.append({"role": "user", "content": interaction.user_prompt})
            messages.append(
                {"role": "assistant", "content": interaction.assistant_response}
            )
        messages.append({"role": "user", "content": user_prompt})
        if not model.startswith("claude"):
            messages.insert(0, {"role": "system", "content": system_prompt})
        return messages

    def update_chat_history(self, user_prompt: str, response: str) -> None:
        interaction = ChatInteraction(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            assistant_response=response,
        )
        self.chat_history.append(interaction)

    def log_llm_interaction(self, messages: List, response: str) -> None:
        self.logger.info(f"Calling LLM with following messages:\n {messages}")
        self.logger.info(f"Response from LLM: {response}")

    def call_llm(self, query):
        model = self.model
        few_shot_examples = generate_dynamic_few_shot(query, n=3)
        user_prompt = BASE_USER_PROMPT.format(
            user_query=query, examples=few_shot_examples
        )
        messages = self.create_messages(self.system_prompt, user_prompt, model)

        client = self.clients[self.get_client_key(model)]
        response, call_success = client.call(model, messages, self.system_prompt)

        if not call_success:
            self.logger.error(f"LLM call failed: {response}")
        else:
            self.last_response = response
            # Within chat history only store the user query (without the examples) and the response
            self.update_chat_history(query, response)
            self.log_llm_interaction(messages, response)

        return response, call_success

    def evaluate(self, llm_response):
        self.logger.info("Evaluating code from LLM response")
        result, success, error, only_text = self.evaluator.evaluate(llm_response)
        if self.chat_history:
            self.chat_history[-1].evaluation_result = result
            self.chat_history[-1].code_success = success
            self.chat_history[-1].error_message = error
        return result, success, error, only_text

    def evaluate_with_retry(
        self, llm_response: str
    ) -> Tuple[Any, bool, str, bool, str]:
        calls_made = 1  # Initialize with 1 for the initial evaluation

        for retry in range(self.max_retry):
            result, success, error, only_text = self.evaluate(llm_response)
            if success or only_text:
                return result, success, error, only_text, llm_response

            if retry < self.max_retry - 1:  # Don't increment on the last iteration
                calls_made += 1

            st.write(f"Something wasn't right, retrying: attempt {retry + 1}")
            self.logger.info(
                f"Evaluation failed with error: {error}. Retrying attempt {retry + 1}"
            )

            llm_response, call_success = self.call_llm_retry(error)
            if not call_success:
                self.logger.error(f"LLM call failed on retry {retry + 1}")
                break

        # Update the error message with the latest error
        error_message = f"Evaluation failed after {calls_made} {'call' if calls_made == 1 else 'calls'}\nLast Error:\n{error}"
        return None, False, error_message, False, llm_response

    def get_retry_messages(self, error: str) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            messages.append({"role": "user", "content": interaction.user_prompt})
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

    def call_llm_retry(self, error: str) -> str:
        model = self.model
        self.logger.info(f"Retrying LLM call with model: {model}")

        messages = self.get_retry_messages(error)
        client = self.clients[self.get_client_key(model)]
        response, call_success = client.call(model, messages, self.system_prompt)

        self.logger.info(f"LLM Response: {response}")
        return response, call_success

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
        executable_pattern = r"```python\n(.*?)```"
        code_response = re.findall(
            executable_pattern, last_interaction.assistant_response, re.DOTALL
        )
        user_prompt = FINAL_LLM_USER_PROMPT.format(
            question=last_interaction.user_prompt,
            response=code_response,
            evaluation=summarized_evaluation,
            success=last_interaction.code_success,
            error=last_interaction.error_message,
        )
        # Hardcoded model for final LLM call
        model = "gpt-4o-mini"
        messages = self.create_messages(system_prompt, user_prompt, model)
        self.logger.info(f"Following message sent to {model} : {messages}")
        full_response = ""
        client = self.clients["gpt"]
        # Stream the response
        for chunk in client.stream_call(model, messages):
            full_response += chunk
            stream_placeholder.markdown(full_response + "▌")

        self.logger.info("Final response from LLM:\n %s", full_response)
        return full_response

    def evaluate_code(self, retry_code, llm_response: str):
        with st.status("Evaluating code..."):
            if retry_code:
                return self.evaluate_with_retry(llm_response)
            else:
                result, success, error, only_text = self.evaluate(llm_response)
                return result, success, error, only_text, llm_response

    def reset(self):
        self.last_response = None
        self.chat_history = []
        self.result = None

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
