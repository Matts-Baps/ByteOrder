"""Run the scripted customers against a running assistant-service.

    uv run python -m scenarios.run --url http://localhost:9002
    uv run python -m scenarios.run --tag injection --repeat 3

Every conversation gets a `gen_ai.conversation.id` starting with `scenario-<case id>-`,
so you can find its traces in Dash0. Needs the demo menu loaded (see scenarios.seed).
"""
import argparse
import sys
import uuid

import httpx

from scenarios.cases import CASES


def run_case(client: httpx.Client, case: dict) -> tuple[bool, list[str], dict]:
    messages = list(case.get("history", []))
    conversation_id = f"scenario-{case['id']}-{uuid.uuid4().hex[:8]}"
    data: dict = {}
    for turn in case["turns"]:
        messages.append({"role": "user", "content": turn})
        resp = client.post(
            "/chat",
            json={
                "messages": messages,
                "customer_name": case.get("customer_name", "Sam"),
                "conversation_id": conversation_id,
            },
        )
        if resp.status_code == 429:
            return False, ["rate limited: raise RATE_LIMIT_PER_CLIENT_PER_MINUTE and "
                           "RATE_LIMIT_PER_KITCHEN_PER_MINUTE on the service for test runs"], {}
        if resp.status_code != 200:
            return False, [f"HTTP {resp.status_code}: {resp.text[:200]}"], {}
        data = resp.json()
        messages.append({"role": "assistant", "content": data["reply"]})

    problems = []
    draft_names = [i["menu_item_name"] for i in (data.get("draft") or {}).get("items", [])]
    if "draft" in case and sorted(draft_names) != sorted(case["draft"]):
        problems.append(f"draft was {draft_names or 'empty'}, expected {case['draft']}")
    if case.get("no_draft") and draft_names:
        problems.append(f"expected no draft, got {draft_names}")
    reply = data.get("reply", "").casefold()
    for text in case.get("not_in_reply", []):
        if text.casefold() in reply:
            problems.append(f"reply contains {text!r}")
    return not problems, problems, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:9002")
    parser.add_argument("--kitchen", default="default", help="X-Kitchen-ID to send (ignored in self-hosted mode)")
    parser.add_argument("--tag", action="append", help="only run cases with this tag (repeatable)")
    parser.add_argument("--case", action="append", help="only run this case id (repeatable)")
    parser.add_argument("--repeat", type=int, default=1, help="run each case this many times")
    parser.add_argument("--verbose", "-v", action="store_true", help="print every reply")
    args = parser.parse_args()

    cases = [
        c for c in CASES
        if (not args.tag or set(args.tag) & set(c["tags"])) and (not args.case or c["id"] in args.case)
    ]
    passed = total = 0
    with httpx.Client(base_url=args.url, headers={"X-Kitchen-ID": args.kitchen}, timeout=120) as client:
        for case in cases:
            for _ in range(args.repeat):
                ok, problems, data = run_case(client, case)
                total += 1
                passed += ok
                print(f"{'PASS' if ok else 'FAIL'}  {case['id']}")
                for problem in problems:
                    print(f"      - {problem}")
                if args.verbose or not ok:
                    print(f"      reply: {data.get('reply', '')!r}")
    print(f"\n{passed}/{total} passed the quick checks")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
