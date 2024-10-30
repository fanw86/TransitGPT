import streamlit as st
import time
from prompts.all_prompts import (
    SUMMARY_LLM_SYSTEM_PROMPT,
    SUMMARY_LLM_USER_PROMPT,
    RETRY_PROMPT,
    MAIN_LLM_USER_PROMPT,
)
from prompts.generate_prompt import generate_dynamic_few_shot
from utils.constants import LOG_FILE, SUMMARY_LLM, MAIN_LLM_RETRY_TEMPERATURE
from typing import List, Dict, Any, Tuple
from utils.helper import summarize_large_output
from gtfs_agent.llm_client import OpenAIClient, GroqClient, AnthropicClient
from utils.data_models import ChatInteraction
from evaluator.eval_code import GTFS_Eval
from streamlit_folium import folium_static
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow, task
from utils.logger import setup_logger, reset_logger


class LLMAgent:
    def __init__(
        self,
        file_mapping,
        model: str,
        allow_viz: bool = False,
        max_retry=3,
        max_chars=2000,
        max_rows=20,
    ):
        self.evaluator = GTFS_Eval(file_mapping)
        self.model = model
        # Initialize with first entry of file_mapping
        self.GTFS = list(file_mapping.keys())[0]
        self.distance_unit = file_mapping[self.GTFS]["distance_unit"]
        self.allow_viz = allow_viz

        # Set Hyperparameters
        self.max_retry = max_retry
        self.max_chars = max_chars
        self.max_rows = max_rows

        ## Initialize the logger and clients
        self.logger = setup_logger(LOG_FILE)
        self.logger.info(
            f"Updating LLMAgent with model: [red]{self.model}[/red], GTFS: [red]{self.GTFS}[/red], distance unit: [red]{self.distance_unit}[/red], and allow_viz: [green]{self.allow_viz}[/green]"
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
        self.allow_viz = allow_viz
        self.load_system_prompt(self.GTFS, self.distance_unit, self.allow_viz)
        if "TRACELOOP_API_KEY" in st.secrets:
            Traceloop.init(disable_batch=True, api_key=st.secrets["TRACELOOP_API_KEY"])

    def load_system_prompt(self, GTFS, distance_unit, allow_viz):
        ## Load system prompt
        self.system_prompt = self.evaluator.get_system_prompt(
            GTFS, distance_unit, allow_viz
        )
        self.logger.info(
            f"Loaded system prompt for GTFS: {self.GTFS} with distance unit: {self.distance_unit} and visualization: {self.allow_viz}"
        )

    @staticmethod
    def get_client_key(model):
        if model.startswith("claude"):
            return "claude"
        if model.startswith("gpt") or model.startswith("o1"):
            return "gpt"
        return "llama"

    def create_messages(self, user_prompt: str, model: str) -> List[Dict[str, str]]:
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
        return messages

    def update_chat_history(
        self,
        user_prompt: str,
        response: str,
        result: Any = None,
        success: bool = None,
        error: str = None,
        only_text: bool = None,
    ) -> None:
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

    @task(name="Call Main LLM")
    def call_main_llm(self, user_input: str) -> Tuple[str, bool, str]:
        model = self.model
        self.logger.info(f"Calling LLM with model: {model}")
        few_shot_examples = generate_dynamic_few_shot(user_input, self.allow_viz)
        user_prompt = MAIN_LLM_USER_PROMPT.format(
            user_query=user_input, examples=few_shot_examples
        )
        messages = self.create_messages(user_prompt, model)
        client = self.clients[self.get_client_key(model)]
        self.logger.info(f"Messages sent to {model}: {messages}\n")
        response, call_success = client.call(model, messages, self.system_prompt)
        return response, call_success

    @task(name="Execute Code")
    def execute(self, user_input: str, llm_response: str):
        self.logger.info("Evaluating code from LLM response")
        output = self.evaluator.evaluate(llm_response)
        result = output["code_output"]
        success = output["eval_success"]
        error = output["error_message"]
        only_text = output["only_text"]
        return result, success, error, only_text

    @task(name="Evaluate Code with Retry")
    def evaluate_code_with_retry(
        self, user_input: str, llm_response: str, retry_code: bool
    ) -> Tuple[Any, bool, str, bool, str]:
        errors = []
        attempts_allowed = self.max_retry if retry_code else 1
        with st.status("Evaluating code..."):
            for attempt in range(1, attempts_allowed + 1):
                result, success, error, only_text = self.execute(
                    user_input, llm_response
                )

                if isinstance(result, dict) and "map" in result:
                    success, error = self._check_map_renderability(result["map"])

                if success or only_text or "TimeoutError" in error:
                    error_message = "\n".join(errors) if len(errors) > 0 else error
                    self.update_chat_history(
                        user_input,
                        llm_response,
                        result,
                        success,
                        error_message,
                        only_text,
                    )
                    return result, success, error_message, only_text, llm_response

                errors.append(f"Attempt {attempt}: {error}")
                self._log_retry_attempt(attempt, error)

                if attempt < attempts_allowed:
                    llm_response, call_success = self.call_main_llm_retry(
                        user_input, llm_response, error, temperature=MAIN_LLM_RETRY_TEMPERATURE
                    )
                    if not call_success:
                        errors.append(f"Attempt {attempt + 1}: LLM call failed")
                        break

            error_message = self._format_error_message(attempt, errors)
            self.update_chat_history(
                user_input, llm_response, result, success, error_message, only_text
            )
        return None, False, error_message, only_text, llm_response

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

    def get_retry_messages(
        self, user_input: str, main_llm_response: str, error: str
    ) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            if interaction.user_prompt.strip():
                messages.append({"role": "user", "content": interaction.user_prompt})
            if interaction.assistant_response.strip():
                messages.append(
                    {"role": "assistant", "content": interaction.assistant_response}
                )
        # Add the user input and main LLM response
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": main_llm_response})
        # # Add the error message as part of the last assistant's response
        # if messages and messages[-1]["role"] == "assistant":
        #     messages[-1]["content"] += f"\n\nError: {error}"
        # else:
        #     # If the last message was not from the assistant, add a new assistant message with the error
        #     messages.append({"role": "assistant", "content": f"Error: {error}"})

        # Add the retry prompt as a new user message
        messages.append({"role": "user", "content": RETRY_PROMPT.format(error=error)})

        return messages

    @task(name="Call Main LLM Retry")
    def call_main_llm_retry(
        self,
        user_input: str,
        main_llm_response: str,
        error: str,
        temperature: float = MAIN_LLM_RETRY_TEMPERATURE,
    ) -> str:
        model = self.model
        self.logger.info(f"Retrying LLM call with model: {model}")
        messages = self.get_retry_messages(user_input, main_llm_response, error)
        client = self.clients[self.get_client_key(model)]
        response, call_success = client.call(
            model, messages, self.system_prompt, temperature
        )

        self.logger.info(f"LLM Response: {response}")
        return response, call_success

    @task(name="Summary LLM Call")
    def call_summary_llm(self, stream_placeholder):
        last_interaction = self.chat_history[-1] if self.chat_history else None

        if not last_interaction:
            self.logger.warning("No interactions in chat history for summary LLM call")
            return "No previous interaction available."
        # Additional check to ensure that large dataframes are not passed to the LLM
        summarized_evaluation = summarize_large_output(
            last_interaction.evaluation_result, self.max_rows, self.max_chars
        )
        user_prompt = SUMMARY_LLM_USER_PROMPT.format(
            question=last_interaction.user_prompt,
            response=last_interaction.assistant_response,
            evaluation=summarized_evaluation,
            success=last_interaction.code_success,
            error=last_interaction.error_message,
        )
        # Hardcoded model for summary LLM call
        model = SUMMARY_LLM
        messages = self.create_messages(user_prompt, model)
        self.logger.info(f"Summary LLM message sent to {model} : {messages}")
        full_response = ""
        client = self.clients["gpt"]
        # Stream the response
        system_prompt = SUMMARY_LLM_SYSTEM_PROMPT
        for chunk in client.stream_call(model, messages, system_prompt):
            full_response += chunk
            stream_placeholder.markdown(full_response + "▌")

        self.logger.info("Summary response from LLM:\n %s", full_response)
        return full_response

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

    def update_agent(self, GTFS, model, distance_unit, allow_viz):
        # Reset the agent if the GTFS feed changes
        if self.GTFS != GTFS:
            self.reset()
            self.evaluator.reset()
            self.GTFS = GTFS
        self.model = model
        self.distance_unit = distance_unit
        self.allow_viz = allow_viz

        self.logger.info(
            f"Updating LLMAgent with model: [red]{model}[/red], GTFS: [red]{GTFS}[/red], distance unit: [red]{distance_unit}[/red], and allow_viz: [red]{allow_viz}[/red]"
        )
        self.load_system_prompt(GTFS, distance_unit, allow_viz)

    @workflow(name="LLM Agent Workflow")
    def run_workflow(
        self, user_input: str, retry_code: bool = False, summarize: bool = True, task: str = None
    ):
        start_time = time.time()
        llm_response, call_success = self.call_main_llm(user_input)

        if not call_success:
            self.logger.error(f"LLM call failed: {llm_response}")
            # If call is not successful, LLM response is the error message
            return None, False, llm_response, True, None, None, None

        self.logger.info(f"LLM call success: {llm_response}")
        output, success, error, only_text, llm_response = self.evaluate_code_with_retry(
            user_input, llm_response, retry_code=retry_code
        )

        # New step: Validate evaluation results
        # validation_response = self.validate_evaluation(user_input, llm_response, result, success, error, only_text)
        # validation_response = None

        if success and not only_text and summarize:
            summary_response = self.call_summary_llm(st.empty())
        else:
            summary_response = None

        end_time = time.time()
        execution_time = end_time - start_time
        self.logger.info(f"Execution time: {execution_time:.2f} seconds")

        return {
            "task": task,
            "code_output": output,
            "eval_success": success,
            "error_message": error,
            "only_text": only_text,
            "main_response": llm_response,
            "summary_response": summary_response,
            # "validation_response": validation_response,
            "execution_time": execution_time,
        }

    @task(name="Validate Evaluation")
    def validate_evaluation(
        self,
        user_input: str,
        llm_response: str,
        result: Any,
        success: bool,
        error: str,
        only_text: bool,
    ):
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

        messages = self.create_messages(validation_prompt, self.model)
        client = self.clients["gpt"]
        validation_response, _ = client.call(SUMMARY_LLM, messages, self.system_prompt)

        self.logger.info(f"Validation response from LLM: {validation_response}")
        return validation_response
