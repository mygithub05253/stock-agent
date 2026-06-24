import sys
from types import SimpleNamespace

from stock_agent.observability import Span, Trace, _emit_to_langfuse


def test_emit_to_langfuse_v4_event_api(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class FakeLangfuse:
        def create_event(self, **kwargs):
            calls.append(("create_event", kwargs))

        def flush(self):
            calls.append(("flush", {}))

    fake_module = SimpleNamespace(Langfuse=FakeLangfuse)
    monkeypatch.setitem(sys.modules, "langfuse", fake_module)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    trace = Trace(name="guardrail", trace_id="trace-1")
    trace.spans.append(
        Span(
            name="policy_check",
            status="error",
            attributes={"rule": "investment_guarantee"},
            duration_ms=12.3,
        )
    )

    assert _emit_to_langfuse(trace) is True
    assert calls[0][0] == "create_event"
    assert calls[0][1]["trace_context"] == {"trace_id": "trace-1"}
    assert calls[1][1]["name"] == "policy_check"
    assert calls[1][1]["level"] == "ERROR"
    assert calls[-1][0] == "flush"
