from typing import Tuple, Generator
from openai import OpenAI, OpenAIError
from groq import Groq, GroqError
from anthropic import Anthropic, AnthropicError
import streamlit as st
from abc import ABC, abstractmethod
from utils.constants import MAIN_LLM_TEMPERATURE, SUMMARY_LLM_TEMPERATURE

class LLMClient(ABC):
    @abstractmethod
    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        pass

    @abstractmethod
    def set_logger(self, logger):
        pass


class OpenAIClient(LLMClient):
    def __init__(self):
        self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=MAIN_LLM_TEMPERATURE,
            )
            self.logger.info(f"Raw Response from OpenAI: {response}")
            self.last_error = None
            return response.choices[0].message.content, True
        except OpenAIError as e:
            error_message = f"OpenAI API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False

    def stream_call(self, model, messages) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=SUMMARY_LLM_TEMPERATURE,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except OpenAIError as e:
            error_message = f"OpenAI API streaming call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            yield error_message


class GroqClient(LLMClient):
    def __init__(self):
        self.client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=MAIN_LLM_TEMPERATURE,
            )
            self.logger.info(f"Raw Response from Groq: {response}")
            self.last_error = None
            return response.choices[0].message.content, True
        except GroqError as e:
            error_message = f"Groq API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False


class AnthropicClient(LLMClient):
    def __init__(self):
        self.client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt) -> Tuple[str, bool]:
        cache_system_prompt = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        try:
            response = self.client.beta.prompt_caching.messages.create(
                model=model,
                system=cache_system_prompt,
                messages=messages,
                max_tokens=4096,
                temperature=MAIN_LLM_TEMPERATURE,
            )
            self.logger.info(f"Raw Response from Anthropic: {response}")
            self.last_error = None
            return response.content[0].text, True
        except AnthropicError as e:
            error_message = f"Anthropic API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False
