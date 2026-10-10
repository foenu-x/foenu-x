"""Лексер языка Foenu-x: разбивает исходный код на токены."""

import re
from dataclasses import dataclass


class FoenuSyntaxError(Exception):
    def __init__(self, message, line):
        super().__init__(f"Строка {line}: {message}")
        self.line = line


KEYWORDS = {
    "Foenu-x", "text-", "var", "be", "if", "then", "else",
    "while", "begin", "end", "function", "return", "CMD",
    "and", "or", "not", "true", "false",
}

MASTER = re.compile(
    r"""
      (?P<COMMENT>//[^\n]*)
    | (?P<KEYWORD>(?:Foenu-x|text-|var|be|if|then|else|while|begin|end|function|return|CMD|and|or|not|true|false)(?![\w]))
    | (?P<NUMBER>\d+(?:\.\d+)?)
    | (?P<TEXT>\#[^#\n]*\#)
    | (?P<IDENT>[^\W\d]\w*)
    | (?P<OP>:=|==|!=|>=|<=|[><+\-*/=(),;])
    | (?P<NEWLINE>\n)
    | (?P<SKIP>[ \t\r]+)
    """,
    re.VERBOSE,
)


@dataclass
class Token:
    type: str
    value: str
    line: int

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


def tokenize(source):
    tokens = []
    line = 1
    pos = 0
    length = len(source)

    while pos < length:
        match = MASTER.match(source, pos)
        if not match:
            bad = source[pos]
            if bad == "#":
                raise FoenuSyntaxError("незакрытый текстовый литерал (нет парного #)", line)
            raise FoenuSyntaxError(f"неожиданный символ {bad!r}", line)

        kind = match.lastgroup
        text = match.group()
        pos = match.end()

        if kind == "NEWLINE":
            line += 1
        elif kind in ("COMMENT", "SKIP"):
            pass
        elif kind == "KEYWORD":
            tokens.append(Token("KEYWORD", text, line))
        elif kind == "NUMBER":
            tokens.append(Token("NUMBER", text, line))
        elif kind == "TEXT":
            tokens.append(Token("TEXT", text[1:-1], line))
        elif kind == "IDENT":
            tokens.append(Token("IDENT", text, line))
        elif kind == "OP":
            tokens.append(Token("OP", text, line))

    tokens.append(Token("EOF", "", line))
    return tokens
