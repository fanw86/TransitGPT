from typing import Tuple, Generator, Union
from openai import OpenAI, OpenAIError
from groq import Groq, GroqError
from anthropic import Anthropic, AnthropicError
import streamlit as st
from abc import ABC, abstractmethod
from utils.constants import MAIN_LLM_TEMPERATURE, SUMMARY_LLM_TEMPERATURE


class LLMClient(ABC):
    @abstractmethod
    def call(self, model, messages, system_prompt=None) -> Tuple[str, bool, dict]:
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

    def call(self, model, messages, system_prompt=None, temperature=MAIN_LLM_TEMPERATURE, max_tokens=None, **kwargs) -> Tuple[str, bool, dict]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        role = kwargs.get('role', 'Main LLM' if temperature == MAIN_LLM_TEMPERATURE else 'Summary LLM' if temperature == SUMMARY_LLM_TEMPERATURE else 'Moderation LLM')
        store = role == "Main LLM"
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                store=store,
                metadata={
                    'role': role,
                    'source': "TransitGPT"
                }
            )
            self.logger.info(f"Raw Response from OpenAI: {response}")
            self.last_error = None
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            self.logger.info(f"Usage from OpenAI: {usage}")
            return response.choices[0].message.content, True, usage
        except OpenAIError as e:
            error_message = f"OpenAI API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def stream_call(
        self, model, messages, system_prompt=None, temperature=SUMMARY_LLM_TEMPERATURE
    ) -> Generator[Union[str, dict], None, None]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                try:        
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                except Exception as e:
                    pass  # for the usage data
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

    def call(self, model, messages, system_prompt=None, temperature=MAIN_LLM_TEMPERATURE, **kwargs) -> Tuple[str, bool, dict]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            self.logger.info(f"Raw Response from Groq: {response}")
            self.last_error = None
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            self.logger.info(f"Usage from Groq: {usage}")
            return response.choices[0].message.content, True, usage
        except GroqError as e:
            error_message = f"Groq API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class AnthropicClient(LLMClient):
    def __init__(self):
        self.client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt, temperature=MAIN_LLM_TEMPERATURE, **kwargs) -> Tuple[str, bool, dict]:
        cache_system_prompt = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        try:
            response = self.client.messages.create(
                model=model,
                system=cache_system_prompt,
                messages=messages,
                max_tokens=4096,
                temperature=temperature,
            )
            self.logger.info(f"Raw Response from Anthropic: {response}")
            self.last_error = None
            input_tokens = response.usage.input_tokens + response.usage.cache_creation_input_tokens + response.usage.cache_read_input_tokens
            output_tokens = response.usage.output_tokens
            usage = {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
            self.logger.info(f"Usage from Anthropic: {usage}")
            return response.content[0].text, True, usage
        except AnthropicError as e:
            error_message = f"Anthropic API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class GeminiClient(LLMClient):
    def __init__(self):
        self.client = OpenAI(
            api_key=st.secrets["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt=None, temperature=MAIN_LLM_TEMPERATURE, **kwargs) -> Tuple[str, bool, dict]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            self.logger.info(f"Raw Response from Gemini: {response}")
            self.last_error = None
            usage = {
                "prompt_tokens": response.usage.promptTokens,
                "completion_tokens": response.usage.completionTokens,
                "total_tokens": response.usage.totalTokens
            }
            self.logger.info(f"Usage from Gemini: {usage}")
            return response.choices[0].message.content, True, usage
        except OpenAIError as e:
            error_message = f"Gemini API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class OpenRouterClient(LLMClient):
    def __init__(self):
        self.client = OpenAI(
            api_key=st.secrets.general.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        self.logger = None
        self.last_error = None

    def set_logger(self, logger):
        self.logger = logger

    def call(self, model, messages, system_prompt=None, temperature=MAIN_LLM_TEMPERATURE, max_tokens=None, **kwargs) -> Tuple[str, bool, dict]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.logger.info(f"Raw Response from OpenRouter: {response}")
            self.last_error = None
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            self.logger.info(f"Usage from OpenRouter: {usage}")
            return response.choices[0].message.content, True, usage
        except OpenAIError as e:
            error_message = f"OpenRouter API call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            return error_message, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def stream_call(
        self, model, messages, system_prompt=None, temperature=SUMMARY_LLM_TEMPERATURE
    ) -> Generator[Union[str, dict], None, None]:
        messages.insert(0, {"role": "system", "content": system_prompt})
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
                stream_options={"include_usage": True}
            )
            for chunk in stream:
                try:        
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                except Exception as e:
                    pass  # for the usage data
        except OpenAIError as e:
            error_message = f"OpenRouter API streaming call failed: {str(e)}"
            self.logger.error(error_message)
            self.last_error = error_message
            yield error_message
