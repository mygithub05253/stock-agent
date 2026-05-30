from streamlit.testing.v1 import AppTest

from stock_agent.intake import onboarding_card_count


def _complete_onboarding(at: AppTest) -> AppTest:
    for _ in range(onboarding_card_count()):
        button = next(widget for widget in at.button if widget.label in {"다음", "성향 분석"})
        button.click()
        at.run(timeout=10)
    return at


def test_staged_intake_reaches_portfolio_step() -> None:
    at = AppTest.from_file("streamlit_app.py")
    at.run(timeout=10)

    _complete_onboarding(at)

    assert any("투자 성향 분석 에이전트 결과" in widget.value for widget in at.subheader)
    assert any("후보 산업" in widget.label for widget in at.multiselect)
    assert any("SK하이닉스 수량" in widget.label for widget in at.number_input)
    assert any("SK하이닉스 평단가" in widget.label for widget in at.number_input)
    assert any("삼성전자 수량" in widget.label for widget in at.number_input)
    assert any("보유 현금" in widget.label for widget in at.number_input)

    qty_input = next(widget for widget in at.number_input if widget.label == "SK하이닉스 수량")
    qty_input.set_value(10)
    at.run(timeout=10)

    assert any(widget.label == "총 평가금액" for widget in at.metric)


def test_staged_intake_runs_analysis_after_portfolio_save() -> None:
    at = AppTest.from_file("streamlit_app.py")
    at.run(timeout=10)
    _complete_onboarding(at)

    qty_input = next(widget for widget in at.number_input if widget.label == "SK하이닉스 수량")
    qty_input.set_value(10)
    at.run(timeout=10)

    save_button = next(widget for widget in at.button if widget.label == "투자성향 확인")
    save_button.click()
    at.run(timeout=10)

    assert any("대화형 질문" in widget.value for widget in at.subheader)
    run_button = next(widget for widget in at.button if widget.label == "분석 실행")
    run_button.click()
    at.run(timeout=10)

    assert any(widget.label == "포트폴리오 적합도" for widget in at.metric)
    assert any("질문 분류" in widget.value for widget in at.markdown)
