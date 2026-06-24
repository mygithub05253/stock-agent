"""경량 관측(Observability) 레이어.

루브릭 #3(sLLM + 검증 + 관측)의 "관측" 요구를 의존성 없이 충족하기 위한 모듈이다.
- langfuse가 설치·설정돼 있으면 trace/span을 전송한다.
- 없으면 구조화된 로깅으로 폴백한다.

따라서 로컬·CI·Docker 어디서나 import 실패 없이 동작하며, 폴백 철학(에러핸들링 일관성)을
관측 레이어에도 그대로 적용한다. 각 에이전트는 `Trace`로 span을 기록하고 `flush()`로 내보낸다.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger("stock_agent.observability")


@dataclass
class Span:
    """단일 작업 구간. 이름·상태·속성·소요시간을 담는다."""

    name: str
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None


@dataclass
class Trace:
    """한 에이전트 실행에 대한 span 묶음."""

    name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spans: list[Span] = field(default_factory=list)

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        """span 컨텍스트. 예외 발생 시 status=error로 기록하고 그대로 전파한다."""
        current = Span(name=name, attributes=dict(attributes))
        start = time.perf_counter()
        try:
            yield current
        except Exception as exc:  # 관측은 실패를 삼키지 않고 기록만 한 뒤 재전파한다.
            current.status = "error"
            current.attributes["error"] = f"{exc.__class__.__name__}: {exc}"
            raise
        finally:
            current.duration_ms = round((time.perf_counter() - start) * 1000, 3)
            self.spans.append(current)

    def as_dicts(self) -> list[dict[str, Any]]:
        """span을 직렬화 가능한 dict 목록으로 변환 (스키마 checks/저장용)."""
        return [
            {
                "name": s.name,
                "status": s.status,
                "duration_ms": s.duration_ms,
                **s.attributes,
            }
            for s in self.spans
        ]


def _emit_to_langfuse(trace: Trace) -> bool:
    """langfuse가 사용 가능하면 trace를 전송한다. 미설치·실패 시 False 반환."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return False

    try:
        from langfuse import Langfuse  # type: ignore
    except Exception:
        return False

    try:
        client = Langfuse()  # 키는 환경변수(LANGFUSE_*)에서 자동 로드
        if hasattr(client, "trace"):
            root = client.trace(id=trace.trace_id, name=trace.name)
            for span in trace.spans:
                root.span(
                    name=span.name,
                    metadata=span.attributes,
                    level="ERROR" if span.status == "error" else "DEFAULT",
                )
        else:
            trace_context = {"trace_id": trace.trace_id}
            client.create_event(
                trace_context=trace_context,
                name=trace.name,
                metadata={"span_count": len(trace.spans)},
            )
            for span in trace.spans:
                client.create_event(
                    trace_context=trace_context,
                    name=span.name,
                    metadata={
                        **span.attributes,
                        "duration_ms": span.duration_ms,
                    },
                    level="ERROR" if span.status == "error" else "DEFAULT",
                    status_message=span.status,
                )
        client.flush()
        return True
    except Exception as exc:  # 관측 실패가 본 파이프라인을 막아서는 안 된다.
        logger.warning("langfuse 전송 실패, 로깅으로 폴백: %s", exc)
        return False


def flush(trace: Trace) -> None:
    """trace를 내보낸다. langfuse 우선, 실패·미설치 시 구조화 로깅."""
    if not _emit_to_langfuse(trace):
        logger.info(
            "trace_id=%s name=%s spans=%s",
            trace.trace_id,
            trace.name,
            trace.as_dicts(),
        )
