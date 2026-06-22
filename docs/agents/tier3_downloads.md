**Tier 3 다운로드 산출물**

목적
- Streamlit 분석 결과를 사용자가 파일로 내려받을 수 있게 합니다.
- 기존 placeholder였던 `PB 리포트`, `밸류에이션 Excel`, `산업/뉴스 분석 HTML`을 실제 다운로드 버튼으로 연결합니다.

현재 지원 파일
- PDF 리포트
  - Tier 1 핵심 판단, 신뢰도, 포트폴리오 적합도, 투자 근거, 리스크, 권장 행동을 포함합니다.
  - 현재는 간단 PB 리포트 형태이며, 7페이지 정식 템플릿은 후속 개선 범위입니다.
- Excel 밸류에이션
  - `Summary`, `Tier2`, `Tier3`, `Quant` 시트를 생성합니다.
  - Quant 지표(PER, PBR, ROE, 성장률, 부채비율, 종가 등)를 함께 포함합니다.
- HTML 분석
  - 브라우저에서 바로 열 수 있는 분석 요약 HTML입니다.
  - Tier 1/2/3 내용을 섹션별로 정리합니다.

구현 위치
- UI 다운로드 버튼: `streamlit_app.py`
- Tier3 상태 문구: `src/stock_agent/graph/pipeline.py`

UI 확인 방법
1. Docker app을 실행합니다.

   ```bash
   docker compose --profile app up -d app
   ```

2. 브라우저에서 앱을 엽니다.

   ```text
   http://localhost:8501
   ```

3. 분석을 실행한 뒤 요약 카드 아래의 `산출물 다운로드` 영역을 확인합니다.

4. 다음 버튼이 보여야 합니다.
   - `PDF 리포트`
   - `Excel 밸류에이션`
   - `HTML 분석`

검증
- `streamlit_app` import 확인
- Guardrail 관련 테스트 통과

```bash
python -m pytest tests/agents/test_guardrail_agent.py tests/agents/test_pipeline_guardrail_integration.py -q
```

현재 한계
- PDF는 외부 PDF 라이브러리 없이 생성하는 간단 리포트입니다.
- 정식 PB 리포트 디자인, 차트, 표지, 페이지 구분, DOCX 생성은 후속 작업이 필요합니다.
- Excel은 별도 라이브러리 없이 `.xlsx` ZIP/XML을 직접 생성하므로, 복잡한 차트/서식은 후속 개선 범위입니다.
