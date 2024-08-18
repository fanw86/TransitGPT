import logging
from typing import Tuple
from openai import OpenAI, OpenAIError
from groq import Groq, GroqError
from anthropic import Anthropic, AnthropicError
import streamlit as st
from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        pass


class OpenAIClient(LLMClient):
    def __init__(self):
        self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.logger = logging.getLogger(__name__)

    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content, True
        except OpenAIError as e:
            self.logger.error(f"OpenAI API call failed: {str(e)}")
            return f"Error: OpenAI API call failed - {str(e)}", False


class GroqClient(LLMClient):
    def __init__(self):
        self.client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        self.logger = logging.getLogger(__name__)

    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool]:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content, True
        except GroqError as e:
            self.logger.error(f"Groq API call failed: {str(e)}")
            return f"Error: Groq API call failed - {str(e)}", False


class AnthropicClient(LLMClient):
    def __init__(self):
        self.client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.logger = logging.getLogger(__name__)

    def call(self, model, messages, system_prompt) -> Tuple[str, bool]:
        try:
            response = self.client.beta.prompt_caching.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                max_tokens=4096,
            )
            return response.content[0].text, True
        except AnthropicError as e:
            self.logger.error(f"Anthropic API call failed: {str(e)}")
            return f"Error: Anthropic API call failed - {str(e)}", False
