"""
大语言模型客户端模块
封装不同LLM提供商（OpenAI API、智谱API、本地模型）的统一调用接口
"""

import json
from typing import Optional, List, Dict, Any, Generator
from abc import ABC, abstractmethod

from app.core.config import settings


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话接口"""
        pass

    @abstractmethod
    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """流式对话接口"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API 客户端"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.API_KEY
        self.base_url = base_url or settings.API_BASE_URL
        self.model = model or settings.LLM_MODEL_NAME

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", settings.TEMPERATURE),
                "max_tokens": kwargs.get("max_tokens", settings.MAX_OUTPUT_TOKENS),
                "top_p": kwargs.get("top_p", settings.TOP_P),
                "stream": False
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"[API调用错误] {str(e)}"

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", settings.TEMPERATURE),
                "max_tokens": kwargs.get("max_tokens", settings.MAX_OUTPUT_TOKENS),
                "top_p": kwargs.get("top_p", settings.TOP_P),
                "stream": True
            }

            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", f"{self.base_url}/chat/completions",
                                   headers=headers, json=payload) as response:
                    for line in response.iter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            yield f"[API调用错误] {str(e)}"


class ZhipuClient(BaseLLMClient):
    """智谱 ChatGLM API 客户端"""

    def __init__(self, api_key: str = None, model: str = "glm-4"):
        self.api_key = api_key or settings.API_KEY
        self.model = model

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", settings.TEMPERATURE),
                "max_tokens": kwargs.get("max_tokens", settings.MAX_OUTPUT_TOKENS),
                "top_p": kwargs.get("top_p", settings.TOP_P),
                "stream": False
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"[智谱API调用错误] {str(e)}"

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", settings.TEMPERATURE),
                "max_tokens": kwargs.get("max_tokens", settings.MAX_OUTPUT_TOKENS),
                "stream": True
            }

            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                   headers=headers, json=payload) as response:
                    for line in response.iter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            yield f"[智谱API调用错误] {str(e)}"


class LocalModelClient(BaseLLMClient):
    """本地模型客户端（使用Transformers加载开源模型）"""

    def __init__(self, model_name: str = None, model_path: str = None):
        self.model_name = model_name or settings.LOCAL_MODEL_NAME
        self.model_path = model_path or settings.LOCAL_MODEL_PATH
        self._tokenizer = None
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_id = self.model_path or self.model_name
            print(f"正在加载本地模型: {model_id} ...")

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_id, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            print("本地模型加载完成")
        except Exception as e:
            raise RuntimeError(f"加载本地模型失败: {e}")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        self._load_model()
        try:
            import torch

            # 构建输入
            prompt = self._build_prompt(messages)

            inputs = self._tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=kwargs.get("max_tokens", settings.MAX_OUTPUT_TOKENS),
                    temperature=kwargs.get("temperature", settings.TEMPERATURE),
                    top_p=kwargs.get("top_p", settings.TOP_P),
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id
                )

            response = self._tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            return response.strip()

        except Exception as e:
            return f"[本地模型推理错误] {str(e)}"

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        # 本地模型暂不支持流式，直接返回完整结果
        yield self.chat(messages, **kwargs)

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建模型输入提示词"""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
        prompt += "<|assistant|>\n"
        return prompt


def create_llm_client(provider: str = None) -> BaseLLMClient:
    """工厂函数：根据配置创建LLM客户端"""
    provider = provider or settings.LLM_PROVIDER

    if provider == "openai":
        return OpenAIClient()
    elif provider == "zhipu":
        return ZhipuClient()
    elif provider == "local":
        return LocalModelClient()
    else:
        raise ValueError(f"不支持的LLM提供商: {provider}")
