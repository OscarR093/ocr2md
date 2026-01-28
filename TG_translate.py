#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

SOURCE_LANG = "English"
SOURCE_CODE = "en"
TARGET_LANG = "Spanish"
TARGET_CODE = "es"

MODEL = "translategemma"

def build_prompt(text: str) -> str:
    return f"""You are a professional {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) translator. Your goal is to accurately convey the meaning and nuances of the original {SOURCE_LANG} text while adhering to {TARGET_LANG} grammar, vocabulary, and cultural sensitivities.
Produce only the {TARGET_LANG} translation, without any additional explanations or commentary. Please translate the following {SOURCE_LANG} text into {TARGET_LANG}:


{text}
"""

def run_translation(md_text: str) -> str:
    prompt = build_prompt(md_text)

    proc = subprocess.run(
        ["ollama", "run", MODEL],
        input=prompt,
        text=True,
        capture_output=True
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)

    return proc.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 TG_translate.py archivo.md")
        sys.exit(1)

    md_path = Path(sys.argv[1]).expanduser().resolve()

    if not md_path.exists() or md_path.suffix.lower() != ".md":
        print(f"❌ Archivo inválido: {md_path}")
        sys.exit(1)

    print(f"🌍 Traduciendo: {md_path.name}")

    md_text = md_path.read_text(encoding="utf-8")

    translated = run_translation(md_text)

    out_path = md_path.with_suffix(f".{TARGET_CODE}.md")
    out_path.write_text(translated, encoding="utf-8")

    print(f"✅ Traducción guardada en: {out_path}")

if __name__ == "__main__":
    main()

