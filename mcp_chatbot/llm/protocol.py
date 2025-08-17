from uuid import UUID, uuid4

from pydantic import BaseModel
from typing import Any, Optional, List, Dict

from typing import Any, Optional, List, Union
import json

class TextContent(BaseModel):
    text: str
    type: str = "text"

class ImageContent(BaseModel):
    type: str = "image"
    class Source(BaseModel):
        type: str = "base64"
        media_type: str = "image/jpeg"
        data: str
    source: Source

# Anthropic 对 Image 的定义与 OpenAI 不同，OpenRouter 做了适配，但是 aws 没有适配，目前没使用
class AnthropicImage(BaseModel):
    class Source(BaseModel):
        type: str = "base64"
        media_type: str = "image/jpeg"
        data: str
        url: str = ""

    type: str = "image"
    source: Source

class GeminiImage(BaseModel):
    class ImageUrl(BaseModel):
        url: str
    type: str = "image_url"
    image_url: ImageUrl

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
    content: Optional[Union[str, List[Union[TextContent, ImageContent, AnthropicImage, GeminiImage]]]] = ""
    reasoning_content: Optional[Union[str, List[Union[TextContent, ImageContent]]]] = None
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

class BaseReportPayload(BaseModel):
    conversation_id: str
    question_id: str
    request_id: str
    card_type: str
    status: int = 1
    block_id: str
    card_id: str
    content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.dict(exclude_none=True)



class TaskItem(BaseModel):
    id: str
    title: str
    block_id: str
    status: str  # e.g., "todo", "in_progress", "done"
    startedAt: Optional[int] = None  # 时间戳，单位：毫秒

class ToolUsePayload(BaseReportPayload):
    data: Optional[Dict[str, Any]] = None

class ContextClarifyPayload(BaseReportPayload):
    context_fields: Optional[List[Dict[str, Any]]] = None

class TasksPayload(BaseReportPayload):
    tasks: Optional[List[TaskItem]] = None

class ToolResult(BaseModel):
    query: str
    num_results: int
    tool: str
    payload: Optional[Dict[str, Any]] = None
    result: str



def merge_usage(base_usage: Usage, new_usage: Usage) -> Usage:
    base_usage.prompt_tokens += new_usage.prompt_tokens
    base_usage.completion_tokens += new_usage.completion_tokens
    base_usage.total_tokens += new_usage.total_tokens
    base_usage.reasoning_tokens += new_usage.reasoning_tokens
    
    if not base_usage.prompt_tokens_details:
        base_usage.prompt_tokens_details = Usage.PromptTokensDetails(cached_tokens=0)
    if not new_usage.prompt_tokens_details:
        new_usage.prompt_tokens_details = Usage.PromptTokensDetails(cached_tokens=0)
    
    base_usage.prompt_tokens_details.cached_tokens += new_usage.prompt_tokens_details.cached_tokens
    return base_usage

def merge_function_call(base_function_call: FunctionCall, new_function_call: FunctionCall) -> FunctionCall:
    if base_function_call.name is None:
        base_function_call.name = new_function_call.name
    elif new_function_call.name is not None:
        base_function_call.name += new_function_call.name
    
    if base_function_call.arguments is None:
        base_function_call.arguments = new_function_call.arguments
    elif new_function_call.arguments is not None:
        base_function_call.arguments += new_function_call.arguments
    return base_function_call

def merge_tool_call(base_tool_call: ToolCall, new_tool_call: ToolCall) -> ToolCall:
    base_tool_call.function = merge_function_call(base_tool_call.function, new_tool_call.function)
    return base_tool_call

def merge_tool_calls(base_tool_calls: List[ToolCall], new_tool_calls: List[ToolCall]) -> List[ToolCall]:
    if not base_tool_calls:
        return new_tool_calls
    if not new_tool_calls:
        return base_tool_calls
    
    merged_tool_calls = base_tool_calls[:-1]
    base_last_tool_call = base_tool_calls[-1]
    
    for new_tool_call in new_tool_calls:
        if new_tool_call.id and base_last_tool_call.id != new_tool_call.id:
            # 新的 tool call
            merged_tool_calls.append(base_last_tool_call)
            base_last_tool_call = new_tool_call
        else:
            # 在原来的 last tool call 基础上追加
            base_last_tool_call = merge_tool_call(base_last_tool_call, new_tool_call)
    merged_tool_calls.append(base_last_tool_call)
    return merged_tool_calls

def merge_message(base_message: Message, new_message: Message) -> Message:
    if isinstance(base_message.content, str) and isinstance(new_message.content, str):
        base_message.content += new_message.content
    
    if isinstance(new_message.reasoning, str):
        if isinstance(base_message.reasoning, str): 
            base_message.reasoning += new_message.reasoning
        if base_message.reasoning is None:
            base_message.reasoning = new_message.reasoning

    if new_message.tool_calls is None:
        new_message.tool_calls = []
    
    # 如果为空 直接使用 new message，否则按照index merge
    if base_message.tool_calls is None or len(base_message.tool_calls) == 0:
        base_message.tool_calls = new_message.tool_calls
    else:
        tool_calls = base_message.tool_calls[:-1]
        base_last_tool_call = base_message.tool_calls[-1]
        for new_tool_call in new_message.tool_calls:
            if new_tool_call.id and base_last_tool_call.id != new_tool_call.id:
                # 新的 tool call
                tool_calls.append(base_last_tool_call)
                base_last_tool_call = new_tool_call
            else:
                # 在原来的 last tool call 基础上追加
                base_last_tool_call = merge_tool_call(base_last_tool_call, new_tool_call)
        tool_calls.append(base_last_tool_call)
        base_message.tool_calls = tool_calls
    return base_message

def merge_choice(base_choice: Choice, new_choice: Choice) -> Choice:
    if isinstance(base_choice.finish_reason, str) and isinstance(new_choice.finish_reason, str):
        base_choice.finish_reason += new_choice.finish_reason
    if base_choice.message is not None and new_choice.message is not None:
        base_choice.message = merge_message(base_choice.message, new_choice.message)
    elif new_choice.message is not None:
        base_choice.message = new_choice.message
    if base_choice.delta is not None and new_choice.delta is not None:
        base_choice.delta = merge_message(base_choice.delta, new_choice.delta)
    elif new_choice.delta is not None:
        base_choice.delta = new_choice.delta
    return base_choice

def merge_response(base_response: Response, new_response: Response) -> Response:
    """
    合并两个 Response 对象
    """
    if base_response.choices and new_response.choices:
        choices = []
        for i in range(min(len(base_response.choices), len(new_response.choices))):
            choices.append(merge_choice(base_response.choices[i], new_response.choices[i]))
        base_response.choices = choices
    if base_response.usage is not None and new_response.usage is not None:
        base_response.usage = merge_usage(base_response.usage, new_response.usage)
    elif new_response.usage is not None:
        base_response.usage = new_response.usage
    return base_response

class SkyworkResData(BaseModel):
    status: Optional[int] = None
    reply: Optional[str] = None

class SkyworkResponse(BaseModel):
    code: Optional[int] = None
    code_msg: Optional[str] = None
    trace_id: Optional[str] = None
    resp_data: Optional[SkyworkResData] = None
    reasoning: Optional[str] = None
    finish_reason: Optional[int] = None
    all_response: Optional[int] = None
    usage: Optional[Usage] = None

# NOTE(Diamond): 为适配 leili 接口返回的数据，将Response转为 OpenAI 的通用格式
def convert_to_openai_response(skywork_response: SkyworkResponse) -> Response:
    usage = None
    if skywork_response and skywork_response.usage:
        usage = Usage(prompt_tokens=skywork_response.usage.prompt_tokens, completion_tokens=skywork_response.usage.completion_tokens, total_tokens=skywork_response.usage.total_tokens)
    return Response(id=skywork_response.trace_id, model="skywork", usage=usage,
                    choices=[Choice(message=Message(role="assistant", content=skywork_response.resp_data.reply))])
