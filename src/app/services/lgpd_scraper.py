from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib import request as urllib_request

from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DEFAULT_LGPD_URL = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
DEFAULT_OUTPUT_DIR = Path("data/legal/lgpd")
TEXT_FILE_NAME = "lgpd_clean.txt"
PDF_FILE_NAME = "lgpd_clean.pdf"
RAW_FILE_NAME = "lgpd_clean_native.txt"


def fetch_html(url: str) -> str:
    http_request = urllib_request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RAG-LGPD-Scraper/1.0)"},
        method="GET",
    )
    with urllib_request.urlopen(http_request, timeout=60) as response:
        raw_bytes = response.read()

    detected_encoding = detect_html_encoding(raw_bytes)
    encodings_to_try = [
        detected_encoding,
        "utf-8",
        "windows-1252",
        "latin-1",
    ]
    return decode_with_best_effort(raw_bytes, encodings_to_try)


def decode_with_best_effort(raw_bytes: bytes, encodings: list[str | None]) -> str:
    best_text: str | None = None
    best_score: int | None = None

    for encoding in encodings:
        if not encoding:
            continue
        try:
            decoded = raw_bytes.decode(encoding, errors="replace")
        except LookupError:
            continue

        score = score_decoding_quality(decoded)
        if best_score is None or score < best_score:
            best_text = decoded
            best_score = score

    if best_text is None:
        return raw_bytes.decode("latin-1", errors="replace")

    repaired_text = try_mojibake_repair(best_text)
    if score_decoding_quality(repaired_text) < score_decoding_quality(best_text):
        return repaired_text
    return best_text


def try_mojibake_repair(text: str) -> str:
    try:
        return text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except UnicodeError:
        return text


def score_decoding_quality(text: str) -> int:
    # Penaliza padrões comuns de mojibake e caracteres de substituição.
    return (
        text.count("�") * 10
        + text.count("Ã") * 4
        + text.count("Â") * 3
        + text.count("Ð") * 2
    )


def detect_html_encoding(raw_bytes: bytes) -> str | None:
    head = raw_bytes[:4096].decode("ascii", errors="ignore").lower()

    charset_match = re.search(r"charset\s*=\s*['\"]?([a-z0-9_\-]+)", head)
    if charset_match:
        return charset_match.group(1)

    return None


def remove_strikethrough_nodes(soup: BeautifulSoup) -> None:
    for tag_name in ("strike", "s", "del"):
        for node in soup.find_all(tag_name):
            node.decompose()

    for node in list(soup.find_all(style=True)):
        if not getattr(node, "attrs", None):
            continue
        style_value = str(node.attrs.get("style") or "").lower().replace(" ", "")
        if "text-decoration:line-through" in style_value or "text-decoration-line:line-through" in style_value:
            node.decompose()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_lgpd_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for garbage_tag in soup.find_all(["script", "style", "noscript"]):
        garbage_tag.decompose()

    remove_strikethrough_nodes(soup)

    root = soup.body or soup
    raw_text = root.get_text("\n", strip=True)

    start_markers = [
        "O PRESIDENTE DA REPÚBLICA",
        "O PRESIDENTE DA REPUBLICA",
        "CAPÍTULO I",
        "CAPITULO I",
        "Art. 1º",
        "Art. 1o",
    ]

    start_index = -1
    for marker in start_markers:
        marker_pos = raw_text.find(marker)
        if marker_pos != -1:
            start_index = marker_pos
            break

    if start_index != -1:
        raw_text = raw_text[start_index:]

    end_markers = [
        "Brasília,",
        "Este texto não substitui o publicado",
    ]
    end_positions = [raw_text.find(marker) for marker in end_markers if raw_text.find(marker) != -1]
    if end_positions:
        raw_text = raw_text[: min(end_positions)]

    return normalize_text(raw_text)


def save_txt(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content + "\n", encoding="utf-8")


def save_pdf(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    paragraph_style = styles["BodyText"]
    paragraph_style.leading = 14

    flow = []
    for block in content.split("\n\n"):
        cleaned_block = block.strip()
        if not cleaned_block:
            continue
        escaped = (
            cleaned_block.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        escaped = escaped.replace("\n", "<br/>")
        flow.append(Paragraph(escaped, paragraph_style))
        flow.append(Spacer(1, 8))

    doc.build(flow)


def scrape_lgpd(url: str = DEFAULT_LGPD_URL, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    html = fetch_html(url)
    clean_text = extract_lgpd_text(html)

    txt_path = output_dir / TEXT_FILE_NAME
    pdf_path = output_dir / PDF_FILE_NAME
    native_path = output_dir / RAW_FILE_NAME

    save_txt(clean_text, txt_path)
    save_txt(clean_text, native_path)
    save_pdf(clean_text, pdf_path)

    return {
        "txt": txt_path,
        "pdf": pdf_path,
        "native": native_path,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scraper da LGPD (Planalto) com remoção de texto riscado")
    parser.add_argument("--url", default=DEFAULT_LGPD_URL, help="URL da página da lei")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Diretório onde os arquivos serão salvos",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    outputs = scrape_lgpd(url=args.url, output_dir=output_dir)
    print(f"TXT salvo em: {outputs['txt']}")
    print(f"PDF salvo em: {outputs['pdf']}")
    print(f"Texto nativo salvo em: {outputs['native']}")


if __name__ == "__main__":
    main()
