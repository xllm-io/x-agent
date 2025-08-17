# Python script
import json
import requests
from typing import Dict, List
from protocol import ChatCompletionStreamResponse, ChatCompletionResponse

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

#  <service_url>：替换为服务访问地址。
end_point = "https://gpt-bj.singularity-ai.com/gpt-proxy/router"
openai_key = "1a463c8c36a4b97be88db4f4b1ececab"
model_id = 'claude37-sonnet'

# openai_key = "OGJiOGU0NDlmMzkxNTQ2MmUxNmZmMjdhODlmMWI2ZjUwOGFmMjQ1Yg=="
# end_point = "http://1893706806886638.cn-shanghai.pai-eas.aliyuncs.com/api/predict/prod_qw25_2050_agent_mcpimg_814v1ep3_0815_q/v1"
# model_id = "qw25_2050_agent_mcpimg_814v1ep3_0815_q"

use_chat = True
stream = False
if use_chat:
    url = f"{end_point}/chat/completions"
    prompt = load_json("debug_oai_request.json").get('messages', [])
    tools = load_json("debug_oai_request.json").get("tools", [])


# model_id = 'claude37-sonnet'
print(f"model_id: {model_id}")

req = {
    "model": model_id,
    "messages" if use_chat else "prompt": prompt,
    "tools": tools,
    # "tool_choice": {"type": "function", "function":{"name":"parallel_web_search"}},
    "stream": stream,
    "temperature": 0.0,
    "top_p": 1.0,
    "top_k": 10,
    "max_tokens": 8192,
    "stream_options": {
        "include_usage": True,
    },    
}
# print(f"req: {req}")
response = requests.post(
    url,
    json=req,
    # <Your EAS Token>：替换为服务Token。
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
    stream=True,
)
for chunk in response.iter_lines(chunk_size=8192, decode_unicode=False):
    msg = chunk.decode("utf-8")
    # print(msg)
    # continue
    if msg.startswith('data'):
        info = msg[6:]
        if info == '[DONE]':
            break
        else:
            if stream:
                resp = ChatCompletionStreamResponse.model_validate_json(info)
                # print(f"{resp}")
                # print(f"resp_stream: {resp.model_dump_json()}")
                if resp.usage:
                    print(f"\n##usage## total_tokens: {resp.usage.total_tokens}, prompt_tokens: {resp.usage.prompt_tokens}, completion_tokens: {resp.usage.completion_tokens}", end='', flush=True)
                if len(resp.choices) == 0:
                    continue
                if resp.choices[0].delta.content:
                    print(resp.choices[0].delta.content, end='', flush=True)
                if resp.choices[0].delta.tool_calls:
                    if resp.choices[0].delta.tool_calls[0].function.name:
                        print(f"\n{resp.choices[0].delta.tool_calls[0].function.name}:", end='\n', flush=True)
                    if resp.choices[0].delta.tool_calls[0].function.arguments:
                        print(resp.choices[0].delta.tool_calls[0].function.arguments, end='', flush=True)                 
    else:
        resp = ChatCompletionResponse.model_validate_json(msg)
        print(resp.choices[0].message.content)
        print(resp.choices[0].message.tool_calls[0])