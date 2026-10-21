import json

import httpx
import pytest
import respx

from app.llm import InvalidToolCall, LLMUnavailable, OllamaChat, ToolCall

URL = "http://ollama.test"


@respx.mock
async def test_chat_sends_native_request_and_parses_tool_calls():
    route = respx.post(f"{URL}/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "qwen3:4b-instruct",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "abc", "function": {"name": "propose_order", "arguments": {"items": []}}}
                    ],
                },
                "done_reason": "stop",
                "prompt_eval_count": 120,
                "eval_count": 15,
            },
        )
    )
    chat = OllamaChat(URL, "qwen3:4b-instruct", num_ctx=4096, max_output_tokens=256, temperature=0.2)
    response = await chat.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    body = json.loads(route.calls.last.request.content)
    assert body == {
        "model": "qwen3:4b-instruct",
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [{"type": "function"}],
        "stream": False,
        "options": {"num_ctx": 4096, "num_predict": 256, "temperature": 0.2},
    }
    assert response.tool_calls == [ToolCall(id="abc", name="propose_order", arguments={"items": []})]
    assert response.content == ""
    assert response.finish_reason == "stop"
    assert response.input_tokens == 120
    assert response.output_tokens == 15
    assert response.model == "qwen3:4b-instruct"


@respx.mock
async def test_chat_omits_unset_options_and_fills_missing_ids():
    route = respx.post(f"{URL}/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "m",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "tool_calls": [{"function": {"name": "t", "arguments": "{\"a\": 1}"}}],
                },
                "done_reason": "stop",
            },
        )
    )
    response = await OllamaChat(URL, "m", max_output_tokens=None).chat([], tools=[])
    assert "options" not in json.loads(route.calls.last.request.content)
    assert response.tool_calls[0].id.startswith("call_")
    assert response.tool_calls[0].arguments == {"a": 1}
    assert response.input_tokens is None


@respx.mock
async def test_unparseable_tool_arguments_become_empty_dict():
    respx.post(f"{URL}/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "m",
                "message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "t", "arguments": "{nope"}}]},
            },
        )
    )
    response = await OllamaChat(URL, "m").chat([], tools=[])
    assert response.tool_calls[0].arguments == {}


@respx.mock
async def test_errors_raise_llm_unavailable():
    respx.post(f"{URL}/api/chat").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(LLMUnavailable):
        await OllamaChat(URL, "m").chat([], tools=[])


@respx.mock
async def test_malformed_tool_call_is_its_own_error():
    respx.post(f"{URL}/api/chat").mock(
        return_value=httpx.Response(
            500,
            json={"error": "llama-server returned invalid tool call arguments for \"propose_order\": unexpected end of JSON input"},
        )
    )
    with pytest.raises(InvalidToolCall, match="unexpected end of JSON input"):
        await OllamaChat(URL, "m").chat([], tools=[])


@respx.mock
async def test_connection_errors_raise_llm_unavailable():
    respx.post(f"{URL}/api/chat").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(LLMUnavailable):
        await OllamaChat(URL, "m").chat([], tools=[])


@respx.mock
async def test_output_is_capped_by_default():
    route = respx.post(f"{URL}/api/chat").mock(
        return_value=httpx.Response(200, json={"model": "m", "message": {"role": "assistant", "content": "x"}})
    )
    await OllamaChat(URL, "m").chat([], tools=[])
    assert json.loads(route.calls.last.request.content)["options"] == {"num_predict": 512}


def test_server_address_and_port():
    chat = OllamaChat("https://ollama.wallace.network", "m")
    assert chat.server_address == "ollama.wallace.network"
    assert chat.server_port == 443
