"""Интерпретатор языка Foenu-x: выполняет AST."""

import subprocess
import sys

from .lexer import FoenuSyntaxError
from .parser import (
    Num, Text, Bool, Var, Unary, Binary, Call, TextCast,
    Print, Cmd, VarDecl, Assign, If, While, FunctionDecl, Return, ExprStmt,
    parse,
)


class FoenuRuntimeError(Exception):
    def __init__(self, message, line):
        super().__init__(f"Строка {line}: {message}")
        self.line = line


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value):
        self.values[name] = value

    def get(self, name, line):
        env = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise FoenuRuntimeError(f"переменная {name!r} не объявлена", line)

    def assign(self, name, value, line):
        env = self
        while env is not None:
            if name in env.values:
                env.values[name] = value
                return
            env = env.parent
        raise FoenuRuntimeError(f"нельзя присвоить несуществующей переменной {name!r}: сначала var {name} be ...", line)


class Function:
    def __init__(self, decl, closure):
        self.decl = decl
        self.closure = closure


def to_str(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return repr(value)
    return str(value)


def truthy(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return bool(value)


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.allow_redefine = False
        self.echo_results = False

    # ----- Точка входа -----

    def run(self, source, filename="<stdin>"):
        program = parse(source)
        try:
            self.exec_block(program, self.globals)
        except ReturnSignal:
            raise FoenuRuntimeError("return вне функции", 1) from None

    # ----- Выполнение инструкций -----

    def exec_block(self, statements, env):
        for stmt in statements:
            self.exec_stmt(stmt, env)

    def exec_stmt(self, stmt, env):
        if isinstance(stmt, Print):
            print(to_str(self.eval(stmt.expr, env)))
        elif isinstance(stmt, Cmd):
            self.exec_cmd(stmt, env)
        elif isinstance(stmt, VarDecl):
            value = self.eval(stmt.expr, env)
            if stmt.name in env.values and not (self.allow_redefine and env is self.globals):
                raise FoenuRuntimeError(f"переменная {stmt.name!r} уже объявлена", stmt.line)
            env.define(stmt.name, value)
        elif isinstance(stmt, Assign):
            value = self.eval(stmt.expr, env)
            env.assign(stmt.name, value, stmt.line)
        elif isinstance(stmt, If):
            if truthy(self.eval(stmt.cond, env)):
                self.exec_block(stmt.then_block, Environment(env))
            elif stmt.else_block is not None:
                self.exec_block(stmt.else_block, Environment(env))
        elif isinstance(stmt, While):
            while truthy(self.eval(stmt.cond, env)):
                self.exec_block(stmt.body, Environment(env))
        elif isinstance(stmt, FunctionDecl):
            env.define(stmt.name, Function(stmt, env))
        elif isinstance(stmt, Return):
            value = self.eval(stmt.expr, env) if stmt.expr is not None else None
            raise ReturnSignal(value)
        elif isinstance(stmt, ExprStmt):
            value = self.eval(stmt.expr, env)
            if self.echo_results and value is not None:
                print(to_str(value))
        else:
            raise FoenuRuntimeError(f"неизвестная инструкция {stmt!r}", getattr(stmt, "line", 1))

    def exec_cmd(self, stmt, env):
        arg = self.eval(stmt.expr, env)
        command = to_str(arg)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        except OSError as e:
            raise FoenuRuntimeError(f"не удалось выполнить команду: {e}", stmt.line) from None
        if result.stdout:
            out = result.stdout
            if out.endswith("\n") or out.endswith("\r\n"):
                out = out.rstrip("\r\n")
            if out:
                print(out)
        if result.stderr:
            err = result.stderr.rstrip("\r\n")
            if err:
                print(err, file=sys.stderr)
        if result.returncode != 0:
            print(f"[foenu-x] команда завершилась с кодом {result.returncode}", file=sys.stderr)

    # ----- Вычисление выражений -----

    def eval(self, node, env):
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Text):
            return node.value
        if isinstance(node, Bool):
            return node.value
        if isinstance(node, Var):
            return env.get(node.name, node.line)
        if isinstance(node, TextCast):
            return to_str(self.eval(node.expr, env))
        if isinstance(node, Unary):
            return self.eval_unary(node, env)
        if isinstance(node, Binary):
            return self.eval_binary(node, env)
        if isinstance(node, Call):
            return self.eval_call(node, env)
        raise FoenuRuntimeError(f"неизвестное выражение {node!r}", getattr(node, "line", 1))

    def eval_unary(self, node, env):
        value = self.eval(node.operand, env)
        if node.op == "-":
            if not is_number(value):
                raise FoenuRuntimeError("унарный минус работает только с числами", node.line)
            return -value
        if node.op == "not":
            return not truthy(value)
        raise FoenuRuntimeError(f"неизвестный оператор {node.op!r}", node.line)

    def eval_binary(self, node, env):
        op = node.op

        if op == "and":
            left = self.eval(node.left, env)
            if not truthy(left):
                return False
            return truthy(self.eval(node.right, env))
        if op == "or":
            left = self.eval(node.left, env)
            if truthy(left):
                return True
            return truthy(self.eval(node.right, env))

        left = self.eval(node.left, env)
        right = self.eval(node.right, env)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return to_str(left) + to_str(right)
            if is_number(left) and is_number(right):
                return left + right
            raise FoenuRuntimeError("оператор + работает только с числами или текстом", node.line)

        if op in ("-", "*", "/"):
            if not is_number(left) or not is_number(right):
                raise FoenuRuntimeError(f"оператор {op} работает только с числами", node.line)
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if right == 0:
                raise FoenuRuntimeError("деление на ноль", node.line)
            if isinstance(left, int) and isinstance(right, int):
                if left % right == 0:
                    return left // right
                return left / right
            return left / right

        if op in ("=", "=="):
            return self.loose_eq(left, right)
        if op == "!=":
            return not self.loose_eq(left, right)

        if op in (">", "<", ">=", "<="):
            if is_number(left) and is_number(right):
                pass
            elif isinstance(left, str) and isinstance(right, str):
                pass
            else:
                raise FoenuRuntimeError(f"нельзя сравнивать {to_str(left)!r} и {to_str(right)!r}", node.line)
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            if op == ">=":
                return left >= right
            return left <= right

        raise FoenuRuntimeError(f"неизвестный оператор {op!r}", node.line)

    @staticmethod
    def loose_eq(left, right):
        if is_number(left) and is_number(right):
            return left == right
        if isinstance(left, bool) or isinstance(right, bool):
            return left == right
        if isinstance(left, str) and isinstance(right, str):
            return left == right
        return False

    def eval_call(self, node, env):
        callee = env.get(node.name, node.line)

        if isinstance(callee, Function):
            decl = callee.decl
            if len(node.args) != len(decl.params):
                raise FoenuRuntimeError(
                    f"функция {node.name!r} ждёт {len(decl.params)} аргументов, получено {len(node.args)}",
                    node.line,
                )
            call_env = Environment(callee.closure)
            for name, arg in zip(decl.params, node.args):
                call_env.define(name, self.eval(arg, env))
            try:
                self.exec_block(decl.body, call_env)
            except ReturnSignal as sig:
                return sig.value
            return None

        raise FoenuRuntimeError(f"{node.name!r} не является функцией", node.line)


def run_source(source, filename="<stdin>"):
    Interpreter().run(source, filename)
