# Final Presentation Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 1조 stock-agent final presentation as a 14-slide browser HTML deck, PDF export, and PowerPoint deck using the approved 심사 설득형 structure.

**Architecture:** Keep one canonical slide source in a small JSON file, then render it into `final_presentation.html` and a PPTX. The HTML deck is optimized for live browser presentation and PDF export; the PPTX is created with the presentations skill and `@oai/artifact-tool` so it can be edited or projected from PowerPoint.

**Tech Stack:** HTML/CSS/JavaScript, Playwright/Chromium PDF export, `@oai/artifact-tool` for PPTX, existing stock-agent README assets, optional image generation for the title thumbnail.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/presentation/final_presentation_source.json` | Create | Canonical slide text, metrics, speaker-note source hints |
| `docs/presentation/final_presentation.html` | Create | Browser-based 16:9 final deck with keyboard navigation |
| `docs/presentation/final_presentation.pdf` | Create | PDF export from the HTML deck |
| `docs/presentation/final_presentation.pptx` | Create | PowerPoint deck generated with `@oai/artifact-tool` |
| `docs/assets/presentation/final-title-thumbnail.png` | Create | Title visual based on actual Streamlit result screen and multi-agent framing |
| `docs/assets/presentation/README.md` | Create | Asset provenance and update notes |
| `docs/presentation/README.md` | Modify | Link final presentation deliverables |
| `work/presentations/final-presentation/*` or temp scratch | Create outside commit scope | PPTX builder scripts, previews, QA logs |

Do not commit `.superpowers/`, API keys, generated scratch folders, or browser caches.

---

## Task 1: Branch And Source Inventory

**Files:**
- Verify: `docs/superpowers/specs/2026-06-24-final-presentation-design.md`
- Verify: `C:\Users\kik32\Downloads\stock_agent_research.html`
- Verify: `README.md`
- Verify: `docs/report/result_report.md`
- Verify: `docs/architecture/pipeline_11node_groundtruth.md`

- [ ] **Step 1: Confirm branch and untracked files**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## docs/final-presentation-design
?? .superpowers/
```

Only `.superpowers/` may be untracked before new presentation files are created.

- [ ] **Step 2: Extract source slide headings from the downloaded research HTML**

Run:

```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$html = Get-Content -Raw -Encoding UTF8 'C:\Users\kik32\Downloads\stock_agent_research.html'
[regex]::Matches($html, '<!--\s*=+\s*SLIDE\s+(\d+):\s*(.*?)\s*=+\s*-->', 'Singleline') |
  ForEach-Object { "Slide $($_.Groups[1].Value): $($_.Groups[2].Value.Trim())" }
```

Expected output:

```text
Slide 1: TITLE
Slide 2: 핵심 수치 5개
Slide 3: 상세 수치 표
Slide 4: 문제 정의 3문장
Slide 5: 왜 Agent가 필요한가
Slide 6: 경쟁 대안 한계 표
Slide 7: 행태 편향 데이터
Slide 8: 발표용 차트 아이디어
Slide 9: 출처 목록
Slide 10: CLOSING
```

- [ ] **Step 3: Confirm existing core assets**

Run:

```powershell
Test-Path docs\assets\readme\current-streamlit-results.png
Test-Path docs\assets\readme\current-streamlit-onboarding.png
Test-Path docs\assets\readme\stock-agent-architecture.png
```

Expected:

```text
True
True
True
```

---

## Task 2: Canonical Slide Source

**Files:**
- Create: `docs/presentation/final_presentation_source.json`

- [ ] **Step 1: Create canonical JSON source**

Create `docs/presentation/final_presentation_source.json` with exactly this structure:

```json
{
  "meta": {
    "title": "stock-agent 최종 발표",
    "subtitle": "개인 포트폴리오 기반 한국 주식 멀티에이전트 분석 보조 시스템",
    "team": "PoCaT BDAI 12기 1조",
    "date": "2026-06-27",
    "durationMinutes": 15
  },
  "slides": [
    {
      "id": 1,
      "kind": "title",
      "title": "stock-agent",
      "headline": "개인투자자의 의사결정을 구조화하는 멀티에이전트 분석 보조 시스템",
      "bullets": ["투자성향과 보유 포트폴리오를 함께 반영", "정량·정성·Peer·거시 데이터를 Agent가 분리 분석", "투자 권유가 아닌 근거 기반 분석 신호 제공"],
      "visual": "docs/assets/presentation/final-title-thumbnail.png",
      "speakerNote": "첫 문장은 주식 추천기가 아니라 분석 신호를 구조화하는 시스템이라고 못 박는다."
    },
    {
      "id": 2,
      "kind": "metrics",
      "title": "Why Now: 개인투자 시장은 커졌지만 판단 부담도 커졌다",
      "metrics": [
        {"label": "개인투자자", "value": "1,442만 명", "caption": "2025년 말 개인 기준"},
        {"label": "주식거래 활동계좌", "value": "1억 500만 개", "caption": "2026.04.29 금융투자협회"},
        {"label": "개인 MTS 거래 비중", "value": "65.7%", "caption": "2026년 1~5월 한국거래소"}
      ],
      "takeaway": "투자는 대중화되었지만, 판단은 더 빠르고 복잡한 모바일 환경으로 이동했다.",
      "speakerNote": "출처는 발표 본문에 크게 노출하지 않고 Q&A 대응용으로만 기억한다."
    },
    {
      "id": 3,
      "kind": "problem",
      "title": "문제: 정보는 많지만 근거 있는 통합 판단은 어렵다",
      "bullets": ["1~3종목 집중투자 비중 59.7%: 포트폴리오 리스크가 개인에게 집중", "디지털 금융이해력 59.3점: 모바일 금융 사용은 보편화됐지만 이해도는 부족", "2024년 개인 평균 수익률 -16.77%: 표본 분석 기준 시장 대비 부진"],
      "takeaway": "핵심 문제는 정보 부족이 아니라, 흩어진 정보를 내 포트폴리오 맥락에서 해석하는 능력의 부족이다.",
      "speakerNote": "-16.77%는 공식통계가 아니라 NH투자증권·머니투데이 표본 분석임을 질문 시 명확히 말한다."
    },
    {
      "id": 4,
      "kind": "comparison",
      "title": "기존 대안은 한 가지 축만 해결한다",
      "columns": ["대안", "포트폴리오 맥락", "멀티 관점", "안전 검증", "한계"],
      "rows": [
        ["증권사 MTS", "△", "△", "△", "정보는 많지만 종합 판단은 사용자 몫"],
        ["로보어드바이저", "○", "△", "△", "자산배분 중심, 개별 종목 근거 설명 약함"],
        ["범용 LLM", "×", "△", "×", "실시간 데이터·출처·환각 통제 한계"],
        ["stock-agent", "○", "○", "○", "포트폴리오 맥락에서 Agent별 근거를 합성"]
      ],
      "takeaway": "시장 공백은 내 보유 종목 기준으로 여러 근거를 검증해주는 분석 보조다.",
      "speakerNote": "stock-agent는 제안이 아니라 현재 구현한 MVP라는 표현을 사용한다."
    },
    {
      "id": 5,
      "kind": "agent-rationale",
      "title": "왜 멀티 Agent인가",
      "bullets": ["정량 Agent: DART·시세 기반 재무/밸류에이션 지표 계산", "정성 Agent: 뉴스·공시 RAG로 호재/악재 근거 탐색", "Peer·Macro Agent: 같은 업종 비교와 거시 환경 보완", "Guardrail: 투자 권유·위험 표현을 규칙 기반으로 완화"],
      "takeaway": "한 모델이 모든 판단을 말하는 구조보다, 역할을 나눠 계산·검색·합성·검증을 분리하는 구조가 더 설명 가능하다.",
      "speakerNote": "악마의 대변인이라는 표현 대신 Guardrail과 전문 Agent 관점 분리라고 말한다."
    },
    {
      "id": 6,
      "kind": "demo",
      "title": "사용 흐름: 7단계 성향 입력에서 Tier 결과까지",
      "bullets": ["1. 투자 목적·기간·손실 감내 등 7단계 성향 수집", "2. 보유 종목·평단·현금 비중 입력", "3. Agent 진행 상태를 실시간으로 확인", "4. HOLD/신뢰도/포트폴리오 적합도와 근거 확인"],
      "visuals": ["docs/assets/readme/current-streamlit-onboarding.png", "docs/assets/readme/current-streamlit-results.png"],
      "speakerNote": "라이브 데모가 실패해도 이 슬라이드가 데모 대체 역할을 한다."
    },
    {
      "id": 7,
      "kind": "architecture",
      "title": "시스템 구성: UI, DB/RAG, LangGraph, 안전 검증",
      "bullets": ["Streamlit UI에서 온보딩과 결과를 제공", "PostgreSQL + pgvector로 정형 데이터와 RAG 검색 통합", "LangGraph StateGraph와 Send API로 worker Agent 동적 fan-out", "LLM은 해석·합성에 사용하고, Guardrail은 규칙 기반으로 검증"],
      "visual": "docs/assets/readme/stock-agent-architecture.png",
      "speakerNote": "7장은 레이어, 8장은 11노드 흐름으로 나누어 설명한다."
    },
    {
      "id": 8,
      "kind": "flow",
      "title": "11노드 Agent 파이프라인",
      "nodes": ["Curator", "Classifier", "Quant", "Qual", "Competitor", "Macro", "Strategist", "InvestmentAnalyst", "Guardrail", "GuardrailApply", "ResultRenderer"],
      "takeaway": "Classifier 이후 필요한 worker를 병렬 실행하고, Strategist에서 join한 뒤 Analyst와 Guardrail을 통과한다.",
      "speakerNote": "기준 문서는 docs/architecture/pipeline_11node_groundtruth.md다."
    },
    {
      "id": 9,
      "kind": "deep-dive",
      "title": "핵심 Agent: 근거, 비교, 안전장치",
      "bullets": ["Competitor: DB→MCP→mock 3단 폴백과 6/6 회귀 평가", "Qual RAG: Hybrid 검색과 reranker 평가로 hit@5 1.0 기록", "Guardrail: 7게이트로 위험 표현·PII를 검증하고 재합성 루프 수행"],
      "takeaway": "Agent의 장점은 기능 추가가 아니라 실패와 책임 범위를 분리할 수 있다는 점이다.",
      "speakerNote": "구현된 사실만 말한다. Quant·Qual의 프롬프트는 있지만 일부 LLM 연결은 제한적이라고 질문 시 답한다."
    },
    {
      "id": 10,
      "kind": "differentiation",
      "title": "stock-agent의 차별점",
      "bullets": ["보유 종목·현금 비중·투자성향을 함께 보는 포트폴리오 맥락", "도구 계산과 LLM 해석을 분리해 환각 위험 완화", "부분 실패를 허용하는 degraded fallback", "낮은 RAGAS 점수까지 공개하는 평가 문화"],
      "speakerNote": "좋은 점만 말하지 않고 솔직한 평가 공개를 차별점으로 둔다."
    },
    {
      "id": 11,
      "kind": "validation",
      "title": "검증 결과: 강점과 한계를 같이 공개했다",
      "metrics": [
        {"label": "Phase 1 rule checks", "value": "40/41", "caption": "97.6%"},
        {"label": "Competitor 회귀", "value": "6/6", "caption": "100%"},
        {"label": "Qual RAG hit@5", "value": "1.0", "caption": "MRR 1.0 / nDCG 0.93"},
        {"label": "RAGAS faithfulness", "value": "0.41", "caption": "목표 0.80 미달"}
      ],
      "takeaway": "검색은 잘 맞지만 생성이 근거를 충분히 반영하지 못하는 한계를 다음 개선 과제로 잡았다.",
      "speakerNote": "D→C→B 개선 서사를 20초 안에만 언급한다."
    },
    {
      "id": 12,
      "kind": "business",
      "title": "상업성: 개인투자자용 PB-lite 분석 보조",
      "bullets": ["B2C: 개인투자자의 보유 종목 점검과 리포트 생성", "B2B: 증권·핀테크 앱의 설명형 AI 분석 모듈", "교육: 투자 판단 과정을 설명하는 실습형 튜터", "리서치 보조: 뉴스·공시·peer 요약 자동화"],
      "speakerNote": "규제 리스크 때문에 자동매매나 확정 추천이 아니라 분석 보조로 포지셔닝한다."
    },
    {
      "id": 13,
      "kind": "limits",
      "title": "한계와 발전 가능성",
      "bullets": ["RAG faithfulness 0.41 → 인용 스팬과 context gating으로 개선", "users·holdings·analysis_cache 영속화 테이블 구현 필요", "실데이터 범위와 커버 종목 확대 필요", "PB 리포트 PDF/Excel 다운로드와 운영 비용 제어 고도화"],
      "speakerNote": "한계를 숨기지 않고 다음 스프린트 작업으로 연결한다."
    },
    {
      "id": 14,
      "kind": "team",
      "title": "팀 역할과 결론",
      "bullets": ["이동원: PM·문서/설계·Competitor·평가/CI", "백형준: UI·투자성향 intake·LangGraph streaming·LLM 연동", "윤수정: Quant·Qual 공시·Guardrail·출력", "문수빈: Macro·Supabase·LangGraph fan-out", "김도예: 뉴스 크롤러·RAG 임베딩·Qual 검색 평가"],
      "takeaway": "우리는 투자 판단을 자동화한 것이 아니라, 판단에 필요한 근거를 Agent 구조로 분해하고 다시 합성했다.",
      "speakerNote": "마지막 문장은 또박또박 말하고 Q&A로 넘긴다."
    }
  ]
}
```

- [ ] **Step 2: Validate JSON**

Run:

```powershell
node -e "JSON.parse(require('fs').readFileSync('docs/presentation/final_presentation_source.json','utf8')); console.log('valid')"
```

Expected:

```text
valid
```

- [ ] **Step 3: Commit source JSON**

Run:

```powershell
git add docs/presentation/final_presentation_source.json
git commit -m "📝 Docs: 최종 발표 슬라이드 원천 JSON 추가"
```

---

## Task 3: Presentation Assets

**Files:**
- Create: `docs/assets/presentation/README.md`
- Create: `docs/assets/presentation/final-title-thumbnail.png`
- Reuse: `docs/assets/readme/current-streamlit-results.png`
- Reuse: `docs/assets/readme/current-streamlit-onboarding.png`
- Reuse: `docs/assets/readme/stock-agent-architecture.png`

- [ ] **Step 1: Create asset directory and README**

Create `docs/assets/presentation/README.md`:

```markdown
# 발표 자료 자산

최종 발표 HTML/PDF/PPTX에서 사용하는 이미지 자산입니다.

| 파일 | 용도 | 출처/생성 기준 |
|------|------|----------------|
| `final-title-thumbnail.png` | 최종 발표 1장 대표 이미지 | 실제 Streamlit 결과 화면 구조와 README 아키텍처 이미지를 참조한 발표용 생성 이미지 |

재사용 자산:

- `../readme/current-streamlit-onboarding.png`: 데모 흐름 슬라이드
- `../readme/current-streamlit-results.png`: 데모 흐름 슬라이드와 썸네일 참조
- `../readme/stock-agent-architecture.png`: 시스템 구성도 슬라이드

주의:

- 이미지 내부에는 API 키, 개인 정보, 실제 계좌 정보가 들어가면 안 됩니다.
- 발표용 이미지는 투자 권유처럼 보이는 문구를 포함하지 않습니다.
```

- [ ] **Step 2: Generate the title thumbnail**

Use image generation with this exact prompt:

```text
Create a polished 16:9 presentation hero image for a Korean stock analysis multi-agent system called stock-agent. The image should feel like a real fintech product screen, based on a Streamlit-style dashboard: central dashboard with candlestick chart, HOLD analysis signal, confidence gauge, portfolio suitability gauge, and small evidence panels. Around the dashboard, show four subtle analysis streams labeled only with short English labels: Quant, Qual, Peer, Macro. Add a small safety check layer at the bottom with a shield/check icon. Clean navy and white fintech palette with blue and teal accents. No people, no stock-photo look, no tiny unreadable paragraphs, no fake company logos, no investment advice language. Leave enough negative space for a slide title overlay on the left.
```

Save the result as:

```text
docs/assets/presentation/final-title-thumbnail.png
```

- [ ] **Step 3: Visual inspect the thumbnail**

Run:

```powershell
Test-Path docs\assets\presentation\final-title-thumbnail.png
```

Expected:

```text
True
```

Open the image and verify:

```text
- 16:9 landscape
- no API key or personal data
- no "BUY now" or direct investment advice
- labels are short and legible enough, or the slide can work without reading them
```

- [ ] **Step 4: Commit assets**

Run:

```powershell
git add docs/assets/presentation/README.md docs/assets/presentation/final-title-thumbnail.png
git commit -m "🎨 Style: 최종 발표 대표 이미지 자산 추가"
```

---

## Task 4: HTML Deck

**Files:**
- Create: `docs/presentation/final_presentation.html`

- [ ] **Step 1: Create the HTML deck**

Create `docs/presentation/final_presentation.html` as a self-contained deck that:

```text
- loads `final_presentation_source.json` content embedded as `window.DECK_SOURCE`
- uses 16:9 full viewport slides
- supports ArrowLeft, ArrowRight, Space, Home, End navigation
- shows slide count at bottom right
- uses a restrained navy finance theme
- uses local relative images from `../assets/...`
- prints one slide per page with `@media print`
```

The HTML must include these exact slide render rules:

```javascript
const renderers = {
  title: renderTitleSlide,
  metrics: renderMetricsSlide,
  problem: renderBulletsSlide,
  comparison: renderComparisonSlide,
  "agent-rationale": renderBulletsSlide,
  demo: renderDemoSlide,
  architecture: renderArchitectureSlide,
  flow: renderFlowSlide,
  "deep-dive": renderBulletsSlide,
  differentiation: renderBulletsSlide,
  validation: renderMetricsSlide,
  business: renderBulletsSlide,
  limits: renderBulletsSlide,
  team: renderTeamSlide
};
```

Use these design constants:

```css
:root {
  --bg: #07111f;
  --panel: #0f1b2e;
  --panel-2: #15233a;
  --text: #edf5ff;
  --muted: #90a4c3;
  --blue: #4f8ef7;
  --cyan: #27d3d0;
  --green: #34d399;
  --red: #fb7185;
  --amber: #f59e0b;
  --line: rgba(255,255,255,.12);
}
```

Use only these local image paths:

```text
../assets/presentation/final-title-thumbnail.png
../assets/readme/current-streamlit-onboarding.png
../assets/readme/current-streamlit-results.png
../assets/readme/stock-agent-architecture.png
```

- [ ] **Step 2: Check for external links and remote scripts**

Run:

```powershell
rg -n "https://|http://|cdn|fonts.googleapis|tailwind" docs\presentation\final_presentation.html
```

Expected: no output.

- [ ] **Step 3: Smoke-test the HTML in Chromium**

Run:

```powershell
node -e "const fs=require('fs'); const html=fs.readFileSync('docs/presentation/final_presentation.html','utf8'); console.log((html.match(/class=\"slide\"/g)||[]).length)"
```

Expected:

```text
14
```

- [ ] **Step 4: Commit HTML deck**

Run:

```powershell
git add docs/presentation/final_presentation.html
git commit -m "📝 Docs: 최종 발표 HTML 슬라이드 추가"
```

---

## Task 5: PDF Export

**Files:**
- Create: `docs/presentation/final_presentation.pdf`

- [ ] **Step 1: Export HTML to PDF with Playwright**

Run this one-off Node script from the repository root:

```powershell
@'
const { chromium } = require("playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const filePath = path.resolve("docs/presentation/final_presentation.html");
  await page.goto("file:///" + filePath.replace(/\\/g, "/"), { waitUntil: "networkidle" });
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: "docs/presentation/final_presentation.pdf",
    width: "16in",
    height: "9in",
    printBackground: true,
    margin: { top: "0in", right: "0in", bottom: "0in", left: "0in" }
  });
  await browser.close();
})();
'@ | node
```

Expected:

```text
docs/presentation/final_presentation.pdf exists and opens as 14 pages.
```

- [ ] **Step 2: Verify PDF exists and has non-trivial size**

Run:

```powershell
Get-Item docs\presentation\final_presentation.pdf | Select-Object FullName,Length
```

Expected: `Length` greater than `500000`.

- [ ] **Step 3: Commit PDF**

Run:

```powershell
git add docs/presentation/final_presentation.pdf
git commit -m "📝 Docs: 최종 발표 PDF 산출물 추가"
```

---

## Task 6: PPTX Build With Presentations Skill

**Files:**
- Create: `docs/presentation/final_presentation.pptx`
- Scratch only: `$TMP_DIR/final_presentation.mjs`
- Scratch only: `$TMP_DIR/preview/*`
- Scratch only: `$TMP_DIR/qa/*`

- [ ] **Step 1: Load bundled workspace dependencies**

Run the Codex app dependency loader before authoring the PPTX implementation.

Expected: paths for Node.js and document/presentation libraries are returned.

- [ ] **Step 2: Read required presentation tool docs**

Read these files before writing the PPTX builder:

```text
C:\Users\kik32\.codex\plugins\cache\openai-primary-runtime\presentations\26.623.12021\skills\presentations\artifact_tool\API_QUICK_START.md
C:\Users\kik32\.codex\plugins\cache\openai-primary-runtime\presentations\26.623.12021\skills\presentations\artifact_tool\api\API_DOCS.md
```

- [ ] **Step 3: Initialize artifact-tool workspace**

Set:

```powershell
$SKILL_DIR = "C:\Users\kik32\.codex\plugins\cache\openai-primary-runtime\presentations\26.623.12021\skills\presentations"
$WORKSPACE = Join-Path ([System.IO.Path]::GetTempPath()) "codex-presentations\final-presentation"
$TMP_DIR = Join-Path $WORKSPACE "tmp"
New-Item -ItemType Directory -Force $TMP_DIR | Out-Null
node "$SKILL_DIR\container_tools\setup_artifact_tool_workspace.mjs" --workspace "$TMP_DIR"
```

Expected: `node_modules/@oai/artifact-tool` is available under `$TMP_DIR`.

- [ ] **Step 4: Create PPTX builder**

Create `$TMP_DIR/final_presentation.mjs` that:

```text
- imports `@oai/artifact-tool`
- reads `docs/presentation/final_presentation_source.json`
- creates 16:9 slides
- uses the same 14 slide titles and key points as the HTML source
- embeds `final-title-thumbnail.png`, onboarding screenshot, result screenshot, and architecture image
- uses native table elements for slide 4, slide 11, and slide 14
- uses native shapes/connectors for slide 8 flow diagram
- exports to `docs/presentation/final_presentation.pptx`
```

Use these layout constraints:

```text
- Slide title font: 35pt or larger
- Body font: 18pt or larger
- No more than 5 bullet lines per slide
- No text box should overlap images or tables
- Every slide must include bottom-right page number `n / 14`
```

- [ ] **Step 5: Run PPTX builder**

Run:

```powershell
node "$TMP_DIR\final_presentation.mjs"
```

Expected:

```text
docs/presentation/final_presentation.pptx created
```

- [ ] **Step 6: Render and inspect PPTX previews**

Use the artifact-tool or bundled preview scripts available in the presentations skill to render the deck into `$TMP_DIR/preview`.

Expected inspection checklist:

```text
- 14 rendered slide previews
- no overlap warnings ignored
- slide 2 metric cards fit
- slide 4 comparison table is legible
- slide 8 flow diagram connectors do not cross labels
- slide 11 validation metrics show RAGAS 0.41 as a limitation, not a success
- slide 14 team role table fits without wrapping names into unreadable lines
```

- [ ] **Step 7: Commit PPTX**

Run:

```powershell
git add docs/presentation/final_presentation.pptx
git commit -m "📝 Docs: 최종 발표 PPTX 산출물 추가"
```

---

## Task 7: README And Index Update

**Files:**
- Modify: `docs/presentation/README.md`

- [ ] **Step 1: Update presentation README**

Replace `docs/presentation/README.md` with:

```markdown
# `docs/presentation/` - 발표 자료

> 프로젝트 시연과 중간·최종 발표에 사용하는 브라우저/PDF/PPTX 자료를 보관합니다.

## 최종 발표

| 파일 | 용도 |
|------|------|
| `final_presentation.html` | 브라우저 발표용 14장 HTML deck |
| `final_presentation.pdf` | 제출·백업용 PDF |
| `final_presentation.pptx` | 프로젝터 연결·편집용 PowerPoint |
| `final_presentation_source.json` | HTML/PPTX 공통 원천 슬라이드 텍스트 |

## 기존 자료

`midterm_presentation.html`은 중간 발표 시점의 시스템·성과·로드맵을 담은 HTML deck입니다.

## 관리 원칙

- 발표 자료의 수치에는 평가 리포트나 구현 문서 기준을 speaker note 또는 백업 자료로 남깁니다.
- 당시 상태를 보존하되 현재 구현처럼 오해되지 않도록 날짜를 표시합니다.
- 발표 전 브라우저 해상도와 로컬 asset 로딩을 확인합니다.
- 비밀값과 개인 데이터는 포함하지 않습니다.

[상위 문서 인덱스](../README.md)
```

- [ ] **Step 2: Commit README update**

Run:

```powershell
git add docs/presentation/README.md
git commit -m "📝 Docs: 최종 발표 자료 인덱스 갱신"
```

---

## Task 8: Final QA

**Files:**
- Verify: `docs/presentation/final_presentation.html`
- Verify: `docs/presentation/final_presentation.pdf`
- Verify: `docs/presentation/final_presentation.pptx`
- Verify: `docs/assets/presentation/final-title-thumbnail.png`

- [ ] **Step 1: Check presentation files**

Run:

```powershell
Get-Item docs\presentation\final_presentation.html,
         docs\presentation\final_presentation.pdf,
         docs\presentation\final_presentation.pptx,
         docs\assets\presentation\final-title-thumbnail.png |
  Select-Object FullName,Length
```

Expected:

```text
All four files exist.
HTML length > 20000.
PDF length > 500000.
PPTX length > 500000.
PNG length > 100000.
```

- [ ] **Step 2: Check for accidental secrets**

Run:

```powershell
rg -n "sk-|OPENAI_API_KEY|GLM_API_KEY|OPENROUTER_API_KEY|LANGFUSE_SECRET|password|secret" docs\presentation docs\assets\presentation
```

Expected: no output.

- [ ] **Step 3: Check HTML asset paths**

Run:

```powershell
rg -n "src=\"|url\\(" docs\presentation\final_presentation.html
```

Expected paths should only reference:

```text
../assets/presentation/final-title-thumbnail.png
../assets/readme/current-streamlit-onboarding.png
../assets/readme/current-streamlit-results.png
../assets/readme/stock-agent-architecture.png
```

- [ ] **Step 4: Open local HTML and PDF**

Open:

```text
C:\Users\kik32\workspace\stock-agent-project\docs\presentation\final_presentation.html
C:\Users\kik32\workspace\stock-agent-project\docs\presentation\final_presentation.pdf
```

Manual checklist:

```text
- Slide 1 title visual is not blank
- Slide 2 numbers are readable
- Slide 4 table fits
- Slide 6 screenshots are visible
- Slide 8 flow is understandable within 60 seconds
- Slide 11 clearly says RAGAS faithfulness is a limitation
- Slide 14 team roles fit
```

- [ ] **Step 5: Final git state**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## docs/final-presentation-design
?? .superpowers/
```

Only `.superpowers/` should remain untracked.

---

## Task 9: Push And PR

**Files:**
- Push branch: `docs/final-presentation-design`

- [ ] **Step 1: Push branch**

Run:

```powershell
git push -u origin docs/final-presentation-design
```

Expected: remote branch created or updated.

- [ ] **Step 2: Create PR**

Run:

```powershell
gh pr create --base main --head docs/final-presentation-design --title "📝 Docs: 최종 발표 자료 HTML/PDF/PPTX 추가" --body @"
## 요약

- 최종 발표 설계 스펙을 기반으로 14장 심사 설득형 발표 자료를 구성했습니다.
- `stock_agent_research.html`의 시장조사 자료를 3~4장으로 압축하고, 실제 구현·Agent 흐름·검증·상업성·한계를 보강했습니다.
- HTML deck, PDF, PPTX, 발표용 이미지 자산과 인덱스를 추가했습니다.

## 왜 했는지

- 6월 27일 최종 발표회에서 1조 stock-agent를 15분 안에 문제 정의부터 구현 증거까지 설득하기 위함입니다.
- 발표 요구사항인 문제 정의, Agent 활용 이점, Agent 흐름, 차별점, 상업성, 한계, 팀원 역할을 모두 포함합니다.

## 테스트

- HTML 14장 로컬 브라우저 확인
- PDF 14페이지 export 확인
- PPTX 14장 preview 확인
- 발표 자산 secret scan 확인

## 비고

- 발표 본문에는 출처를 크게 노출하지 않고, 수치의 기준 시점은 원천 JSON과 speaker note 성격의 메모에 남겼습니다.
- `.superpowers/` 브레인스토밍 임시 파일은 커밋하지 않았습니다.
"@
```

Expected: PR URL is printed.

---

## Self-Review

**Spec coverage:** This plan implements the approved design document: 14 slides, research compression, actual project implementation, Agent rationale, 11-node flow, validation, business potential, limitations, team roles, HTML/PDF/PPTX outputs.

**Completion marker scan:** The plan avoids unfinished markers and vague implementation directions. Each task states concrete files, commands, expected outputs, and content requirements.

**Type and path consistency:** All committed deliverables live under `docs/presentation/` or `docs/assets/presentation/`. Scratch files stay outside commit scope. The title asset path is consistently `docs/assets/presentation/final-title-thumbnail.png`.
