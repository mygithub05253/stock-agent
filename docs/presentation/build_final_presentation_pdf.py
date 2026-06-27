from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


REPO_ROOT = Path(__file__).resolve().parents[2]
PRESENTATION_DIR = REPO_ROOT / "docs" / "presentation"
HTML_PATH = PRESENTATION_DIR / "final_presentation.html"
OUTPUT_PDF = PRESENTATION_DIR / "final_presentation.pdf"
TMP_DIR = REPO_ROOT / "tmp" / "presentation-pdf-build"
RAW_PDF = TMP_DIR / "raw_chrome_export.pdf"
PAGE_PREFIX = TMP_DIR / "page"


def first_existing(paths: list[str | Path]) -> str | None:
    for item in paths:
        if not item:
            continue
        candidate = Path(item)
        if candidate.exists():
            return str(candidate)
    return None


def find_chrome() -> str:
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome = first_existing(candidates)
    if not chrome:
        raise RuntimeError("Chrome or Edge executable was not found.")
    return chrome


def find_pdftoppm() -> str:
    home = Path.home()
    candidates = [
        shutil.which("pdftoppm"),
        home / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "bin" / "pdftoppm.exe",
        home
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "native"
        / "poppler"
        / "Library"
        / "bin"
        / "pdftoppm.exe",
    ]
    pdftoppm = first_existing(candidates)
    if not pdftoppm:
        raise RuntimeError("pdftoppm executable was not found.")
    return pdftoppm


def export_raw_pdf() -> None:
    chrome = find_chrome()
    html_url = HTML_PATH.resolve().as_uri()
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--allow-file-access-from-files",
            f"--print-to-pdf={RAW_PDF}",
            "--no-pdf-header-footer",
            html_url,
        ],
        check=True,
    )


def render_pages() -> list[Path]:
    pdftoppm = find_pdftoppm()
    subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            "160",
            str(RAW_PDF),
            str(PAGE_PREFIX),
        ],
        check=True,
    )
    pages = sorted(TMP_DIR.glob("page-*.png"))
    if not pages:
        raise RuntimeError("No pages were rendered from the raw PDF.")
    return pages


def build_flat_pdf(pages: list[Path]) -> None:
    page_width = 16 * 72
    page_height = 9 * 72
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=(page_width, page_height))
    pdf.setTitle("stock-agent final presentation")
    for page in pages:
        with Image.open(page) as image:
            image.load()
            reader = ImageReader(image.convert("RGB"))
            pdf.drawImage(reader, 0, 0, width=page_width, height=page_height)
        pdf.showPage()
    pdf.save()


def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(HTML_PATH)
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    export_raw_pdf()
    pages = render_pages()
    build_flat_pdf(pages)
    print(f"Created flattened PDF: {OUTPUT_PDF}")
    print(f"Pages: {len(pages)}")


if __name__ == "__main__":
    main()
