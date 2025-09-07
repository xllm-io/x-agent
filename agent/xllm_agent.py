import asyncio
from typing import List, Union, Awaitable, Dict, Callable, Optional, TypeVar
import json
from agent.agent import AgentType
from pydantic import BaseModel, Field
from loguru import logger

from agent.llm import LLM
from agent.protocol import Message

AgentType = TypeVar('Agent', bound='Agent')

class ChatMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (user, tool or agent)")
    content: str = Field(..., description="The content of the message")

class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Field that identify each session")
    request_id: str = Field(None, description="Field that identify each request")
    user_id: str = Field("", description="Field that identify each user")
    action: str = Field(..., description="The behavior you want the agent to perform")
    query: str = Field(..., description="User input content")
    language: str = Field("zh-cn", description="Field that support multi-language")
    chat_history: List[ChatMessage] = Field(None, description="enabled team members")

class HeartbeatContext:
    def __init__(self, heartbeat_interval: int = 60, report_func: Optional[Callable] = None):
        self.heartbeat_interval = heartbeat_interval
        self.report_func = report_func
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def _heartbeat_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.report_func:
                    await self.report_func()
                logger.debug("Heartbeat sent")
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
            
            try:
                # 使用 wait_for 和 Event().wait() 来实现可中断的等待
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.heartbeat_interval)
            except asyncio.TimeoutError:
                # 超时说明需要发送下一次心跳
                continue
            else:
                # 如果 stop_event 被设置，立即退出
                break

    async def __aenter__(self):
        self._task = asyncio.create_task(self._heartbeat_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._task:
            await self._task 
    

class CallStack:
    def __init__(self, call_stack: List[str], funtion_call_name: str):
        self._call_stack = call_stack
        self._funtion_call_name = funtion_call_name
    
    def __enter__(self):
        self._call_stack.append(self._funtion_call_name)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._call_stack.pop()
    
    async def __aenter__(self):
        self._call_stack.append(self._funtion_call_name)
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        self._call_stack.pop()
    

class AgentStack:
    def __init__(self, stack: List[AgentType], agent: AgentType, call_stack: List[str]):
        self._stack = stack
        self._agent = agent
        self._call_stack = call_stack

    def __enter__(self):
        self._stack.append(self._agent)
        self._call_stack.append(f"@{self._agent.agent_name}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stack.pop()
        self._call_stack.pop()

    async def __aenter__(self):
        self._stack.append(self._agent)
        self._call_stack.append(f"@{self._agent.agent_name}")
        self._cancel_scope = asyncio.get_running_loop().create_future()
        return self


class Agent:
    def __init__(self, available_tools: List[str]):
        self.agent_name = "Agent"
        self.available_tools = available_tools
        self._history = []
        self._llm = LLM(model_name="gpt-4o-mini", model_params={})

    async def run(self, input: str, using_stream: bool):
        logger.info(f"Agent {self.agent_name} run, input: {input}, using_stream: {using_stream}")
        await self.save_history(Message(role="user", content=input))
        # await self._tool_registry.initialize()
        response = await self._llm.chat(self._history, using_stream=using_stream)
        if response.choices is None or len(response.choices) == 0:
            logger.error(f"Agent {self.agent_name} LLM返回空响应: {json.dumps(response.model_dump(), indent=2, ensure_ascii=False)}")
            choice_message = Message(role="assistant", content=f"发生错误: LLM返回空响应")
            await self.save_history(choice_message)
            raise Exception("LLM返回空响应")
        choice = response.choices[0]
        choice_message = choice.message
        await self.save_history(choice_message)

        while choice_message.tool_calls:
            for idx, tool_call in enumerate(choice_message.tool_calls):
                tool_result = await self.execute_tool(tool_call.function.name, tool_call.function.arguments)
                tool_message = Message(role="tool", content=tool_result, tool_call_id=tool_call.id, tool_name = tool_call.function.name)
                await self.save_history(tool_message)
            
            response = await self._llm.chat(self._history, using_stream=using_stream)
            choice = response.choices[0]
            choice_message = choice.message
            await self.save_history(choice_message)
        
        return response.choices[0].message

    async def save_history(self, choice_message: Message):
        self._history.append(choice_message)

    async def execute_tool(self, tool_name: str, tool_args: Dict):
        for tool in self.available_tools:
            if tool.name == tool_name:
                return tool.execute(tool_args)
        return None


def create_agent():
    return Agent(available_tools=[])


class AgentContext:
    def __init__(self):
        self._agents = []
        self._history = []
        self._call_stack = []
        self._loop = asyncio.new_event_loop()
        self._current_task = None
        self._main_agent = None
 
    def run(self, input: str):
        with AgentStack(self._agents, self._main_agent, self._call_stack):
            self._loop.run_until_complete(self._main_agent.run(input, using_stream=True))

    async def report(self, data: Union[dict, Callable[[], Awaitable[Dict]]], await_timeout: float = 10.0) -> None:
        pass

    async def run_wrapper(self, request: ChatRequest) -> None:
        await self.load_persistence_context()
        self.create_main_agent()
        user_input = None

        async with HeartbeatContext(report_func=self.emit_heartbeat):
            async with AgentStack(self._agents, self._main_agent, self._call_stack) as agent_stack:
                await agent_stack.run(user_input=user_input, using_stream=True)
                await self.wait_for_async_tasks(waiting_time=30)

    async def wait_for_async_tasks(self, waiting_time: int = 30) -> None:
        await asyncio.wait_for(asyncio.gather(*self._async_tasks), timeout=waiting_time)

    def create_main_agent(self):
        if self.get_main_agent() is None:
            self.set_main_agent(create_agent())

    def set_main_agent(self, agent: AgentType) -> None:
        self._main_agent = agent
        if agent:
            self._current_agent_id = agent.id
            agent.set_persist(True)
            # Set agent name for context management
            if hasattr(agent, 'agent_name'):
                self.set_agent_name(agent.agent_name)

    async def chat(self, request: ChatRequest) -> None:
        self._current_task = asyncio.create_task(self.run_wrapper(request))
        await self._current_task

    async def cancel(self):
        if self._current_task is not None:
            self._current_task.cancel()
            await self._current_task
        else:
            logger.warning(f"Task was not exist. conversation_id:{self._base_info.conversation_id}")
