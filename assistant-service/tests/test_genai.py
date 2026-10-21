import json

from app.genai import input_messages, output_messages, system_instructions
from app.llm import LLMResponse, ToolCall

CONVERSATION = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "One lemonade please"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "call_1", "function": {"name": "propose_order", "arguments": {"items": []}}}
        ],
    },
    {"role": "tool", "tool_call_id": "call_1", "tool_name": "propose_order", "content": "Draft ready"},
]


def test_system_instructions_are_separate():
    assert json.loads(system_instructions(CONVERSATION)) == [
        {"type": "text", "content": "You are helpful."}
    ]


def test_system_instructions_absent():
    assert system_instructions([{"role": "user", "content": "hi"}]) is None


def test_input_messages_follow_semconv_parts():
    assert json.loads(input_messages(CONVERSATION)) == [
        {"role": "user", "parts": [{"type": "text", "content": "One lemonade please"}]},
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool_call",
                    "id": "call_1",
                    "name": "propose_order",
                    "arguments": {"items": []},
                }
            ],
        },
        {
            "role": "tool",
            "parts": [{"type": "tool_call_response", "id": "call_1", "response": "Draft ready"}],
        },
    ]


def test_output_messages_include_text_tool_calls_and_finish_reason():
    response = LLMResponse(
        content="Here you go",
        tool_calls=[ToolCall(id="c2", name="propose_order", arguments={"items": [1]})],
        finish_reason="stop",
        model="qwen3:4b-instruct",
    )
    assert json.loads(output_messages(response)) == [
        {
            "role": "assistant",
            "parts": [
                {"type": "text", "content": "Here you go"},
                {"type": "tool_call", "id": "c2", "name": "propose_order", "arguments": {"items": [1]}},
            ],
            "finish_reason": "stop",
        }
    ]
