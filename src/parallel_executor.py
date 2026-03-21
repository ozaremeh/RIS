# src/parallel_executor.py

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from model_registry import get_model


# ------------------------------------------------------------
# Model Task
# ------------------------------------------------------------

@dataclass
class ModelTask:
    """
    Represents a single model call to be executed in parallel.
    """
    model_key: str
    prompt: str
    temperature: float = 0.2
    max_tokens: int = 1024
    metadata: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------
# LM Studio / llama.cpp async client
# ------------------------------------------------------------

async def call_lmstudio_async(
    model_name: str,
    port: int,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Asynchronous call to an LM Studio or llama.cpp model server.
    Works for:
      - Phi-4 Reasoner
      - Qwen2.5 72B Writer
      - DeepSeek Coder
      - DeepSeek Math
      - Any LM Studio model
    """
    url = f"http://localhost:{port}/v1/chat/completions"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                text = await resp.text()
                raise RuntimeError(f"Invalid JSON from model server: {text}")

            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                raise RuntimeError(f"Unexpected response format: {data}")


# ------------------------------------------------------------
# Parallel Executor
# ------------------------------------------------------------

class ParallelExecutor:
    """
    Runs multiple model tasks concurrently using asyncio.
    Supports:
      - coder + reasoner parallelism
      - writer + reasoner parallelism
      - future math + reasoner hybrid mode
    """

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout

    async def _run_single(self, task: ModelTask) -> Dict[str, Any]:
        """
        Run a single model task.
        """
        model_info = get_model(task.model_key)

        try:
            output = await call_lmstudio_async(
                model_name=model_info["model_name"],
                port=model_info["port"],
                prompt=task.prompt,
                temperature=task.temperature,
                max_tokens=task.max_tokens,
            )

            return {
                "model": task.model_key,
                "output": output,
                "metadata": task.metadata,
                "error": None,
            }

        except Exception as e:
            return {
                "model": task.model_key,
                "output": None,
                "metadata": task.metadata,
                "error": str(e),
            }

    async def run(self, tasks: List[ModelTask]) -> List[Dict[str, Any]]:
        """
        Run all tasks concurrently and return results.
        """
        coroutines = [self._run_single(t) for t in tasks]

        if self.timeout:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*coroutines),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                return [
                    {
                        "model": t.model_key,
                        "output": None,
                        "metadata": t.metadata,
                        "error": "timeout",
                    }
                    for t in tasks
                ]
        else:
            results = await asyncio.gather(*coroutines)

        return results
