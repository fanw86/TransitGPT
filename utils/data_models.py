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
    only_text: bool = False


class ChatHistoryEntry(BaseModel):
    role: Literal["assistant"]  # Since this is always "assistant" in the given context
    summary_response: Optional[str] = None
    main_response: Optional[str] = None
    code_output: Optional[Any] = None
    eval_success: bool = False
    error_message: Optional[str] = None
    only_text: bool = False
    is_cancelled: bool = False


class FeedbackEntry(BaseModel):
    question: str
    main_response: Optional[str]
    code_eval_success: bool
    code_eval_result: Optional[str] = None
    GTFS: str
    llm_model: str
    # system_prompt: str
    summary_response: Optional[str] = None
    figure: Optional[str] = None
    user_rating: Optional[int] = None
    user_comment: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=get_current_time)
    user_name: Optional[str]
    user_email: Optional[str]
    only_text: bool = False
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
