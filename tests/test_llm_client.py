import types
import unittest
from unittest.mock import patch

from agents import llm_client


class DummyAnthropicClient:
    def __init__(self):
        self.messages = types.SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        raise RuntimeError("blocked")


class DummyOpenAIClient:
    def __init__(self):
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self.create)
        )

    def create(self, **kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="fallback reply"))]
        )


class LLMClientFallbackTest(unittest.TestCase):
    def test_chat_falls_back_to_openai_when_anthropic_fails(self):
        with patch.object(llm_client, "_ANTHROPIC_CLIENT", DummyAnthropicClient()), patch.object(
            llm_client, "_OPENAI_CLIENT", DummyOpenAIClient()
        ):
            result = llm_client.chat("system", "user")

        self.assertEqual(result, "fallback reply")


if __name__ == "__main__":
    unittest.main()
