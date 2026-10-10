"""Foenu-x — интерпретатор языка программирования.

Запуск:
    python main.py файл.foenu-x
    python main.py              # REPL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from foenux.lexer import FoenuSyntaxError
from foenux.interpreter import FoenuRuntimeError, Interpreter, run_source


BANNER = """\
--------------------------------------------
Foenu-x
--------------------------------------------
Для справки набери help, для выхода — exit.
"""

HELP = """\
Foenu-x REPL — командная строка языка.

Команды оболочки:
  exit, quit  — выход
  help        — эта справка
  version     — версия языка
  clear       — очистить экран

Всё остальное — код Foenu-x:
  var x be 5;        объявить переменную
  Foenu-x x * 2;     вывести значение
  2 + 3              выражение печатает результат
"""


def run_file(path):
    file = Path(path)
    if not file.exists():
        print(f"Файл не найден: {file}", file=sys.stderr)
        return 1
    source = file.read_text(encoding="utf-8-sig")
    try:
        run_source(source, filename=str(file))
    except (FoenuSyntaxError, FoenuRuntimeError) as e:
        print(f"Ошибка в {file}: {e}", file=sys.stderr)
        return 1
    return 0


def is_balanced(source):
    """True, если блоки begin/end и скобки закрыты."""
    from foenux.lexer import tokenize, FoenuSyntaxError as _E

    try:
        tokens = tokenize(source)
    except _E:
        return True  # ошибка покажется при выполнении
    depth = 0
    for tok in tokens:
        if tok.type == "KEYWORD" and tok.value == "begin":
            depth += 1
        elif tok.type == "KEYWORD" and tok.value == "end":
            depth -= 1
        elif tok.type == "OP" and tok.value == "(":
            depth += 1
        elif tok.type == "OP" and tok.value == ")":
            depth -= 1
    return depth <= 0


def repl():
    if not sys.stdin.isatty() and getattr(sys.stdin, "reconfigure", None):
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print(BANNER)
    interp = Interpreter()
    interp.allow_redefine = True
    interp.echo_results = True
    buffer = ""
    while True:
        prompt = ">>> " if not buffer else "... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        stripped = line.strip().replace("\ufeff", "")
        if not buffer:
            if stripped in ("exit", "quit"):
                break
            if stripped == "help":
                print(HELP)
                continue
            if stripped == "version":
                print("Foenu-x 1.0 (БЕТА)")
                continue
            if stripped == "clear":
                import os
                os.system("cls" if os.name == "nt" else "clear")
                continue
        buffer = buffer + ("\n" if buffer else "") + line.replace("\ufeff", "")
        if not is_balanced(buffer):
            continue
        source, buffer = buffer, ""
        if not source.strip():
            continue
        try:
            interp.run(source, filename="<repl>")
        except (FoenuSyntaxError, FoenuRuntimeError) as e:
            print(f"Ошибка: {e}")
    return 0


def main(argv):
    if getattr(sys.stdout, "reconfigure", None):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if len(argv) == 0:
        return repl()
    if argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Запуск файла:  python main.py программа.foenu-x")
        print("REPL:          python main.py")
        return 0
    if argv[0] in ("-v", "--version"):
        print("Foenu-x 1.0")
        return 0
    return run_file(argv[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
