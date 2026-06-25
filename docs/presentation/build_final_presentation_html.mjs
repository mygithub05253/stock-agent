import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const sourcePath = path.join(__dirname, "final_presentation_source.json");
const outputPath = path.join(__dirname, "final_presentation.html");

const source = JSON.parse(await fs.readFile(sourcePath, "utf8"));

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function asset(value) {
  return esc(value.replace(/^docs\//, "../"));
}

function header(slide) {
  return `
    <header class="slide-header">
      <div>
        <div class="kicker">${esc(slide.kicker ?? source.meta.mode)}</div>
        <h2>${esc(slide.title)}</h2>
      </div>
      <div class="page">${String(slide.id).padStart(2, "0")}</div>
    </header>`;
}

function takeaway(slide) {
  if (!slide.takeaway) return "";
  return `<footer class="takeaway"><strong>Takeaway</strong><span>${esc(slide.takeaway)}</span></footer>`;
}

function bullets(items, className = "bullet-list") {
  return `<ul class="${className}">${(items ?? []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
}

function renderTitle(slide) {
  return `
  <section class="slide title-slide" data-slide="${slide.id}">
    <div class="title-copy">
      <div class="kicker">${esc(slide.kicker)}</div>
      <h1>${esc(slide.title)}</h1>
      <p>${esc(slide.headline)}</p>
      ${bullets(slide.bullets, "title-bullets")}
      <div class="date">${esc(source.meta.date)} · ${esc(source.meta.team)}</div>
    </div>
    <img class="title-image" src="${asset(slide.visual)}" alt="stock-agent 발표 썸네일">
  </section>`;
}

function renderTeam(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="team-grid">
      ${(slide.bullets ?? []).map((item, index) => {
        const [name, role] = item.split(": ");
        return `<article class="team-row accent-${index % 5}">
          <strong>${esc(name)}</strong>
          <span>${esc(role ?? "")}</span>
        </article>`;
      }).join("")}
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderMetrics(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="metric-grid">
      ${slide.metrics.map((metric, index) => `<article class="metric-card accent-${index}">
        <span>${esc(metric.label)}</span>
        <strong>${esc(metric.value)}</strong>
        <p>${esc(metric.caption)}</p>
      </article>`).join("")}
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderProblem(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="problem-stack">
      ${slide.bullets.map((item, index) => `<article class="problem-row accent-${index}">
        <b>${index + 1}</b>
        <p>${esc(item)}</p>
      </article>`).join("")}
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderComparison(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="table-wrap">
      <table>
        <thead><tr>${slide.columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead>
        <tbody>
          ${slide.rows.map((row) => `<tr>${row.map((cell) => `<td>${esc(cell)}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderCardList(slide, columns = 2) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="card-grid cols-${columns}">
      ${(slide.bullets ?? []).map((item, index) => `<article class="info-card accent-${index % 5}">
        <b>${index + 1}</b>
        <p>${esc(item)}</p>
      </article>`).join("")}
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderArchitecture(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="split-layout">
      <div class="text-stack">${(slide.bullets ?? []).map((item, index) => `<article class="small-card accent-${index}">
        ${esc(item)}
      </article>`).join("")}</div>
      <img class="architecture-image" src="${asset(slide.visual)}" alt="stock-agent 시스템 구성도">
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderFlow(slide) {
  const workers = ["Quant", "Qual", "Competitor", "Macro"];
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="pipeline">
      <div class="flow-line top"><span>Curator</span><i>→</i><span>Classifier</span></div>
      <div class="worker-row">${workers.map((worker) => `<span>${worker}</span>`).join("")}</div>
      <div class="flow-line bottom"><span>Strategist</span><i>→</i><span>InvestmentAnalyst</span><i>→</i><span>Guardrail</span><i>→</i><span>GuardrailApply</span><i>→</i><span>ResultRenderer</span></div>
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderAgentDetail(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="agent-layout">
      <p class="summary">${esc(slide.summary)}</p>
      <div class="agent-flow">
        ${slide.flow.map((step, index) => `<article class="flow-step accent-${index % 5}">
          <b>${String(index + 1).padStart(2, "0")}</b>
          <p>${esc(step)}</p>
        </article>`).join("")}
      </div>
      <div class="agent-cards">
        ${slide.cards.map((card, index) => `<article class="agent-card accent-${index}">
          <strong>${esc(card.label)}</strong>
          <span>${esc(card.text)}</span>
        </article>`).join("")}
      </div>
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderQualRag(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="qual-layout">
      <p class="summary">${esc(slide.summary)}</p>
      <div class="qual-flow">
        ${slide.flow.map((step, index) => {
          const [head, ...rest] = step.split(": ");
          return `<article class="flow-step accent-${index % 5}">
            <b>${String(index + 1).padStart(2, "0")}</b>
            <strong>${esc(head)}</strong>
            <p>${esc(rest.join(": "))}</p>
          </article>`;
        }).join("")}
      </div>
      <div class="agent-cards">
        ${slide.cards.map((card, index) => `<article class="agent-card accent-${index}">
          <strong>${esc(card.label)}</strong>
          <span>${esc(card.text)}</span>
        </article>`).join("")}
      </div>
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderDemoVideo(slide) {
  return `
  <section class="slide" data-slide="${slide.id}">
    ${header(slide)}
    <main class="demo-video-layout">
      <div class="video-poster">
        <img src="${asset(slide.visuals[0])}" alt="온보딩 화면">
        <img src="${asset(slide.visuals[1])}" alt="결과 화면">
        <div class="play-badge">▶ DEMO VIDEO</div>
      </div>
      <div class="demo-cue-list">${slide.bullets.map((item) => `<article>${esc(item)}</article>`).join("")}</div>
    </main>
    ${takeaway(slide)}
  </section>`;
}

function renderSlide(slide) {
  switch (slide.kind) {
    case "title":
      return renderTitle(slide);
    case "team":
      return renderTeam(slide);
    case "metrics":
      return renderMetrics(slide);
    case "problem":
      return renderProblem(slide);
    case "comparison":
      return renderComparison(slide);
    case "architecture":
      return renderArchitecture(slide);
    case "flow":
      return renderFlow(slide);
    case "agent-detail":
      return renderAgentDetail(slide);
    case "qual-rag":
      return renderQualRag(slide);
    case "demo-video":
      return renderDemoVideo(slide);
    case "agent-rationale":
    case "differentiation":
    case "business":
    case "closing":
      return renderCardList(slide, slide.bullets.length > 4 ? 1 : 2);
    default:
      throw new Error(`Unsupported slide kind: ${slide.kind}`);
  }
}

const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(source.meta.title)}</title>
<style>
:root {
  --bg: #07111f;
  --panel: #0f1b2e;
  --panel-2: #16243a;
  --text: #edf5ff;
  --muted: #93a4c4;
  --subtle: #64748b;
  --line: #263b5e;
  --blue: #4f8ef7;
  --cyan: #27d3d0;
  --green: #34d399;
  --amber: #f59e0b;
  --red: #fb7185;
}
* { box-sizing: border-box; }
html, body { margin: 0; width: 100%; height: 100%; background: var(--bg); color: var(--text); }
body { font-family: "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif; overflow: hidden; }
.deck { width: 100vw; height: 100vh; position: relative; }
.slide {
  position: absolute;
  inset: 0;
  width: 100vw;
  height: 100vh;
  padding: 4.8vh 5.6vw 6vh;
  display: none;
  background:
    linear-gradient(180deg, rgba(79,142,247,.95) 0 1.1vh, transparent 1.1vh),
    radial-gradient(circle at 88% 10%, rgba(39,211,208,.13), transparent 25vh),
    var(--bg);
}
.slide.active { display: block; }
.slide-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; margin-bottom: 3.2vh; }
.kicker {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 5px 16px;
  border: 1px solid rgba(39,211,208,.75);
  border-radius: 999px;
  color: var(--cyan);
  font-weight: 800;
  font-size: 15px;
  line-height: 1;
}
h1, h2, p { margin: 0; letter-spacing: 0; }
h2 { margin-top: 14px; font-size: clamp(30px, 3vw, 43px); line-height: 1.08; }
.page { color: var(--subtle); font-size: 17px; margin-top: 18px; }
.title-slide { display: none; grid-template-columns: 1fr .95fr; gap: 4vw; align-items: center; }
.title-slide.active { display: grid; }
.title-copy h1 { margin: 42px 0 18px; font-size: clamp(64px, 7vw, 96px); line-height: .9; }
.title-copy > p { max-width: 680px; color: #d8e5f7; font-size: 31px; line-height: 1.34; }
.title-bullets { list-style: none; padding: 0; margin: 46px 0 0; display: grid; gap: 18px; font-size: 23px; }
.title-bullets li::before { content: ""; display: inline-block; width: 18px; height: 18px; border-radius: 50%; background: var(--cyan); margin-right: 16px; vertical-align: -1px; }
.title-image { width: 100%; height: 76vh; object-fit: cover; border-radius: 24px; border: 1px solid rgba(79,142,247,.28); }
.date { margin-top: 52px; color: var(--muted); font-size: 18px; }
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 8vh; }
.metric-card, .info-card, .small-card, .agent-card, .flow-step, .problem-row, .team-row, .demo-cue-list article {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
}
.metric-card { min-height: 240px; padding: 28px; border-top-width: 8px; }
.metric-card span { color: var(--muted); font-weight: 800; font-size: 18px; }
.metric-card strong { display: block; margin: 30px 0 18px; color: var(--cyan); font-size: 54px; line-height: 1; }
.metric-card p { color: #bfd0e6; font-size: 19px; line-height: 1.35; }
.problem-stack, .team-grid { display: grid; gap: 18px; }
.problem-row { display: grid; grid-template-columns: 58px 1fr; gap: 24px; align-items: center; padding: 24px 28px; }
.problem-row b { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 50%; background: var(--cyan); color: var(--bg); font-size: 22px; }
.problem-row p, .team-row span { font-size: 23px; line-height: 1.36; color: var(--text); }
.table-wrap { margin-top: 2vh; }
table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 14px; font-size: 19px; }
th, td { border: 1px solid rgba(148,163,184,.2); padding: 16px 14px; text-align: left; vertical-align: top; }
th { background: #10233b; color: var(--cyan); }
td { background: rgba(15,27,46,.92); }
tbody tr:last-child td { background: rgba(39,211,208,.12); font-weight: 800; }
.card-grid { display: grid; gap: 16px; }
.card-grid.cols-2 { grid-template-columns: 1fr 1fr; }
.card-grid.cols-1 { grid-template-columns: 1fr; }
.info-card { display: grid; grid-template-columns: 42px 1fr; gap: 18px; align-items: center; min-height: 72px; padding: 16px 24px; }
.info-card b { color: var(--cyan); font-size: 22px; }
.info-card p, .small-card, .agent-card span, .flow-step p, .flow-step strong { color: var(--text); font-size: 21px; line-height: 1.3; }
.team-row { display: grid; grid-template-columns: 190px 1fr; gap: 22px; align-items: center; min-height: 70px; padding: 20px 26px; }
.team-row strong, .agent-card strong { color: var(--cyan); font-size: 23px; }
.split-layout { display: grid; grid-template-columns: .72fr 1.18fr; gap: 28px; align-items: start; }
.text-stack { display: grid; gap: 18px; }
.small-card { min-height: 82px; padding: 20px 24px; }
.architecture-image { width: 100%; height: 51vh; object-fit: contain; background: #fff; border-radius: 18px; border: 1px solid var(--line); }
.pipeline { display: grid; gap: 38px; margin-top: 6vh; }
.flow-line, .worker-row { display: flex; gap: 14px; justify-content: center; align-items: center; }
.flow-line span, .worker-row span { min-width: 150px; padding: 20px 22px; text-align: center; border: 1px solid var(--cyan); border-radius: 16px; background: var(--panel); font-weight: 800; font-size: 20px; }
.flow-line i { color: #5f7f9e; font-style: normal; font-size: 28px; }
.worker-row span { border-color: rgba(79,142,247,.75); min-width: 190px; }
.agent-layout, .qual-layout { display: grid; gap: 24px; }
.summary { color: var(--muted); font-size: 22px; line-height: 1.38; max-width: 1120px; }
.agent-flow, .qual-flow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.qual-flow { grid-template-columns: repeat(5, 1fr); }
.flow-step { min-height: 150px; padding: 20px; border-top-width: 6px; }
.flow-step b { display: block; color: var(--cyan); font-size: 18px; margin-bottom: 16px; }
.flow-step strong { display: block; color: var(--cyan); font-weight: 800; margin-bottom: 10px; }
.flow-step p { font-size: 17px; }
.agent-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.agent-card { min-height: 116px; padding: 20px 24px; }
.agent-card strong { display: block; margin-bottom: 14px; }
.agent-card span { font-size: 18px; color: #dce9fa; }
.demo-video-layout { display: grid; grid-template-columns: 1.1fr .75fr; gap: 36px; align-items: start; }
.video-poster { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 24px; min-height: 390px; background: #06172a; border: 1px solid #275078; border-radius: 24px; }
.video-poster img { width: 100%; height: 300px; object-fit: cover; border-radius: 16px; border: 1px solid rgba(255,255,255,.12); }
.play-badge { position: absolute; left: 50%; bottom: 32px; transform: translateX(-50%); padding: 14px 28px; border: 1px solid var(--cyan); border-radius: 999px; background: #0b2a35; color: var(--cyan); font-weight: 900; }
.demo-cue-list { display: grid; gap: 16px; }
.demo-cue-list article { min-height: 72px; padding: 18px 22px; color: var(--text); font-size: 20px; line-height: 1.3; }
.takeaway { position: absolute; left: 5.6vw; right: 5.6vw; bottom: 5.2vh; min-height: 58px; display: grid; grid-template-columns: 120px 1fr; align-items: center; gap: 18px; padding: 14px 24px; border: 1px solid #234663; border-radius: 16px; background: #0b2034; }
.takeaway strong { color: var(--cyan); }
.takeaway span { color: var(--text); font-size: 21px; line-height: 1.25; }
.accent-0 { border-color: rgba(79,142,247,.58); }
.accent-1 { border-color: rgba(39,211,208,.58); }
.accent-2 { border-color: rgba(52,211,153,.58); }
.accent-3 { border-color: rgba(245,158,11,.58); }
.accent-4 { border-color: rgba(251,113,133,.58); }
@page { size: 16in 9in; margin: 0; }
@media print {
  html, body { width: 16in; height: 9in; overflow: visible; }
  .deck { width: 16in; height: auto; }
  .slide { position: relative; display: block !important; width: 16in; height: 9in; page-break-after: always; padding: .76in .9in .74in; }
  .title-slide { display: grid !important; }
  .slide:last-child { page-break-after: auto; }
}
</style>
</head>
<body>
<div class="deck">
${source.slides.map(renderSlide).join("\n")}
</div>
<script>
const slides = Array.from(document.querySelectorAll('.slide'));
let index = 0;
function show(next) {
  index = Math.max(0, Math.min(slides.length - 1, next));
  slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowRight' || event.key === ' ') show(index + 1);
  if (event.key === 'ArrowLeft') show(index - 1);
  if (event.key === 'Home') show(0);
  if (event.key === 'End') show(slides.length - 1);
});
show(0);
</script>
</body>
</html>
`;

await fs.writeFile(outputPath, html, "utf8");
console.log(`Created ${outputPath}`);
