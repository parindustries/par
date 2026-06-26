#!/usr/bin/env python3
"""Translate missing or incomplete locale JSON files from English source."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = ROOT / "assets" / "i18n"

SKIP_PATTERNS = [
    re.compile(r"^M\d", re.I),
    re.compile(r"^\d"),
    re.compile(r"^PAR Industries$", re.I),
    re.compile(r"^DIN|^ISO|^ASTM|^BS\b", re.I),
]


def should_skip_translation(key: str, text: str) -> bool:
    if not text or not text.strip():
        return True
    if key.startswith("products.item.") and any(c.isdigit() for c in text):
        return False
    for pat in SKIP_PATTERNS:
        if pat.search(text.strip()):
            return True
    return False


def protect_markup(text: str) -> tuple[str, dict[str, str]]:
    tokens: dict[str, str] = {}
    idx = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal idx
        token = f"__TOK{idx}__"
        tokens[token] = match.group(0)
        idx += 1
        return token

    protected = re.sub(r"<[^>]+>|&[a-zA-Z#0-9]+;", repl, text)
    protected = protected.replace("PAR Industries", "__BRAND__")
    return protected, tokens


def restore_markup(text: str, tokens: dict[str, str]) -> str:
    out = text.replace("__BRAND__", "PAR Industries")
    for token, original in tokens.items():
        out = out.replace(token, original)
    return out


def translate_text(text: str, target: str, translator) -> str:
    protected, tokens = protect_markup(text)
    if not protected.strip():
        return text
    try:
        translated = translator.translate(protected)
        return restore_markup(translated, tokens)
    except Exception as exc:
        print(f"  translate error: {exc}", file=sys.stderr)
        return text


def main() -> int:
    from deep_translator import GoogleTranslator

    locales = json.loads((ROOT / "locales.json").read_text(encoding="utf-8"))["locales"]
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))

    targets = [loc for loc in locales if loc != "en"]
    force = "--force" in sys.argv

    for locale_id in targets:
        target_code = locales[locale_id]["translateTarget"]
        out_path = I18N_DIR / f"{locale_id}.json"
        existing = {}
        if out_path.exists() and not force:
            existing = json.loads(out_path.read_text(encoding="utf-8"))

        if existing and len(existing) >= len(en) and not force:
            print(f"Skip {locale_id} (complete)")
            continue

        print(f"Translating {locale_id} -> {target_code}")
        translator = GoogleTranslator(source="en", target=target_code)
        out = dict(existing)

        for i, (key, value) in enumerate(en.items()):
            if key in out and out[key] and not force:
                continue
            if should_skip_translation(key, value):
                out[key] = value
                continue
            out[key] = translate_text(value, target_code, translator)
            if i % 8 == 7:
                time.sleep(0.2)

        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path} ({len(out)} keys)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
