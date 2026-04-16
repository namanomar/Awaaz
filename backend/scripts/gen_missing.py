#!/usr/bin/env python3
"""
Generate missing FAQ files for all schemes and all languages.
Run from project root: python scripts/gen_missing.py
"""
import os, sys, time
sys.path.insert(0, '.')
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from scripts.crawl_ingest import (
    SCHEMES, LANGUAGES, DATA_DIR,
    generate_english_faqs, translate_faqs,
    save_faq_file, ingest_file
)

def run():
    print("=== Generating missing FAQ files ===\n")

    for scheme in SCHEMES:
        en_path = DATA_DIR / f"en_{scheme.id}.txt"

        # Step 1: generate English if missing
        if not en_path.exists():
            print(f"[{scheme.id}] Generating English FAQ...")
            faqs = generate_english_faqs(scheme, "")
            if faqs.strip():
                save_faq_file(scheme.id, "en", faqs)
                time.sleep(3)
            else:
                print(f"  [warn] empty result for {scheme.id}")
                continue
        else:
            print(f"[{scheme.id}] English already exists, loading...")

        en_faqs = en_path.read_text(encoding="utf-8").strip()

        # Step 2: translate to each missing language
        for lang_code, lang_name in LANGUAGES.items():
            if lang_code == "en":
                continue
            out_path = DATA_DIR / f"{lang_code}_{scheme.id}.txt"
            if out_path.exists():
                print(f"  [skip] {lang_code}_{scheme.id}.txt already exists")
                continue  # already ingested, skip
            print(f"[{scheme.id}] Translating → {lang_name}...")
            translated = translate_faqs(en_faqs, lang_code, lang_name)
            if translated.strip():
                save_faq_file(scheme.id, lang_code, translated)
                # Don't ingest here — bulk ingest at the end via scripts/ingest.py
                time.sleep(4)
            else:
                print(f"  [warn] empty translation for {lang_code}")

        print(f"  [{scheme.id}] complete\n")

    # Bulk ingest all files at once (more reliable than per-file ingest)
    print("\n=== Bulk ingesting all FAQ files to Qdrant ===")
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "scripts/ingest.py", "--data-dir", "data/faqs/"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"Ingest error: {result.stderr[-500:]}")

    # Summary
    print("\n=== Summary ===")
    for scheme in SCHEMES:
        files = [l for l in LANGUAGES if (DATA_DIR / f"{l}_{scheme.id}.txt").exists()]
        print(f"  {scheme.id:12} {len(files)}/8 languages")
    print("\nDone.")

if __name__ == "__main__":
    run()
