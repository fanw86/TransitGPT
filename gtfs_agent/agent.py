import streamlit as st
import time
from prompts.all_prompts import (
    SUMMARY_LLM_SYSTEM_PROMPT,
    SUMMARY_LLM_USER_PROMPT,
    RETRY_PROMPT,
    MAIN_LLM_USER_PROMPT,
    MODERATION_LLM_SYSTEM_PROMPT,
    MODERATION_LLM_BLOCK_RESPONSE,
)
from prompts.generate_prompt import generate_dynamic_few_shot
from utils.constants import (
    LOG_FILE,
    SUMMARY_LLM,
    SUMMARY_LLM_TEMPERATURE,
    MAIN_LLM_RETRY_TEMPERATURE,
    ENABLE_TRACING,
    MODERATION_LLM,
    MODERATION_LLM_TEMPERATURE,
    MODERATION_LLM_MAX_TOKENS,
)
from typing import List, Dict, Any, Tuple
from utils.helper import summarize_large_output, combine_token_usage
from gtfs_agent.llm_client import OpenAIClient, GroqClient, AnthropicClient, GeminiClient, OpenRouterClient
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
            "openrouter": OpenRouterClient(),
        }

        # Set the logger for each client
        for client in self.clients.values():
            client.set_logger(self.logger)

        self.result = None
        self.last_response = None
        self.chat_history = []
        self.allow_viz = allow_viz
        self.load_system_prompt(self.GTFS, self.distance_unit, self.allow_viz)
        if ENABLE_TRACING and "TRACELOOP_API_KEY" in st.secrets:
            Traceloop.init(disable_batch=True, api_key=st.secrets["TRACELOOP_API_KEY"])
        self.status = None  # Initialize status

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
        # Always use OpenRouter client for all models
        return "openrouter"

    def create_messages(self, user_prompt: str, model: str) -> List[Dict[str, str]]:
        messages = []
        for interaction in self.chat_history:
            if interaction.user_prompt.strip():
                messages.append({"role": "user", "content": interaction.user_prompt})
            else:
                self.logger.warning(
                    f"Empty user prompt found at index {interaction}: {interaction.user_prompt!r}"
                )
                messages.append({"role": "user", "content": "..."})
            
            if interaction.assistant_response.strip():
                # Format the full response with evaluation details
                response_parts = [interaction.assistant_response]
                
                if interaction.evaluation_result is not None:
                    eval_summary = summarize_large_output(
                        interaction.evaluation_result, 
                        self.max_rows, 
                        self.max_chars
                    )
                    response_parts.extend([
                        "\n\nEvaluation Output:",
                        f"Success: {interaction.code_success}",
                        f"Result: {eval_summary}"
                    ])
                    
                    if interaction.error_message and not interaction.code_success:
                        response_parts.append(f"Error: {interaction.error_message}")
                
                messages.append({
                    "role": "assistant", 
                    "content": "\n".join(response_parts)
                })
        
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
    def call_main_llm(self, user_input: str, method: str = "tfidf") -> Tuple[str, bool, str]:
        model = self.model
        self.logger.info(f"Calling Main LLM with model: {model}")
        few_shot_examples = generate_dynamic_few_shot(user_input, method, self.allow_viz)
        user_prompt = MAIN_LLM_USER_PROMPT.format(
            user_query=user_input, examples=few_shot_examples
        )
        messages = self.create_messages(user_prompt, model)
        client = self.clients[self.get_client_key(model)]
        self.logger.info(f"Messages sent to {model}: {messages}\n")
        response, call_success, usage = client.call(
            model, messages, self.system_prompt, role="Main LLM"
        )
        return response, call_success, usage

    @task(name="Call Moderation LLM")
    def call_moderation_llm(self, user_input: str) -> Tuple[str, bool, str]:
        if self.status:
            self.status.update(label="Moderating query...", state="running")
        model = MODERATION_LLM
        self.logger.info(f"Calling Moderation LLM with model: {model}")
        system_prompt = MODERATION_LLM_SYSTEM_PROMPT
        messages = self.create_messages(user_input, model)
        client = self.clients[self.get_client_key(model)]
        response, call_success, usage = client.call(
            model,
            messages,
            system_prompt,
            max_tokens=MODERATION_LLM_MAX_TOKENS,
            temperature=MODERATION_LLM_TEMPERATURE,
        )
        return response, call_success, usage

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
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        attempts_allowed = self.max_retry if retry_code else 1

        if self.status:
            self.status.update(label="Evaluating code...", state="running")
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
                return (
                    result,
                    success,
                    error_message,
                    only_text,
                    llm_response,
                    total_usage,
                )

            errors.append(f"Attempt {attempt}: {error}")
            self._log_retry_attempt(attempt, error)

            if attempt < attempts_allowed:
                llm_response, call_success, usage = self.call_main_llm_retry(
                    user_input,
                    llm_response,
                    error,
                    temperature=MAIN_LLM_RETRY_TEMPERATURE,
                )
                # Add usage from retry attempt
                for key in total_usage:
                    total_usage[key] += usage.get(key, 0)

                if not call_success:
                    errors.append(f"Attempt {attempt + 1}: LLM call failed")
                    break

        error_message = self._format_error_message(attempt, errors)
        self.update_chat_history(
            user_input, llm_response, result, success, error_message, only_text
        )
        return None, False, error_message, only_text, llm_response, total_usage

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
        messages.append({"role": "user", "content": RETRY_PROMPT.format(error=error)})
        # # Add the error message as part of the last assistant's response
        # if messages and messages[-1]["role"] == "assistant":
        #     messages[-1]["content"] += f"\n\nError: {error}"
        # else:
        #     # If the last message was not from the assistant, add a new assistant message with the error
        #     messages.append({"role": "assistant", "content": f"Error: {error}"})

        # Add the retry prompt as a new user message

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
        response, call_success, usage = client.call(
            model, messages, self.system_prompt, temperature, role="Main LLM Retry"
        )

        self.logger.info(f"LLM Response: {response}")
        return response, call_success, usage

    @task(name="Call Summary LLM")
    def call_summary_llm(self):
        last_interaction = self.chat_history[-1] if self.chat_history else None

        if not last_interaction:
            self.logger.warning("No interactions in chat history for summary LLM call")
            return "No previous interaction available."
            
        summarized_evaluation = summarize_large_output(
            last_interaction.evaluation_result, self.max_rows, self.max_chars
        )
        error_message = "" if last_interaction.code_success else last_interaction.error_message
        user_prompt = SUMMARY_LLM_USER_PROMPT.format(
            question=last_interaction.user_prompt,
            response=last_interaction.assistant_response,
            evaluation=summarized_evaluation,
            success=last_interaction.code_success,
            error=error_message,
        )
        
        model = SUMMARY_LLM
        messages = self.create_messages(user_prompt, model)
        self.logger.info(f"Summary LLM message sent to {model} : {messages}")
        full_response = ""
        client_key = self.get_client_key(model)
        client = self.clients[client_key]
        
        if self.status:
            self.status.update(label="Summarizing response...", state="complete")
        
        stream_placeholder = st.empty()
        # Use the actual stream_placeholder here, but don't include it in task tracking
        for chunk in client.stream_call(
            model, messages, SUMMARY_LLM_SYSTEM_PROMPT, temperature=SUMMARY_LLM_TEMPERATURE
        ):
            full_response += chunk
            stream_placeholder.markdown(full_response + "▌")

        self.logger.info("Summary response from LLM:\n %s", full_response)
        return full_response

    def reset(self):
        self.last_response = None
        self.chat_history = []
        self.result = None
        self.status = None
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

    def set_status(self, status: st.status):
        self.status = status

    @workflow(name="LLM Agent Workflow")
    def run_workflow(
        self,
        user_input: str,
        retry_code: bool = False,
        summarize: bool = True,
        task: str = None,
        similarity_method: str = "sentence_transformer",
    ):
        with st.status("Processing your request...", state="running") as status:
            self.set_status(status)  # Set the status at the beginning of the workflow
            start_time = time.time()
            if not self.chat_history:
                moderation_response, call_success, moderation_usage = self.call_moderation_llm(user_input)
                if "BLOCK" in moderation_response:
                    return {
                        "task": task,
                        "code_output": None,
                        "eval_success": False,
                        "error_message": "Your query has been blocked due to inappropriate content. Please try another query.",
                        "only_text": True,
                        "main_response": MODERATION_LLM_BLOCK_RESPONSE,
                        "summary_response": None,
                        "token_usage": moderation_usage,
                        "execution_time": 0,
                    }
            else:
                moderation_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            if self.status:
                self.status.update(label="Calling Main LLM...", state="running")
            llm_response, call_success, main_llm_usage = self.call_main_llm(user_input, similarity_method)

            if not call_success:
                self.logger.error(f"LLM call failed: {llm_response}")
                # If call is not successful, LLM response is the error message
                end_time = time.time()
                execution_time = end_time - start_time
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

            # Evaluate the code with retry
            self.logger.info(f"LLM call success: {llm_response}")
            output, success, error, only_text, llm_response, retry_usage = (
                self.evaluate_code_with_retry(
                    user_input, llm_response, retry_code=retry_code
                )
            )
            # Compute the total usage by adding the usage from the first attempt
            total_usage = combine_token_usage(
                [moderation_usage, main_llm_usage, retry_usage]
            )

        # New step: Validate evaluation results
        # validation_response = self.validate_evaluation(user_input, llm_response, result, success, error, only_text)
        # validation_response = None

        if success and not only_text and summarize:
            summary_response = self.call_summary_llm()
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
            "token_usage": total_usage,
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
        client_key = self.get_client_key(SUMMARY_LLM)
        client = self.clients[client_key]
        validation_response, _ = client.call(SUMMARY_LLM, messages, self.system_prompt)

        self.logger.info(f"Validation response from LLM: {validation_response}")
        return validation_response
