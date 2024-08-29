
from pydantic import BaseModel, Field
from typing import Any, Optional, Literal
from datetime import datetime
from utils.helper import get_current_time


class ChatInteraction(BaseModel):
    system_prompt: str
    user_prompt: str
    assistant_response: str
    evaluation_result: Optional[Any] = None
    code_success: Optional[bool] = None
    error_message: Optional[str] = None


class ChatHistoryEntry(BaseModel):
    role: Literal["assistant"]  # Since this is always "assistant" in the given context
    final_response: Optional[str] = None
    code_response: Optional[str] = None
    code_output: Optional[Any] = None
    eval_success: bool = False
    error_message: Optional[str] = None
    only_text: bool = False


class FeedbackEntry(BaseModel):
    timestamp: datetime = Field(default_factory=get_current_time)
    question: str
    response: str
    code_eval_success: bool
    GTFS: Optional[str] = None
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    user_rating: Optional[int] = None
    user_comment: Optional[str] = None
    code_eval_result: Optional[str] = None
    figure: Optional[str] = None
    final_response : Optional[str]