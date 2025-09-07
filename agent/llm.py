class LLM:
    def __init__(self, model_name: str, model_params: dict):
        self.model_name = model_name
        self.model_params = model_params

    async def chat(self, input: str, using_stream: bool):
        pass