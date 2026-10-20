"""Databasfria tester för DeepSeek-klienten. Inga nätverksanrop."""
import unittest
from types import SimpleNamespace

from infrastructure.deepseek import DeepSeekClient, DeepSeekError
from infrastructure.settings import DeepSeekSettings, load_deepseek


class LoadDeepSeekTests(unittest.TestCase):
    def test_reads_key_and_defaults_model(self):
        variables = {"DEEPSEEK_API_KEY": "sk-test-123"}
        settings = load_deepseek(variables=variables)
        self.assertEqual(settings.api_key, "sk-test-123")
        self.assertEqual(settings.model, "deepseek-flash")
        self.assertEqual(settings.base_url, "https://api.deepseek.com")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            load_deepseek(variables={})

    def test_whitespace_in_key_rejected(self):
        with self.assertRaises(ValueError):
            load_deepseek(variables={"DEEPSEEK_API_KEY": "sk test"})

    def test_repr_does_not_leak_key(self):
        settings = load_deepseek(variables={"DEEPSEEK_API_KEY": "sk-super-secret"})
        self.assertNotIn("sk-super-secret", repr(settings))

    def test_model_can_be_overridden(self):
        settings = load_deepseek(variables={
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_MODEL": "deepseek-reasoner",
        })
        self.assertEqual(settings.model, "deepseek-reasoner")


class _FakeCompletions:
    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


class _FakeClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


class DeepSeekClientTests(unittest.TestCase):
    def _settings(self):
        return DeepSeekSettings(api_key="sk-test", model="deepseek-flash")

    def test_chat_returns_content_and_does_not_leak_key(self):
        completions = _FakeCompletions(content="hej")
        client = DeepSeekClient(self._settings(), client=_FakeClient(completions))
        result = client.chat([{"role": "user", "content": "hej"}])
        self.assertEqual(result, "hej")
        self.assertEqual(completions.calls[0]["model"], "deepseek-flash")
        self.assertNotIn("sk-test", repr(client))

    def test_empty_response_raises(self):
        completions = _FakeCompletions(content="")
        client = DeepSeekClient(self._settings(), client=_FakeClient(completions),
                                max_retries=0)
        with self.assertRaises(DeepSeekError):
            client.chat([{"role": "user", "content": "hej"}])

    def test_retries_on_transient_error(self):
        class _Flaky:
            def __init__(self):
                self.calls = 0
            def create(self, **kwargs):
                self.calls += 1
                if self.calls < 2:
                    raise RuntimeError("tillfälligt fel")
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
                )

        flaky = _Flaky()
        client = DeepSeekClient(self._settings(),
                                client=_FakeClient(flaky),
                                max_retries=2, backoff_seconds=0.0)
        self.assertEqual(client.chat([{"role": "user", "content": "hej"}]), "ok")
        self.assertEqual(flaky.calls, 2)


if __name__ == "__main__":
    unittest.main()
