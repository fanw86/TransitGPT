import sys
import os
import pytest

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_models import ChatInteraction, ChatHistoryEntry, FeedbackEntry
from datetime import datetime

def test_chat_interaction():
    interaction = ChatInteraction(
        system_prompt="System prompt",
        user_prompt="User prompt",
        assistant_response="Assistant response"
    )
    assert interaction.system_prompt == "System prompt"
    assert interaction.user_prompt == "User prompt"
    assert interaction.assistant_response == "Assistant response"
    assert interaction.evaluation_result is None
    assert interaction.code_success is None
    assert interaction.error_message is None

def test_chat_history_entry():
    entry = ChatHistoryEntry(
        role="assistant",
        final_response="Final response",
        code_response="Code response",
        code_output="Code output",
        eval_success=True
    )
    assert entry.role == "assistant"
    assert entry.final_response == "Final response"
    assert entry.code_response == "Code response"
    assert entry.code_output == "Code output"
    assert entry.eval_success is True
    assert entry.error_message is None
    assert entry.only_text is False
    assert entry.is_cancelled is False

def test_feedback_entry():
    entry = FeedbackEntry(
        question="Test question",
        response="Test response",
        code_eval_success=True,
        GTFS="Test GTFS",
        llm_model="gpt-4",
        user_rating=5
    )
    assert isinstance(entry.timestamp, datetime)
    assert entry.question == "Test question"
    assert entry.response == "Test response"
    assert entry.code_eval_success is True
    assert entry.GTFS == "Test GTFS"
    assert entry.llm_model == "gpt-4"
    assert entry.user_rating == 5
    assert entry.user_comment is None
    assert entry.code_eval_result is None
    assert entry.figure is None
    assert entry.final_response is None

# Add more tests for edge cases and validation