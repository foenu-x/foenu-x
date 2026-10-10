"""Интерпретатор языка Foenu-x: выполняет AST."""

import random as _random
import subprocess
import sys

from .lexer import FoenuSyntaxError
from .parser import (
    Num, Text, Bool, Var, Unary, Binary, Call, TextCast, ListNode, Index,
    Print, Cmd, VarDecl, Assign, If, While, FunctionDecl, Return, ExprStmt,
    IndexAssign, For, Break, Continue,
    parse,
)


class FoenuRuntimeError(Exception):
    def __init__(self, message, line):
        super().__init__(f"Строка {line}: {message}")
        self.line = line


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


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
    if isinstance(value, list):
        return "[" + ", ".join(to_str(v) for v in value) + "]"
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
    if isinstance(value, list):
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
        except (BreakSignal, ContinueSignal):
            raise FoenuRuntimeError("break/continue вне цикла", 1) from None

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
                try:
                    self.exec_block(stmt.body, Environment(env))
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        elif isinstance(stmt, For):
            self.exec_for(stmt, env)
        elif isinstance(stmt, Break):
            raise BreakSignal()
        elif isinstance(stmt, Continue):
            raise ContinueSignal()
        elif isinstance(stmt, IndexAssign):
            obj = self.eval(stmt.obj, env)
            idx = self.eval(stmt.index, env)
            value = self.eval(stmt.value, env)
            if not isinstance(obj, list):
                raise FoenuRuntimeError("изменять по индексу можно только массив", stmt.line)
            i = self.index_of(obj, idx, stmt.line)
            obj[i] = value
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

    def exec_for(self, stmt, env):
        start = self.eval(stmt.start, env)
        end = self.eval(stmt.end, env)
        if not is_number(start) or not is_number(end):
            raise FoenuRuntimeError("границы цикла for должны быть числами", stmt.line)
        if (isinstance(start, float) and not start.is_integer()) or \
                (isinstance(end, float) and not end.is_integer()):
            raise FoenuRuntimeError("границы цикла for должны быть целыми числами", stmt.line)
        s, e = int(start), int(end)
        rng = range(s, e - 1, -1) if stmt.downto else range(s, e + 1)
        for value in rng:
            env.define(stmt.name, value)
            try:
                self.exec_block(stmt.body, Environment(env))
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    @staticmethod
    def index_of(obj, idx, line):
        if not is_number(idx):
            raise FoenuRuntimeError("индекс должен быть числом", line)
        if isinstance(idx, float):
            if not idx.is_integer():
                raise FoenuRuntimeError("индекс должен быть целым числом", line)
            idx = int(idx)
        if idx < 0 or idx >= len(obj):
            raise FoenuRuntimeError(f"индекс {idx} вне диапазона 0..{len(obj) - 1}", line)
        return idx

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
        if isinstance(node, ListNode):
            return [self.eval(item, env) for item in node.items]
        if isinstance(node, Index):
            obj = self.eval(node.obj, env)
            idx = self.eval(node.index, env)
            if isinstance(obj, (list, str)):
                i = self.index_of(obj, idx, node.line)
                return obj[i]
            raise FoenuRuntimeError("индексировать можно только массив или текст", node.line)
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
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            if isinstance(left, str) or isinstance(right, str):
                return to_str(left) + to_str(right)
            if is_number(left) and is_number(right):
                return left + right
            raise FoenuRuntimeError("оператор + работает только с числами, текстом или массивами", node.line)

        if op in ("-", "*", "/", "%"):
            if not is_number(left) or not is_number(right):
                raise FoenuRuntimeError(f"оператор {op} работает только с числами", node.line)
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "%":
                if right == 0:
                    raise FoenuRuntimeError("остаток от деления на ноль", node.line)
                return left % right
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
        if isinstance(left, list) and isinstance(right, list):
            return left == right
        return False

    BUILTIN_ARITY = {
        "len": (1, 1), "push": (2, 2), "pop": (1, 1),
        "upper": (1, 1), "lower": (1, 1),
        "abs": (1, 1), "min": (2, 2), "max": (2, 2),
        "random": (2, 2), "num": (1, 1), "input": (0, 1),
    }

    def call_builtin(self, node, env):
        name = node.name
        lo, hi = self.BUILTIN_ARITY[name]
        if not (lo <= len(node.args) <= hi):
            if lo == hi:
                expect = f"{lo} аргументов"
            else:
                expect = f"{lo}..{hi} аргументов"
            raise FoenuRuntimeError(f"{name} ждёт {expect}, получено {len(node.args)}", node.line)
        args = [self.eval(a, env) for a in node.args]

        if name == "len":
            x = args[0]
            if isinstance(x, (str, list)):
                return len(x)
            raise FoenuRuntimeError("len работает с текстом или массивом", node.line)

        if name == "push":
            lst = args[0]
            if not isinstance(lst, list):
                raise FoenuRuntimeError("push добавляет элементы только в массив", node.line)
            lst.append(args[1])
            return lst

        if name == "pop":
            lst = args[0]
            if not isinstance(lst, list):
                raise FoenuRuntimeError("pop работает только с массивом", node.line)
            if not lst:
                raise FoenuRuntimeError("pop: массив пуст", node.line)
            return lst.pop()

        if name == "upper":
            x = args[0]
            if not isinstance(x, str):
                raise FoenuRuntimeError("upper работает только с текстом", node.line)
            return x.upper()

        if name == "lower":
            x = args[0]
            if not isinstance(x, str):
                raise FoenuRuntimeError("lower работает только с текстом", node.line)
            return x.lower()

        if name == "abs":
            x = args[0]
            if not is_number(x):
                raise FoenuRuntimeError("abs работает только с числами", node.line)
            return abs(x)

        if name in ("min", "max"):
            a, b = args
            if not is_number(a) or not is_number(b):
                raise FoenuRuntimeError(f"{name} работает только с числами", node.line)
            return min(a, b) if name == "min" else max(a, b)

        if name == "random":
            a, b = args
            if not is_number(a) or not is_number(b):
                raise FoenuRuntimeError("random ждёт два числа", node.line)
            return _random.randint(int(a), int(b))

        if name == "num":
            x = args[0]
            if is_number(x):
                return x
            if isinstance(x, str):
                s = x.strip()
                try:
                    return int(s)
                except ValueError:
                    try:
                        return float(s)
                    except ValueError:
                        raise FoenuRuntimeError(f"num: текст {x!r} не похож на число", node.line) from None
            raise FoenuRuntimeError("num превращает текст в число", node.line)

        if name == "input":
            prompt = to_str(args[0]) if args else ""
            try:
                return input(prompt)
            except EOFError:
                raise FoenuRuntimeError("input: ввод закончился", node.line) from None

        raise FoenuRuntimeError(f"неизвестная встроенная функция {name!r}", node.line)

    def eval_call(self, node, env):
        if node.name in self.BUILTIN_ARITY:
            return self.call_builtin(node, env)

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
