#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подсветка .foenu-x в цветной HTML-файл.

Использование:
    python tools\\highlight.py examples\\hello.foenu-x
    (рядом появится hello.html с цветами)
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from foenux.lexer import MASTER

C_BG = "#0d1117"
C_TEXT = "#e6edf3"
C_KEYWORD = "#f778ba"
C_STRING = "#3fb950"
C_NUMBER = "#58a6ff"
C_COMMENT = "#8b949e"
C_FUNC = "#d2a8ff"
C_OP = "#d29922"

KEYWORDS = {
    "Foenu-x", "text-", "var", "be", "if", "then", "else",
    "while", "begin", "end", "function", "return", "CMD",
    "and", "or", "not", "true", "false",
}


def span(color, text):
    return f'<span style="color:{color}">{html.escape(text)}</span>'


def highlight(source):
    out = []
    pos = 0
    length = len(source)
    prev_ident_end = -10

    while pos < length:
        m = MASTER.match(source, pos)
        if not m:
            out.append(html.escape(source[pos]))
            pos += 1
            continue

        kind = m.lastgroup
        text = m.group()
        pos = m.end()

        if kind == "NEWLINE":
            out.append("\n")
        elif kind == "SKIP":
            out.append(text)
        elif kind == "COMMENT":
            out.append(span(C_COMMENT, text))
        elif kind == "KEYWORD":
            out.append(span(C_KEYWORD, text))
        elif kind == "TEXT":
            out.append(span(C_STRING, text))
        elif kind == "NUMBER":
            out.append(span(C_NUMBER, text))
        elif kind == "IDENT":
            j = pos
            while j < length and source[j] in " \t":
                j += 1
            if j < length and source[j] == "(":
                out.append(span(C_FUNC, text))
            else:
                out.append(html.escape(text))
        elif kind == "OP":
            out.append(span(C_OP, text))
        else:
            out.append(html.escape(text))

    return "".join(out)


def make_html(colored_code, title="Foenu-x"):
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        "</head>\n"
        f'<body style="background:{C_BG};color:{C_TEXT};'
        'font-family:Consolas,monospace;padding:20px">\n'
        f"<pre>{colored_code}</pre>\n"
        "</body>\n"
        "</html>\n"
    )


def main(argv):
    if len(argv) < 1:
        print("Использование: python tools\\highlight.py файл.foenu-x")
        return 1
    src_path = Path(argv[0])
    if not src_path.exists():
        print(f"Файл не найден: {src_path}", file=sys.stderr)
        return 1
    source = src_path.read_text(encoding="utf-8-sig")
    colored = highlight(source)
    out_path = src_path.with_suffix(".html")
    out_path.write_text(make_html(colored, title=src_path.name), encoding="utf-8")
    print(f"Готово: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
