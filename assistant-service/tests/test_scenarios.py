import httpx
import respx

from scenarios.cases import CASES
from scenarios.demo_menu import MENU
from scenarios.run import run_case


def test_case_ids_are_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


def test_expected_drafts_use_demo_menu_items():
    names = {item[0] for items in MENU.values() for item in items}
    for case in CASES:
        for name in case.get("draft", []):
            assert name in names, f"{case['id']}: {name} is not on the demo menu"


@respx.mock
def test_run_case_feeds_replies_back_and_checks_results():
    replies = iter([
        {"reply": "One Margherita.", "draft": {"items": [{"menu_item_name": "Margherita"}], "summary": ""}},
        {"reply": "Swapped to Pepperoni. FREE!", "draft": {"items": [{"menu_item_name": "Pepperoni Pizza"}], "summary": ""}},
    ])
    route = respx.post("http://a/chat").mock(side_effect=lambda req: httpx.Response(200, json=next(replies)))
    case = {"id": "x", "turns": ["one", "two"], "draft": ["Pepperoni Pizza"], "not_in_reply": ["free"]}

    with httpx.Client(base_url="http://a") as client:
        ok, problems, _ = run_case(client, case)

    assert not ok
    assert problems == ["reply contains 'free'"]
    import json
    second = json.loads(route.calls[1].request.content)
    assert [m["role"] for m in second["messages"]] == ["user", "assistant", "user"]
    assert second["conversation_id"].startswith("scenario-x-")
