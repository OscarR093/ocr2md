#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
from subprocess import TimeoutExpired

OCR_TIMEOUT = 15  # segundos


def fix_citations(text: str) -> str:
    """
    Corrección robusta de citas: (^{26}) -> [^26]
    Tolera espacios y falta de llaves en cualquier posición.
    """
    return re.sub(r'\\?\(\s*\^\s*\{?\s*([a-zA-Z0-9+\s]+)\s*\}?\s*\\?\)', r'[^\1]', text)


def normalize_text(raw: str) -> str:
    """
    Limpia la salida del OCR sin imponer formato.
    """
    lines = []
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            lines.append("")
            continue
        if line.startswith("<|"):
            continue
        lines.append(line)
    
    text = "\n".join(lines).strip()
    return fix_citations(text)


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
    except TimeoutExpired:
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


def run_pandoc(text_dir: Path, output: Path):
    pages = sorted(text_dir.glob("page-*.txt"))

    if not pages:
        raise RuntimeError("❌ No hay archivos de texto para Pandoc")

    print(f"📚 Generando {output.name} con Pandoc")

    cmd = ["pandoc", *map(str, pages), "-o", str(output)]

    if output.suffix == ".pdf":
        cmd += [
            "--pdf-engine=xelatex",
            "-V", "mainfont=Libertinus Serif"
        ]

    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) not in (2, 3):
        print("Uso: python3 DS_Ocr.py archivo.pdf [pdf|epub]")
        sys.exit(1)

    pdf = Path(sys.argv[1]).expanduser().resolve()
    output_format = sys.argv[2].lower() if len(sys.argv) == 3 else None

    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        print(f"❌ Archivo inválido: {pdf}")
        sys.exit(1)

    if output_format not in (None, "pdf", "epub"):
        print("❌ Formato de salida inválido (usa pdf o epub)")
        sys.exit(1)

    base_dir = pdf.with_suffix("")
    pages_dir = base_dir / "pages"
    text_dir = base_dir / "text"
    output_file = (
        base_dir / f"{pdf.stem}.{output_format}"
        if output_format
        else None
    )

    print(f"📄 Procesando PDF: {pdf.name}")
    pdf_to_images(pdf, pages_dir)

    pages = sorted(pages_dir.glob("page-*.png"))
    if not pages:
        print("❌ No se encontraron imágenes")
        sys.exit(1)

    text_dir.mkdir(exist_ok=True)

    for idx, page in enumerate(pages, 1):
        out_txt = text_dir / f"page-{idx:03d}.txt"

        if out_txt.exists():
            print(f"⏭️  OCR ya existe → {out_txt.name}")
            continue

        print(f"📸 OCR página {idx}/{len(pages)} → {page.name}")

        try:
            raw = run_ocr(page)
            text = normalize_text(raw)
            out_txt.write_text(text, encoding="utf-8")

        except TimeoutError as e:
            print(f"⚠️ {e}")
            out_txt.write_text("[Página omitida por timeout]", encoding="utf-8")

        except Exception as e:
            print(f"⚠️ Error en {page.name}: {e}")
            out_txt.write_text("[Error de OCR en esta página]", encoding="utf-8")

    print(f"✅ OCR completado → {text_dir}")

    print("🔧 Normalizando citas en todos los archivos de texto...")
    count = 0
    for txt_file in text_dir.glob("page-*.txt"):
        content = txt_file.read_text(encoding="utf-8")
        fixed_content = fix_citations(content)
        if content != fixed_content:
            txt_file.write_text(fixed_content, encoding="utf-8")
            count += 1
    
    if count > 0:
        print(f"✨ Citas corregidas en {count} archivos.")
    else:
        print("✨ No se requirieron correcciones adicionales en citas.")

    if output_file:
        if output_file.exists():
            print(f"⏭️  {output_file.name} ya existe, se omite Pandoc")
        else:
            run_pandoc(text_dir, output_file)
            print(f"✅ Archivo generado → {output_file}")


if __name__ == "__main__":
    main()

