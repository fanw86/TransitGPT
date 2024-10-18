import sys
import os
import pytest

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gtfs_agent.llm_client import OpenAIClient, GroqClient, AnthropicClient

# Note: These tests will require mocking the API calls


@pytest.fixture
def mock_openai_client(mocker):
    client = OpenAIClient()
    mocker.patch.object(client.client.chat.completions, "create")
    return client


@pytest.fixture
def mock_groq_client(mocker):
    client = GroqClient()
    mocker.patch.object(client.client.chat.completions, "create")
    return client


@pytest.fixture
def mock_anthropic_client(mocker):
    client = AnthropicClient()
    mocker.patch.object(client.client.beta.prompt_caching.messages, "create")
    return client


def test_openai_client_call(mock_openai_client):
    mock_openai_client.client.chat.completions.create.return_value.choices[
        0
    ].message.content = "Test response"
    response, success = mock_openai_client.call(
        "gpt-4", [{"role": "user", "content": "Test"}]
    )
    assert response == "Test response"
    assert success is True


def test_groq_client_call(mock_groq_client):
    mock_groq_client.client.chat.completions.create.return_value.choices[
        0
    ].message.content = "Test response"
    response, success = mock_groq_client.call(
        "llama2-70b-4096", [{"role": "user", "content": "Test"}]
    )
    assert response == "Test response"
    assert success is True


def test_anthropic_client_call(mock_anthropic_client):
    mock_anthropic_client.client.beta.prompt_caching.messages.create.return_value.content[
        0
    ].text = "Test response"
    response, success = mock_anthropic_client.call(
        "claude-3-opus-20240229", [{"role": "user", "content": "Test"}], "System prompt"
    )
    assert response == "Test response"
    assert success is True


# Add more tests for error cases and edge cases
