from uuid import UUID, uuid4

from pydantic import BaseModel
from typing import Any, Optional, List, Dict

from typing import Any, Optional, List, Union
import json

class TextContent(BaseModel):
    text: str
    type: str = "text"

class Usage(BaseModel):
    raw_prompt_tokens: int = 0
    prompt_tokens: int
    completion_tokens: int = 0
    total_tokens: int
    reasoning_tokens: int = 0

    class Config:
        extra = "allow"

    class CompletionTokensDetails(BaseModel):
        reasoning_tokens: int = 0
    class PromptTokensDetails(BaseModel):
        cached_tokens: int = 0

    completion_tokens_details: Optional[CompletionTokensDetails] = None
    prompt_tokens_details: Optional[PromptTokensDetails] = None

    def model_post_init(self, __context):
        # 如果 completion_tokens_details 存在且 reasoning_tokens 没有赋值，则自动赋值
        if self.completion_tokens_details and not self.reasoning_tokens:
            self.reasoning_tokens = self.completion_tokens_details.reasoning_tokens

class FunctionCall(BaseModel):
    name: Optional[str] = None
    arguments: str

    class Config:
        extra = "allow" # 允许接收额外的字段,这样可以兼容API返回的其他未定义字段

class ToolCall(BaseModel):
    id: Optional[str] = None
    index: Optional[int] = 0
    type: str = "function"
    function: FunctionCall

    class Config:
        extra = "allow" # 允许接收额外的字段,这样可以兼容API返回的其他未定义字段

class Message(BaseModel):
    role: Optional[str] = None
    content: Optional[Union[str, List[Union[TextContent]]]] = ""
    reasoning_content: Optional[Union[str, List[Union[TextContent]]]] = None
    refusal: Optional[str] = None
    reasoning: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    agent_name: Optional[str] = None
    index_id: Optional[int] = None

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False)

    def model_dump_for_chat(self) -> dict:
        """Return a dictionary representation of the message without index_id"""
        data = self.model_dump()
        if "index_id" in data:
            del data["index_id"]
        if "reasoning_details" in data:
            del data["reasoning_details"]
        return data

    def is_content_empty(self) -> bool:
        """Check if the message content and reasoning content are empty (empty or only whitespace)"""
        if self.content is None and self.reasoning_content is None:
            return True
        if isinstance(self.content, str) and isinstance(self.reasoning_content, str):
            content_stripped = str(self.content).strip() if self.content else ""
            reasoning_stripped = str(self.reasoning_content).strip() if self.reasoning_content else ""
            if content_stripped == "" and reasoning_stripped == "":
                return True
        return False

    class Config:
        extra = "allow"  # 允许接收额外的字段,这样可以兼容API返回的其他未定义字段

class Choice(BaseModel):
    logprobs: Optional[Any] = None
    finish_reason: Optional[str] = None
    native_finish_reason: Optional[str] = None
    index: Optional[int] = 0
    message: Optional[Message] = None
    content_filter_results: Optional[dict] = None
    delta: Optional[Message] = None

    class Config:
        extra = "allow"


class ToolChoice(BaseModel):
    type: str
    function: Optional[dict] = None


class Response(BaseModel):
    id: str
    provider: Optional[str] = "openai"
    model: str
    object: Optional[str] = None
    created: Optional[int] = None
    choices: Optional[List[Choice]] = None
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None
    prompt_filter_results: Optional[List[dict]] = None

    class Config:
        extra = "allow"