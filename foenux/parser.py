"""Парсер языка Foenu-x: строит AST из токенов (рекурсивный спуск)."""

from dataclasses import dataclass, field
from typing import List, Optional

from .lexer import FoenuSyntaxError, tokenize


# ---------- Выражения ----------

@dataclass
class Num:
    value: float
    line: int


@dataclass
class Text:
    value: str
    line: int


@dataclass
class Bool:
    value: bool
    line: int


@dataclass
class Var:
    name: str
    line: int


@dataclass
class Unary:
    op: str
    operand: object
    line: int


@dataclass
class Binary:
    op: str
    left: object
    right: object
    line: int


@dataclass
class Call:
    name: str
    args: list
    line: int


@dataclass
class TextCast:
    expr: object
    line: int


@dataclass
class ListNode:
    items: list
    line: int


@dataclass
class Index:
    obj: object
    index: object
    line: int


# ---------- Инструкции ----------

@dataclass
class Print:
    expr: object
    line: int


@dataclass
class Cmd:
    expr: object
    line: int


@dataclass
class VarDecl:
    name: str
    expr: object
    line: int


@dataclass
class Assign:
    name: str
    expr: object
    line: int


@dataclass
class If:
    cond: object
    then_block: list
    else_block: Optional[list]
    line: int


@dataclass
class While:
    cond: object
    body: list
    line: int


@dataclass
class FunctionDecl:
    name: str
    params: List[str]
    body: list
    line: int


@dataclass
class Return:
    expr: Optional[object]
    line: int


@dataclass
class ExprStmt:
    expr: object
    line: int


@dataclass
class IndexAssign:
    obj: object
    index: object
    value: object
    line: int


@dataclass
class For:
    name: str
    start: object
    end: object
    downto: bool
    body: list
    line: int


@dataclass
class Break:
    line: int


@dataclass
class Continue:
    line: int


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def previous(self):
        return self.tokens[self.pos - 1]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def check(self, type_, value=None):
        tok = self.peek()
        if tok.type != type_:
            return False
        if value is not None and tok.value != value:
            return False
        return True

    def match(self, type_, value=None):
        if self.check(type_, value):
            return self.advance()
        return None

    def expect(self, type_, value, message):
        tok = self.match(type_, value)
        if tok is None:
            got = self.peek()
            shown = got.value if got.type != "EOF" else "конец файла"
            raise FoenuSyntaxError(f"{message} (ожидалось {value!r}, найдено {shown!r})", got.line)
        return tok

    def expect_ident(self, message):
        tok = self.match("IDENT")
        if tok is None:
            got = self.peek()
            raise FoenuSyntaxError(f"{message} (найдено {got.value!r})", got.line)
        return tok

    # ----- Программа и блоки -----

    def parse_program(self):
        statements = []
        while not self.check("EOF"):
            if self.match("OP", ";"):
                continue
            statements.append(self.statement())
        return statements

    def block(self):
        """begin ... end"""
        self.expect("KEYWORD", "begin", "ожидалось begin")
        statements = []
        while not self.check("KEYWORD", "end") and not self.check("EOF"):
            if self.match("OP", ";"):
                continue
            statements.append(self.statement())
        self.expect("KEYWORD", "end", "незакрытый блок: не хватает end")
        return statements

    # ----- Инструкции -----

    def statement(self):
        tok = self.peek()

        if tok.type == "KEYWORD":
            if tok.value == "Foenu-x":
                self.advance()
                line = tok.line
                expr = self.expression()
                self.match("OP", ";")
                return Print(expr, line)

            if tok.value == "CMD":
                self.advance()
                line = tok.line
                self.expect("OP", "(", "после CMD нужна скобка (")
                expr = self.expression()
                self.expect("OP", ")", "не закрыта скобка ) у CMD")
                self.match("OP", ";")
                return Cmd(expr, line)

            if tok.value == "var":
                self.advance()
                line = tok.line
                name = self.expect_ident("после var нужно имя переменной")
                self.expect("KEYWORD", "be", "после имени переменной ожидается be")
                expr = self.expression()
                self.match("OP", ";")
                return VarDecl(name.value, expr, line)

            if tok.value == "if":
                return self.if_statement()

            if tok.value == "while":
                self.advance()
                line = tok.line
                cond = self.expression()
                body = self.block()
                self.match("OP", ";")
                return While(cond, body, line)

            if tok.value == "for":
                return self.for_statement()

            if tok.value == "break":
                self.advance()
                self.match("OP", ";")
                return Break(tok.line)

            if tok.value == "continue":
                self.advance()
                self.match("OP", ";")
                return Continue(tok.line)

            if tok.value == "function":
                return self.function_statement()

            if tok.value == "return":
                self.advance()
                line = tok.line
                if self.check("OP", ";") or self.check("KEYWORD", "end") or self.check("EOF"):
                    expr = None
                else:
                    expr = self.expression()
                self.match("OP", ";")
                return Return(expr, line)

        expr = self.expression()
        if self.match("OP", ":="):
            value = self.expression()
            self.match("OP", ";")
            if isinstance(expr, Var):
                return Assign(expr.name, value, expr.line)
            if isinstance(expr, Index):
                return IndexAssign(expr.obj, expr.index, value, expr.line)
            raise FoenuSyntaxError(
                "присваивать можно только переменной или элементу массива [индекс]", expr.line
            )
        self.match("OP", ";")
        return ExprStmt(expr, tok.line)

    def for_statement(self):
        tok = self.advance()  # for
        line = tok.line
        name = self.expect_ident("после for нужно имя переменной цикла")
        self.expect("OP", ":=", "после имени переменной цикла ожидается :=")
        start = self.expression()
        if self.match("KEYWORD", "downto"):
            downto = True
        elif self.match("KEYWORD", "to"):
            downto = False
        else:
            p = self.peek()
            shown = p.value if p.type != "EOF" else "конец файла"
            raise FoenuSyntaxError(f"после границы цикла ожидается to или downto (найдено {shown!r})", p.line)
        end = self.expression()
        body = self.block()
        self.match("OP", ";")
        return For(name.value, start, end, downto, body, line)

    def if_statement(self):
        tok = self.advance()  # if
        line = tok.line
        cond = self.expression()
        self.expect("KEYWORD", "then", "после условия if ожидается then")
        then_block = self.block()
        else_block = None
        if self.match("KEYWORD", "else"):
            if self.check("KEYWORD", "if"):
                else_block = [self.if_statement()]
            else:
                else_block = self.block()
        self.match("OP", ";")
        return If(cond, then_block, else_block, line)

    def function_statement(self):
        tok = self.advance()  # function
        line = tok.line
        name = self.expect_ident("после function нужно имя функции")
        self.expect("OP", "(", "после имени функции нужна скобка (")
        params = []
        if not self.check("OP", ")"):
            while True:
                p = self.expect_ident("ожидалось имя параметра")
                params.append(p.value)
                if not self.match("OP", ","):
                    break
        self.expect("OP", ")", "не закрыта скобка ) с параметрами")
        body = self.block()
        self.match("OP", ";")
        return FunctionDecl(name.value, params, body, line)

    # ----- Выражения -----

    def expression(self):
        return self.or_expr()

    def or_expr(self):
        left = self.and_expr()
        while self.check("KEYWORD", "or"):
            op = self.advance().value
            line = self.previous().line
            right = self.and_expr()
            left = Binary(op, left, right, line)
        return left

    def and_expr(self):
        left = self.equality()
        while self.check("KEYWORD", "and"):
            op = self.advance().value
            line = self.previous().line
            right = self.equality()
            left = Binary(op, left, right, line)
        return left

    def equality(self):
        left = self.comparison()
        while self.check("OP", "=") or self.check("OP", "==") or self.check("OP", "!="):
            op = self.advance().value
            line = self.previous().line
            right = self.comparison()
            left = Binary(op, left, right, line)
        return left

    def comparison(self):
        left = self.term()
        while self.check("OP", ">") or self.check("OP", "<") \
                or self.check("OP", ">=") or self.check("OP", "<="):
            op = self.advance().value
            line = self.previous().line
            right = self.term()
            left = Binary(op, left, right, line)
        return left

    def term(self):
        left = self.factor()
        while self.check("OP", "+") or self.check("OP", "-"):
            op = self.advance().value
            line = self.previous().line
            right = self.factor()
            left = Binary(op, left, right, line)
        return left

    def factor(self):
        left = self.unary()
        while self.check("OP", "*") or self.check("OP", "/") or self.check("OP", "%"):
            op = self.advance().value
            line = self.previous().line
            right = self.unary()
            left = Binary(op, left, right, line)
        return left

    def unary(self):
        if self.check("OP", "-") or self.check("KEYWORD", "not"):
            op = self.advance()
            operand = self.unary()
            return Unary(op.value, operand, op.line)
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while self.check("OP", "["):
            self.advance()
            idx = self.expression()
            self.expect("OP", "]", "не закрыта скобка ] у индекса")
            node = Index(node, idx, node.line)
        return node

    def primary(self):
        tok = self.peek()

        if tok.type == "NUMBER":
            self.advance()
            value = float(tok.value) if "." in tok.value else int(tok.value)
            return Num(value, tok.line)

        if tok.type == "TEXT":
            self.advance()
            return Text(tok.value, tok.line)

        if tok.type == "KEYWORD" and tok.value in ("true", "false"):
            self.advance()
            return Bool(tok.value == "true", tok.line)

        if tok.type == "KEYWORD" and tok.value == "text-":
            self.advance()
            self.expect("OP", "(", "после text- нужна скобка (")
            expr = self.expression()
            self.expect("OP", ")", "не закрыта скобка ) у text-")
            return TextCast(expr, tok.line)

        if tok.type == "IDENT":
            self.advance()
            if self.check("OP", "("):
                self.advance()
                args = []
                if not self.check("OP", ")"):
                    while True:
                        args.append(self.expression())
                        if not self.match("OP", ","):
                            break
                self.expect("OP", ")", "не закрыта скобка ) с аргументами")
                return Call(tok.value, args, tok.line)
            return Var(tok.value, tok.line)

        if tok.type == "OP" and tok.value == "(":
            self.advance()
            expr = self.expression()
            self.expect("OP", ")", "не закрыта скобка )")
            return expr

        if tok.type == "OP" and tok.value == "[":
            self.advance()
            items = []
            if not self.check("OP", "]"):
                while True:
                    items.append(self.expression())
                    if not self.match("OP", ","):
                        break
            self.expect("OP", "]", "не закрыта скобка ] массива")
            return ListNode(items, tok.line)

        shown = tok.value if tok.type != "EOF" else "конец файла"
        raise FoenuSyntaxError(f"неожиданное начало выражения: {shown!r}", tok.line)


def parse(source):
    tokens = tokenize(source)
    return Parser(tokens).parse_program()
