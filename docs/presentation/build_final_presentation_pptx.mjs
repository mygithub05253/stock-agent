import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(__dirname, "final_presentation_source.json");
const outputPath = path.join(__dirname, "final_presentation.pptx");
const previewDir = path.join(repoRoot, "tmp", "presentation-pptx-preview");
const shouldRenderPreview = process.argv.includes("--preview");

function runtimeNodeModules() {
  const home = process.env.HOME || process.env.USERPROFILE || process.cwd();
  return path.join(
    home,
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
  );
}

function artifactToolEntrypoint() {
  const packageDir =
    process.env.ARTIFACT_TOOL_PACKAGE ||
    path.join(runtimeNodeModules(), "@oai", "artifact-tool");
  const candidates = [
    path.join(packageDir, "dist", "node", "artifact_tool.mjs"),
    path.join(packageDir, "dist", "artifact_tool.mjs"),
  ];
  const entrypoint = candidates.find((candidate) => fsSync.existsSync(candidate));
  if (!entrypoint) {
    throw new Error(`Unable to find @oai/artifact-tool entrypoint in ${packageDir}`);
  }
  return entrypoint;
}

const { Presentation, PresentationFile, fr, fixed } = await import(
  pathToFileURL(artifactToolEntrypoint()).href
);

const W = 1280;
const H = 720;
const FONT = "Malgun Gothic";
const MONO = "Consolas";
const BG = "#07111f";
const PANEL = "#0f1b2e";
const PANEL_2 = "#16243a";
const PANEL_3 = "#20314f";
const TEXT = "#edf5ff";
const MUTED = "#93a4c4";
const SUBTLE = "#64748b";
const BORDER = "#263b5e";
const BLUE = "#4f8ef7";
const CYAN = "#27d3d0";
const GREEN = "#34d399";
const AMBER = "#f59e0b";
const RED = "#fb7185";
const TRANSPARENT = "#00000000";
const NO_LINE = { style: "solid", fill: TRANSPARENT, width: 0 };

const source = JSON.parse(await fs.readFile(sourcePath, "utf8"));

function assetPath(value) {
  return path.join(repoRoot, value.replaceAll("/", path.sep));
}

async function readImageBytes(value) {
  const imagePath = assetPath(value);
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function saveBlob(output, blob) {
  await fs.mkdir(path.dirname(output), { recursive: true });
  await fs.writeFile(output, Buffer.from(await blob.arrayBuffer()));
}

function addText(slide, value, position, style = {}, name = "text") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: TRANSPARENT,
    line: NO_LINE,
  });
  shape.text = String(value ?? "");
  shape.text.style = {
    typeface: FONT,
    fontSize: 22,
    color: TEXT,
    lineSpacing: 1.08,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
    ...style,
  };
  return shape;
}

function addRound(slide, position, options = {}) {
  return slide.shapes.add({
    geometry: "roundRect",
    name: options.name ?? "surface",
    position,
    fill: options.fill ?? PANEL,
    line: options.line ?? { style: "solid", fill: options.lineFill ?? BORDER, width: options.lineWidth ?? 1 },
    borderRadius: options.borderRadius ?? 16,
    shadow: options.shadow,
  });
}

function addPill(slide, label, position, color = CYAN) {
  const pill = addRound(slide, position, {
    fill: "#0d2437",
    lineFill: color,
    lineWidth: 1,
    borderRadius: "rounded-full",
  });
  pill.text = label;
  pill.text.style = {
    typeface: FONT,
    fontSize: 14,
    bold: true,
    color,
    alignment: "center",
    insets: { top: 4, right: 12, bottom: 4, left: 12 },
  };
  return pill;
}

function addBase(slide, data) {
  slide.background.fill = BG;
  slide.shapes.add({
    geometry: "rect",
    name: "top-accent",
    position: { left: 0, top: 0, width: W, height: 8 },
    fill: BLUE,
    line: NO_LINE,
  });
  slide.shapes.add({
    geometry: "rect",
    name: "bottom-line",
    position: { left: 72, top: 646, width: 1136, height: 1 },
    fill: BORDER,
    line: NO_LINE,
  });
  addPill(slide, source.meta.team, { left: 72, top: 34, width: 220, height: 30 }, CYAN);
  addText(slide, String(data.id).padStart(2, "0"), { left: 1158, top: 662, width: 54, height: 24 }, {
    fontSize: 16,
    color: SUBTLE,
    alignment: "right",
  });
}

function addSlideTitle(slide, data, subtitle) {
  addText(slide, data.title, { left: 72, top: 70, width: 1000, height: 64 }, {
    fontSize: 36,
    bold: true,
    color: TEXT,
    lineSpacing: 0.96,
  });
  if (subtitle) {
    addText(slide, subtitle, { left: 74, top: 122, width: 980, height: 32 }, {
      fontSize: 18,
      color: MUTED,
    });
  }
}

function addTakeaway(slide, value, top = 566) {
  if (!value) return;
  addRound(slide, { left: 72, top, width: 1136, height: 58 }, {
    fill: "#0b2034",
    lineFill: "#234663",
    borderRadius: 14,
  });
  addText(slide, "Takeaway", { left: 98, top: top + 17, width: 110, height: 24 }, {
    fontSize: 16,
    bold: true,
    color: CYAN,
  });
  addText(slide, value, { left: 218, top: top + 13, width: 958, height: 34 }, {
    fontSize: 20,
    color: TEXT,
    lineSpacing: 1,
  });
}

function cardText(slide, body, position, options = {}) {
  const card = addRound(slide, position, {
    fill: options.fill ?? PANEL,
    lineFill: options.lineFill ?? BORDER,
    borderRadius: options.borderRadius ?? 16,
  });
  card.text = body;
  card.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 22,
    color: options.color ?? TEXT,
    bold: options.bold,
    lineSpacing: options.lineSpacing ?? 1.12,
    insets: options.insets ?? { top: 18, right: 22, bottom: 16, left: 22 },
  };
  return card;
}

function renderTitle(data) {
  const slide = presentation.slides.add();
  slide.background.fill = BG;
  slide.shapes.add({
    geometry: "rect",
    name: "left-band",
    position: { left: 0, top: 0, width: 18, height: H },
    fill: CYAN,
    line: NO_LINE,
  });
  addPill(slide, `${source.meta.team} final`, { left: 72, top: 54, width: 258, height: 32 }, CYAN);
  addText(slide, data.title, { left: 72, top: 148, width: 520, height: 86 }, {
    fontSize: 70,
    bold: true,
    color: TEXT,
    lineSpacing: 0.9,
  });
  addText(slide, data.headline, { left: 76, top: 246, width: 540, height: 98 }, {
    fontSize: 28,
    color: "#d8e5f7",
    lineSpacing: 1.08,
  });
  data.bullets.forEach((bullet, index) => {
    const top = 382 + index * 54;
    addRound(slide, { left: 78, top, width: 30, height: 30 }, {
      fill: [BLUE, CYAN, GREEN][index],
      line: NO_LINE,
      borderRadius: "rounded-full",
    });
    addText(slide, bullet, { left: 124, top: top + 1, width: 492, height: 34 }, {
      fontSize: 20,
      color: TEXT,
    });
  });
  addText(slide, source.meta.date, { left: 78, top: 626, width: 240, height: 30 }, {
    fontSize: 18,
    color: MUTED,
  });
  const visualPath = data.visual;
  slide.images.add({
    blob: awaitImage(visualPath),
    contentType: "image/png",
    alt: "stock-agent presentation thumbnail",
    fit: "cover",
    geometry: "roundRect",
    borderRadius: 24,
    position: { left: 660, top: 54, width: 548, height: 612 },
  });
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function addMetricCard(slide, metric, position, index, isRisk = false) {
  const accent = isRisk ? RED : [BLUE, CYAN, GREEN, AMBER][index % 4];
  addRound(slide, position, {
    fill: PANEL,
    lineFill: "#25496d",
    borderRadius: 18,
  });
  slide.shapes.add({
    geometry: "rect",
    name: "metric-accent",
    position: { left: position.left, top: position.top, width: position.width, height: 7 },
    fill: accent,
    line: NO_LINE,
  });
  addText(slide, metric.label, { left: position.left + 24, top: position.top + 24, width: position.width - 48, height: 28 }, {
    fontSize: 17,
    bold: true,
    color: MUTED,
  });
  addText(slide, metric.value, { left: position.left + 24, top: position.top + 66, width: position.width - 48, height: 58 }, {
    fontSize: metric.value.length > 8 ? 38 : 48,
    bold: true,
    color: accent,
    lineSpacing: 0.95,
  });
  addText(slide, metric.caption, { left: position.left + 24, top: position.top + 132, width: position.width - 48, height: 42 }, {
    fontSize: 17,
    color: "#b8c8df",
    lineSpacing: 1.05,
  });
}

function renderMetrics(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, data.id === 11 ? "검증 결과를 장점과 한계로 동시에 공개" : "시장 확대와 판단 복잡도 상승을 한 장에 압축");
  const count = data.metrics.length;
  const gap = 20;
  const width = (1136 - gap * (count - 1)) / count;
  data.metrics.forEach((metric, index) => {
    addMetricCard(slide, metric, { left: 72 + index * (width + gap), top: 176, width, height: 214 }, index, data.id === 11 && index === 3);
  });
  if (data.id === 11) {
    cardText(
      slide,
      "검증 신호\nRule checks 40/41, Competitor 6/6, Qual RAG hit@5 1.0",
      { left: 72, top: 420, width: 548, height: 112 },
      { fill: "#101f35", fontSize: 20, lineSpacing: 1.08 },
    );
    cardText(
      slide,
      "공개 한계\nRAGAS faithfulness 0.41은 생성 근거 반영 개선 과제",
      { left: 640, top: 420, width: 568, height: 112 },
      { fill: "#171c31", fontSize: 20, lineSpacing: 1.08 },
    );
    addTakeaway(slide, data.takeaway, 568);
  } else {
    addTakeaway(slide, data.takeaway, 488);
  }
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderProblem(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "정보 과잉, 모바일 즉시성, 낮은 맥락화가 함께 만든 의사결정 공백");
  data.bullets.forEach((bullet, index) => {
    const top = 166 + index * 112;
    addRound(slide, { left: 72, top, width: 1136, height: 88 }, {
      fill: index === 1 ? PANEL_2 : PANEL,
      lineFill: "#284867",
      borderRadius: 18,
    });
    addRound(slide, { left: 96, top: top + 22, width: 46, height: 46 }, {
      fill: [BLUE, AMBER, RED][index],
      line: NO_LINE,
      borderRadius: "rounded-full",
    });
    addText(slide, String(index + 1), { left: 96, top: top + 29, width: 46, height: 28 }, {
      fontSize: 20,
      bold: true,
      color: BG,
      alignment: "center",
    });
    addText(slide, bullet, { left: 166, top: top + 18, width: 990, height: 54 }, {
      fontSize: 22,
      color: TEXT,
      lineSpacing: 1.08,
    });
  });
  addTakeaway(slide, data.takeaway, 540);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderComparison(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "각 대안은 강점이 있지만 세 공백을 동시에 닫지는 못함");
  const values = [data.columns, ...data.rows];
  const table = slide.tables.add({
    rows: values.length,
    columns: data.columns.length,
    left: 72,
    top: 164,
    width: 1136,
    height: 326,
    columnTracks: [fixed(178), fixed(142), fixed(142), fixed(142), fr(1)],
    values,
  });
  table.borders.assign({ style: "solid", fill: BORDER, width: 1 });
  for (let row = 0; row < values.length; row += 1) {
    for (let col = 0; col < data.columns.length; col += 1) {
      const cell = table.getCell(row, col);
      cell.fill = row === 0 ? "#10233b" : row === values.length - 1 ? "#0b2a35" : row % 2 ? PANEL : PANEL_2;
      cell.text.style = {
        typeface: FONT,
        fontSize: col === 4 ? 16 : 18,
        color: row === 0 ? CYAN : TEXT,
        bold: row === 0 || row === values.length - 1,
        alignment: col > 0 && col < 4 ? "center" : "left",
      };
    }
  }
  addTakeaway(slide, data.takeaway, 532);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderCardGrid(data, options = {}) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, options.subtitle);
  const bullets = data.bullets ?? [];
  const columns = options.columns ?? 2;
  const gap = options.gap ?? 18;
  const top = options.top ?? 166;
  const cardHeight = options.cardHeight ?? (columns === 1 ? 66 : 132);
  const width = (1136 - gap * (columns - 1)) / columns;
  bullets.forEach((bullet, index) => {
    const col = index % columns;
    const row = Math.floor(index / columns);
    const left = 72 + col * (width + gap);
    const y = top + row * (cardHeight + gap);
    const accent = [BLUE, CYAN, GREEN, AMBER, RED][index % 5];
    addRound(slide, { left, top: y, width, height: cardHeight }, {
      fill: options.fill ?? PANEL,
      lineFill: "#294967",
      borderRadius: 18,
    });
    addRound(slide, { left: left + 18, top: y + 18, width: 34, height: 34 }, {
      fill: accent,
      line: NO_LINE,
      borderRadius: "rounded-full",
    });
    addText(slide, String(index + 1), { left: left + 18, top: y + 24, width: 34, height: 20 }, {
      fontSize: 16,
      bold: true,
      color: BG,
      alignment: "center",
    });
    addText(slide, bullet, { left: left + 66, top: y + 17, width: width - 86, height: cardHeight - 28 }, {
      fontSize: options.fontSize ?? 21,
      color: TEXT,
      lineSpacing: 1.08,
    });
  });
  addTakeaway(slide, data.takeaway, options.takeawayTop ?? 548);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderDemo(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "입력부터 결과까지 발표 중 바로 보여줄 수 있는 사용자 여정");
  data.bullets.forEach((bullet, index) => {
    cardText(slide, bullet, { left: 72, top: 164 + index * 82, width: 422, height: 62 }, {
      fill: index % 2 ? PANEL_2 : PANEL,
      fontSize: 19,
      insets: { top: 14, right: 18, bottom: 12, left: 18 },
    });
  });
  const first = data.visuals[0];
  const second = data.visuals[1];
  slide.images.add({
    blob: awaitImage(first),
    contentType: "image/png",
    alt: "Streamlit onboarding screen",
    fit: "contain",
    geometry: "roundRect",
    borderRadius: 18,
    position: { left: 526, top: 162, width: 320, height: 360 },
  });
  slide.images.add({
    blob: awaitImage(second),
    contentType: "image/png",
    alt: "Streamlit result screen",
    fit: "contain",
    geometry: "roundRect",
    borderRadius: 18,
    position: { left: 868, top: 162, width: 340, height: 360 },
  });
  addTakeaway(slide, "라이브 데모가 막혀도 같은 화면 흐름으로 설명 가능한 백업 슬라이드", 558);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderArchitecture(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "README의 실제 구성도를 발표용으로 재사용");
  data.bullets.forEach((bullet, index) => {
    cardText(slide, bullet, { left: 72, top: 162 + index * 88, width: 438, height: 68 }, {
      fill: index % 2 ? PANEL_2 : PANEL,
      fontSize: 19,
      insets: { top: 14, right: 18, bottom: 12, left: 18 },
    });
  });
  slide.images.add({
    blob: awaitImage(data.visual),
    contentType: "image/png",
    alt: "stock-agent system architecture",
    fit: "contain",
    geometry: "roundRect",
    borderRadius: 18,
    position: { left: 538, top: 154, width: 670, height: 394 },
  });
  addTakeaway(slide, "LangGraph가 worker Agent를 분리하고 DB/RAG/Guardrail이 근거와 안전성을 보완", 572);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function addNode(slide, label, left, top, width, accent = BLUE) {
  addRound(slide, { left, top, width, height: 54 }, {
    fill: PANEL,
    lineFill: accent,
    borderRadius: 16,
  });
  addText(slide, label, { left: left + 10, top: top + 15, width: width - 20, height: 24 }, {
    fontSize: label.length > 14 ? 16 : 18,
    bold: true,
    color: TEXT,
    alignment: "center",
  });
}

function addArrow(slide, left, top, width, height = 18, color = "#476985") {
  slide.shapes.add({
    geometry: "rightArrow",
    position: { left, top, width, height },
    fill: color,
    line: NO_LINE,
  });
}

function renderFlow(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "Classifier 이후 필요한 worker를 fan-out하고 Strategist에서 join");
  addNode(slide, "Curator", 92, 172, 150, BLUE);
  addArrow(slide, 250, 190, 54);
  addNode(slide, "Classifier", 314, 172, 158, CYAN);
  const workers = ["Quant", "Qual", "Competitor", "Macro"];
  workers.forEach((node, index) => {
    const left = 124 + index * 258;
    addRound(slide, { left, top: 286, width: 194, height: 72 }, {
      fill: "#10233b",
      lineFill: [BLUE, CYAN, GREEN, AMBER][index],
      borderRadius: 18,
    });
    addText(slide, node, { left: left + 14, top: 308, width: 166, height: 26 }, {
      fontSize: 20,
      bold: true,
      color: TEXT,
      alignment: "center",
    });
  });
  addText(slide, "parallel worker Agents", { left: 482, top: 246, width: 316, height: 28 }, {
    fontSize: 18,
    color: MUTED,
    alignment: "center",
  });
  slide.shapes.add({
    geometry: "line",
    position: { left: 392, top: 226, width: 0, height: 48 },
    line: { style: "solid", fill: BORDER, width: 2 },
    fill: TRANSPARENT,
  });
  workers.forEach((_, index) => {
    slide.shapes.add({
      geometry: "line",
      position: { left: 221 + index * 258, top: 260, width: 171 - index * 2, height: 0 },
      line: { style: "solid", fill: BORDER, width: 2 },
      fill: TRANSPARENT,
    });
  });
  addNode(slide, "Strategist", 486, 426, 170, GREEN);
  slide.shapes.add({
    geometry: "line",
    position: { left: 574, top: 372, width: 0, height: 42 },
    line: { style: "solid", fill: BORDER, width: 2 },
    fill: TRANSPARENT,
  });
  addArrow(slide, 666, 444, 54);
  addNode(slide, "InvestmentAnalyst", 730, 426, 220, BLUE);
  addArrow(slide, 962, 444, 46);
  addNode(slide, "Guardrail", 1016, 426, 144, RED);
  addNode(slide, "GuardrailApply", 416, 526, 198, RED);
  addArrow(slide, 624, 544, 50);
  addNode(slide, "ResultRenderer", 686, 526, 202, CYAN);
  addTakeaway(slide, data.takeaway, 616);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderDeepDive(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "Agent의 실패 책임 범위를 나누고 검증 지점을 명확히 함");
  const cards = data.bullets.map((bullet) => {
    const [head, ...rest] = bullet.split(": ");
    return { head, body: rest.join(": ") || bullet };
  });
  cards.forEach((card, index) => {
    const left = 72 + index * 386;
    const accent = [BLUE, CYAN, RED][index];
    addRound(slide, { left, top: 168, width: 350, height: 282 }, {
      fill: PANEL,
      lineFill: accent,
      borderRadius: 20,
    });
    addText(slide, card.head, { left: left + 24, top: 196, width: 302, height: 36 }, {
      fontSize: 25,
      bold: true,
      color: accent,
    });
    addText(slide, card.body, { left: left + 24, top: 254, width: 302, height: 132 }, {
      fontSize: 22,
      color: TEXT,
      lineSpacing: 1.12,
    });
    addPill(slide, ["근거", "검색", "안전"][index], { left: left + 24, top: 398, width: 86, height: 30 }, accent);
  });
  addTakeaway(slide, data.takeaway, 534);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

function renderTeam(data) {
  const slide = presentation.slides.add();
  addBase(slide, data);
  addSlideTitle(slide, data, "PR/README 기반 역할 요약과 마지막 메시지");
  data.bullets.forEach((bullet, index) => {
    const [name, role] = bullet.split(": ");
    const top = 156 + index * 72;
    addRound(slide, { left: 72, top, width: 1136, height: 56 }, {
      fill: index % 2 ? PANEL_2 : PANEL,
      lineFill: "#294967",
      borderRadius: 16,
    });
    addText(slide, name, { left: 102, top: top + 15, width: 180, height: 26 }, {
      fontSize: 20,
      bold: true,
      color: [BLUE, CYAN, GREEN, AMBER, RED][index % 5],
    });
    addText(slide, role ?? "", { left: 292, top: top + 14, width: 872, height: 28 }, {
      fontSize: 20,
      color: TEXT,
    });
  });
  addTakeaway(slide, data.takeaway, 548);
  slide.speakerNotes.textFrame.setText(data.speakerNote ?? "");
}

const imageCache = new Map();
function awaitImage(value) {
  if (!imageCache.has(value)) {
    const imagePath = assetPath(value);
    if (!fsSync.existsSync(imagePath)) {
      throw new Error(`Missing image asset: ${imagePath}`);
    }
    const bytes = fsSync.readFileSync(imagePath);
    imageCache.set(value, bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
  }
  return imageCache.get(value);
}

const presentation = Presentation.create({
  slideSize: { width: W, height: H },
});

for (const slideData of source.slides) {
  switch (slideData.kind) {
    case "title":
      renderTitle(slideData);
      break;
    case "metrics":
    case "validation":
      renderMetrics(slideData);
      break;
    case "problem":
      renderProblem(slideData);
      break;
    case "comparison":
      renderComparison(slideData);
      break;
    case "agent-rationale":
      renderCardGrid(slideData, {
        columns: 2,
        cardHeight: 132,
        subtitle: "LLM 하나가 아니라 역할 분리, 근거 통합, 안전검증을 분리",
        takeawayTop: 546,
      });
      break;
    case "demo":
      renderDemo(slideData);
      break;
    case "architecture":
      renderArchitecture(slideData);
      break;
    case "flow":
      renderFlow(slideData);
      break;
    case "deep-dive":
      renderDeepDive(slideData);
      break;
    case "differentiation":
      renderCardGrid(slideData, {
        columns: 2,
        cardHeight: 132,
        subtitle: "기능 나열보다 평가 가능성과 실패 대응이 차별점",
        takeawayTop: 546,
      });
      break;
    case "business":
      renderCardGrid(slideData, {
        columns: 2,
        cardHeight: 120,
        subtitle: "추천 서비스가 아니라 설명 가능한 분석 보조 모듈",
        takeawayTop: 542,
      });
      break;
    case "limits":
      renderCardGrid(slideData, {
        columns: 2,
        cardHeight: 120,
        subtitle: "한계를 숨기지 않고 다음 개선 과제로 연결",
        takeawayTop: 542,
      });
      break;
    case "team":
      renderTeam(slideData);
      break;
    default:
      throw new Error(`Unknown slide kind: ${slideData.kind}`);
  }
}

if (shouldRenderPreview) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await saveBlob(path.join(previewDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(
      path.join(previewDir, `${stem}.layout.json`),
      await (await slide.export({ format: "layout" })).text(),
      "utf8",
    );
  }
  await saveBlob(
    path.join(previewDir, "deck-montage.webp"),
    await presentation.export({ format: "webp", montage: true, scale: 0.42 }),
  );
}

const pptx = await PresentationFile.exportPptx(presentation);
await fs.writeFile(outputPath, Buffer.from(pptx.data));

console.log(`Created ${outputPath}`);
if (shouldRenderPreview) {
  console.log(`Rendered previews to ${previewDir}`);
}
