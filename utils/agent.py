import streamlit as st
from groq import Groq
from openai import OpenAI
from anthropic import Anthropic
import logging
import os
from logging.handlers import RotatingFileHandler
from prompts.all_prompts import FINAL_LLM_SYSTEM_PROMPT

# Initialize OpenAI and Anthropic client
oai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
anth_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

RETRY_PROMPT = """While executing the code, I encountered the following error:
{error}
Please account for this error and adjust your code accordingly."""

LOG_FILE = "logs/llm_agent.log"


class LLMAgent:
    def __init__(self, evaluator, max_retry=3):
        self.evaluator = evaluator
        self.max_retry = max_retry
        self._clear_log_file(LOG_FILE)
        self.logger = self._setup_logger(LOG_FILE)
        self.logger.info(
            "LLM Agent initialized with {} retry attempts".format(max_retry)
        )
        self.last_response = None
        self.chat_history = None
        self.model = None
        self.result = None
        self.distance_units = "Meters"

    def _clear_log_file(self, log_file: str) -> None:
        """Clear the contents of the log file."""
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        with open(log_file, "w") as f:
            f.write("")  # This will empty the file

    def _setup_logger(self, log_file: str) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create file handler which logs even debug messages
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
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

    def call_llm(self, system_prompt, user_prompt, model):
        self.logger.info(
            f"Calling LLM with SYSTEM PROMPT:\n {system_prompt}\n USER PROMPT:\n {user_prompt}"
        )
        self.model = model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if model.startswith("gpt"):
            response = self.call_openai(model, messages)
        elif model.startswith("llama"):
            response = self.call_groq(model, messages)
        else:
            messages = [{"role": "user", "content": user_prompt}]
            response = self.call_anthropic(model, system_prompt, messages)
        self.last_response = response
        self.chat_history = [
            ("system", system_prompt),
            ("user", user_prompt),
            ("assistant", response),
        ]
        self.logger.info(f"Response from LLM: {response}")
        return response

    def evaluate(self, llm_response):
        result, success, error = self.evaluator.evaluate(llm_response)
        self.result = result
        return result, success, error

    def evaluate_with_retry(self, model, llm_response):
        retry = 0
        while retry < self.max_retry:
            result, success, error = self.evaluate(llm_response)
            if success:
                return result, success, error, llm_response
            retry += 1
            st.write(f"Something wasnt right, retrying: attempt {retry}")
            self.logger.info(
                "Evaluation failed with error: %s. \nRetrying attempt %s", error, retry
            )
            llm_response = self.call_llm_retry(model, error)
        return None, False, "Evaluation failed after max retries", llm_response

    def call_openai(self, model, messages):
        response = oai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content

    def call_groq(self, model, messages):
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content

    def call_anthropic(self, model, system_prompt, messages):
        response = anth_client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=4096,
        )
        return response.content[0].text

    def call_llm_retry(self, model, error):
        chat_history = self.chat_history
        # Extract the system and user prompts from the chat history
        self.model = model
        self.logger.info("Retrying LLM call with model: %s", model)
        self.logger.info("Chat history: %s", chat_history)
        messages = [{"role": chat[0], "content": chat[1]} for chat in chat_history]
        messages.append({"role": "user", "content": RETRY_PROMPT.format(error=error)})
        if model.startswith("gpt"):
            response = self.call_openai(model, messages)
        elif model.startswith("llama"):
            response = self.call_groq(model, messages)
        else:
            # Claude has a specified attribute for the system prompt
            messages = [
                {"role": chat[0], "content": chat[1]}
                for chat in chat_history
                if chat[0] != "system"
            ]
            messages.append(
                {"role": "user", "content": RETRY_PROMPT.format(error=error)}
            )
            system_prompt = chat_history[0][1]
            response = self.call_anthropic(model, system_prompt, messages)
        self.logger.info("LLM Response: %s", response)
        return response

    def call_final_llm(self):
        system_prompt = FINAL_LLM_SYSTEM_PROMPT
        user_prompt = """
        
        ## Question 
        {question}
        
        ## Answer 
        {response}
        
        ## Code Evaluation 
        {evaluation}"""
        model = "gpt-4o-mini"
        question = self.chat_history[1][1]
        response = self.last_response  # This accounts for retries too
        evaluation = self.result
        user_prompt = user_prompt.format(
            question=question, response=response, evaluation=evaluation
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = oai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        response = response.choices[0].message.content
        self.logger.info("Final response from LLM:\n %s", response)
        return response

    def reset(self):
        self.last_response = None
        self.chat_history = None
        self.model = None
        self.result = None
