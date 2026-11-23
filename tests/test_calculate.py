# ruff: noqa: F811 (`key` is a fixture from test_voice, used as an argument)
"""Quick job 86: real calculations for the hub's assistant (`calculate`: Python math run on the
brain, in quick job 81's restricted runner)."""

import json
from collections import deque

from test_arm_desk import ai_service
from test_chat import setup_for
from test_voice import key  # noqa: F401 (a fixture)

from lab_os.ai.assistant import Assistant
from lab_os.ai.chat import CALC, THINK_TOOL, Conversation, calc_answer
from lab_os.ai.spend import SpendLog
from lab_os.tools.program import calculate


def test_calculate_runs_math_and_says_why_not():
    assert json.loads(calc_answer(json.dumps({"code": "result = 37 * 48 + 199"}))) == {
        "value": 1975
    }
    code = "km = 1200\nkmh = 850\nresult = round(km / kmh * 60)  # minutes"
    assert json.loads(calc_answer(json.dumps({"code": code})))["value"] == 85
    stats = "result = round(statistics.stdev([2, 4, 4, 4, 5, 5, 7, 9]), 3)"
    assert json.loads(calc_answer(json.dumps({"code": stats})))["value"] == 2.138
    assert "ImportError" in calc_answer(json.dumps({"code": "import os"}))
    assert "no `result`" in calc_answer(json.dumps({"code": "x = 1"}))
    assert "valid JSON" in calc_answer("{oops")
    assert calculate("while True:\n    pass", time_limit_s=0.5)["result"] == "time limit"


def test_hard_questions_still_go_to_the_strong_model_but_not_arithmetic():
    words = THINK_TOOL["function"]["description"]
    assert "use calculate" in words and "maths or a calculation" not in words


async def test_the_assistant_calculates(aiohttp_server, tmp_path, key):
    script, seen = deque(), []
    script.extend(
        [
            ("tool", CALC, {"code": "result = 37 * 48 + 199"}),
            ("words", "37 times 48 is 1776; plus 199 makes 1975."),
        ]
    )
    setup = setup_for(await aiohttp_server(ai_service(script, seen)))
    conv = Conversation(Assistant(), SpendLog(tmp_path / "spend"), setups=lambda: {"main": setup})
    events = [e async for e in conv.ask("calculate 37 times 48, then add 199")]
    assert CALC in {t["function"]["name"] for t in seen[0]["tools"]}
    tool = next(m for m in seen[1]["messages"] if m["role"] == "tool")
    assert json.loads(tool["content"]) == {"value": 1975}
    assert any(e["type"] == "done" for e in events)
    await conv.close()
