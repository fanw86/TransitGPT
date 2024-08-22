import logging
from typing import Tuple, Generator
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

    def stream_call(self, model, messages) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except OpenAIError as e:
            self.logger.error(f"OpenAI API streaming call failed: {str(e)}")
            yield f"Error: OpenAI API streaming call failed - {str(e)}"

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
            )
            return response.content[0].text, True
        except AnthropicError as e:
            self.logger.error(f"Anthropic API call failed: {str(e)}")
            return f"Error: Anthropic API call failed - {str(e)}", False
