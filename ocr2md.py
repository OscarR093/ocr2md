#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from subprocess import TimeoutExpired

OCR_TIMEOUT = 5  # segundos

def deepseek_to_md(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            lines.append("")
            continue
        if line.startswith("<|"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
def run_ocr(image_path: Path) -> str:
    prompt = (
        f"{image_path}\n"
        "<|grounding|>Convert the document to markdown."
    )

    try:
        proc = subprocess.run(
            ["ollama", "run", "deepseek-ocr"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=OCR_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"⏱ Timeout en {image_path.name}")

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)

    return proc.stdout

def pdf_to_images(pdf: Path, out_dir: Path):
    if out_dir.exists() and any(out_dir.glob("page-*.png")):
        print("📂 Imágenes ya existen, se reutilizan")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r", "300",
            str(pdf),
            str(out_dir / "page")
        ],
        check=True
    )

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 DS_Ocr.py archivo.pdf")
        sys.exit(1)

    pdf = Path(sys.argv[1]).expanduser().resolve()

    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        print(f"❌ Archivo inválido: {pdf}")
        sys.exit(1)

    base_dir = pdf.with_suffix("")
    pages_dir = base_dir / "pages"
    output_md = base_dir / f"{pdf.stem}.md"

    print(f"📄 Procesando PDF: {pdf.name}")
    pdf_to_images(pdf, pages_dir)

    pages = sorted(pages_dir.glob("page-*.png"))
    if not pages:
        print("❌ No se encontraron imágenes")
        sys.exit(1)

    all_md = []

    for idx, page in enumerate(pages, 1):
        print(f"📸 OCR página {idx}/{len(pages)} → {page.name}")
        all_md.append(f"\n\n<!-- Página {idx} -->\n\n")

        try:
            raw = run_ocr(page)
            md = deepseek_to_md(raw)
            all_md.append(md)

        except TimeoutError as e:
            print(f"⚠️ {e}")
            all_md.append("_[Página omitida por timeout]_")

        except Exception as e:
            print(f"⚠️ Error en {page.name}: {e}")
            all_md.append("_[Error de OCR en esta página]_")

    output_md.write_text("".join(all_md).strip(), encoding="utf-8")
    print(f"✅ Markdown final: {output_md}")

if __name__ == "__main__":
    main()

