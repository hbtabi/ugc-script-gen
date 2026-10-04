"""Exercise the OpenAI-compatible client against a tiny local HTTP server (no network needed)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ugc_script_gen import generate_hooks, load_brief
from ugc_script_gen.llm import LLMError, MockLLM, OpenAICompatibleLLM, get_llm

BRIEF = load_brief("examples/briefs/driftwell-sleep-mask.toml")


@pytest.fixture
def server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append((self.path, self.headers["Authorization"], body))
            content = '["Your 5am alarm clock is the sun?", "I sleep in now. Here is why."]'
            payload = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1", calls
    httpd.shutdown()


def test_client_posts_chat_completion(server):
    url, calls = server
    llm = OpenAICompatibleLLM("sk-test", url, "test-model")
    hooks = llm.propose_hooks(BRIEF, 2)
    assert hooks[0].startswith("Your 5am")
    path, auth, body = calls[0]
    assert path == "/v1/chat/completions" and auth == "Bearer sk-test" and body["model"] == "test-model"
    pool = generate_hooks(BRIEF, n=200, llm=llm)
    assert sum(h.angle == "llm" for h in pool) == 2


def test_polish_length_mismatch_raises(server):
    url, _ = server
    with pytest.raises(LLMError):
        OpenAICompatibleLLM("k", url).polish_lines(["a", "b", "c"], BRIEF)


def test_unreachable_server_raises_llm_error():
    with pytest.raises(LLMError):
        OpenAICompatibleLLM("k", "http://127.0.0.1:9/v1", timeout=1).propose_hooks(BRIEF)


def test_get_llm_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_llm(), MockLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("UGC_MODEL", "llama3")
    llm = get_llm()
    assert isinstance(llm, OpenAICompatibleLLM) and llm.model == "llama3"
    assert isinstance(get_llm(offline=True), MockLLM)
