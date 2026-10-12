import pytest
from langchain_core.messages import AIMessage

import app.services.llm_service as llm_mod
from app.core.config import Settings
from app.services.llm_service import LLMService


class FakeLLM:
    """Async-only fake: any use of the sync invoke() path fails the test (spec D8)."""

    def __init__(self, result):
        self.result = result
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return self.result

    def invoke(self, prompt):
        raise AssertionError("LLMService must call ainvoke, not invoke via an executor")


def service_returning(result) -> LLMService:
    svc = LLMService()
    svc.llm = FakeLLM(result)
    return svc


async def test_plain_string_response_is_stripped():
    assert await service_returning("  Model is working \n")._generate_response("p") == "Model is working"


async def test_chat_message_response_is_normalized_to_text():
    msg = AIMessage(content="  An answer.  ")
    assert await service_returning(msg)._generate_response("p") == "An answer."


async def test_thinking_parts_are_dropped_from_list_content():
    msg = AIMessage(content=[
        {"type": "thinking", "thinking": "internal reasoning"},
        {"type": "text", "text": " Final answer. "},
    ])
    assert await service_returning(msg)._generate_response("p") == "Final answer."


async def test_prompt_is_passed_through_unchanged():
    svc = service_returning("ok")
    await svc._generate_response("exact prompt {x1}")
    assert svc.llm.prompts == ["exact prompt {x1}"]


def test_default_model_comes_from_active_provider(monkeypatch):
    vertex = Settings.from_env({"LLM_PROVIDER": "vertex", "VERTEX_LLM_MODEL": "gemini-test-flash",
                                "VERTEX_EMBED_MODEL": "e", "GOOGLE_CLOUD_PROJECT": "p"})
    calls = []
    monkeypatch.setattr(llm_mod, "get_settings", lambda: vertex)
    monkeypatch.setattr(llm_mod, "get_llm", lambda temperature, model=None: calls.append((temperature, model)) or object())
    svc = LLMService(temperature=0.4)
    assert svc.model_name == "gemini-test-flash"
    assert calls == [(0.4, "gemini-test-flash")]


def test_local_default_model_unchanged():
    assert LLMService().model_name == "gpt-oss:20b"
