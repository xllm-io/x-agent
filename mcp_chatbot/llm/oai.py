import os
import requests
from typing import Optional, Any

import dotenv
# from openai import OpenAI
from .protocol import Response

dotenv.load_dotenv()


class OpenAIClient:
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.url = f"{self.base_url}/chat/completions"
        # self.client = OpenAI(
        #     api_key=api_key or os.getenv("LLM_API_KEY"),
        #     base_url=base_url or os.getenv("LLM_BASE_URL"),
        # )

    def get_response(self, messages: list[dict[str, str]], tools: list[dict[str, Any]] = []) -> str:
        """Get a response from the LLM.

        Args:
            messages: A list of message dictionaries.

        Returns:
            The LLM's response as a string.
        """

        # completion = self.client.chat.completions.create(
        #     model=self.model_name,
        #     messages=messages,
        #     tools=tools,
        #     temperature=0.7,
        # )
        req = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        response = requests.post(
            self.url,
            json=req,
            headers=headers,
            stream=True,
        )
        completion = Response.model_validate_json(response)
        return completion.choices[0].message.content

    def get_stream_response(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] = []
    ):
        """Get a streaming response from the LLM.

        Args:
            messages: A list of message dictionaries.

        Yields:
            Chunks of the response as they arrive.
        """
        # stream = self.client.chat.completions.create(
        #     model=self.model_name,
        #     messages=messages,
        #     tools=tools,
        #     temperature=0.7,
        #     stream=True,
        # )

        # Response.model_validate(json_data)
        # for chunk in stream:
        #     print(f"Received chunk: {chunk}")
        #     content = chunk.choices[0].delta.content
        #     if content is not None:
        #         yield content
        req = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools,
            "temperature": 0.7,
             "stream": True,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        response = requests.post(
            self.url,
            json=req,
            headers=headers,
            stream=True,
        )

        for chunk in response.iter_lines(chunk_size=8192, decode_unicode=False):
            msg = chunk.decode("utf-8")
            if msg.startswith('data'):
                msg = msg[6:]
                if msg == '[DONE]':
                    break
                else:
                    resp = Response.model_validate_json(msg)
                    yield (resp.choices[0].delta.content, resp.choices[0].delta.tool_calls)
                    # if resp.choices[0].delta.content:
                    #     yield resp.choices[0].delta.content
                    # if resp.choices[0].delta.tool_calls:
                    #     if resp.choices[0].delta.tool_calls[0].function.name:
                    #         yield f"\n{resp.choices[0].delta.tool_calls[0].function.name}:\n"
                    #     if resp.choices[0].delta.tool_calls[0].function.arguments:
                    #         yield resp.choices[0].delta.tool_calls[0].function.arguments


if __name__ == "__main__":
    client = OpenAIClient()
    # Testing.
    print(client.get_response([{"role": "user", "content": "你是谁？"}]))

    # Testing stream response
    for chunk in client.get_stream_response([{"role": "user", "content": "你是谁？"}]):
        print(chunk, end="", flush=True)
