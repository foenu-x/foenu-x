#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генератор корпуса знаний по языку Foenu-x для обучения нейросети.

Корпус (Markdown) содержит:
  - статьи об языке, архитектуре интерпретатора, статусе проекта;
  - справочники синтаксиса;
  - вопросы и ответы (FAQ);
  - типичные ошибки и их исправление;
  - множество примеров кода .foenu-x, которые реально выполняются
    интерпретатором проекта (вывод в корпусе — настоящий).

Использование:
    python tools/generate_corpus.py        # цель 40 МБ
    python tools/generate_corpus.py 0.5    # тестовый прогон
"""

import contextlib
import io
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from foenux.interpreter import run_source
from foenux.lexer import tokenize

TARGET_MB = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
OUT = ROOT / "data" / "foenu-x-corpus.md"

rnd = random.Random(20261009)

# ---------------------------------------------------------------- словари

TEXTS = [
    "Привет", "Мир", "Foenu-x", "БЕТА", "язык", "тест", "программа",
    "код", "переменная", "функция", "цикл", "условие", "вывод", "сумма",
    "результат", "готово", "друзья", "мир", "разработчик", "новичок",
    "документация", "справочник", "пример", "действие", "счёт",
]

NAMES = [
    "счётчик", "имя", "число", "результат", "итог", "сумма", "ответ",
    "глубина", "шаг", "индекс", "цена", "количество", "текст", "заголовок",
    "x", "y", "z", "n", "total", "value", "name", "score", "counter",
    "result", "length", "index", "width", "height", "price",
]

FUNCS = [
    "удвоить", "прибавить", "итог", "минимум", "степень", "обратное",
    "квадрат", "сумма_двух", "среднее", "преобразовать",
    "double", "increment", "result", "square", "combine",
]

PARAMS = ["a", "b", "x", "y", "n", "значение", "число", "шаг"]

CMDS = [
    "echo Foenu-x",
    "echo %DATE%",
    "ver",
    "cd",
    "echo 1 2 3",
    "echo BETA status",
    "powershell -Command \"Get-Location\"",
]

INTROS = [
    "Foenu-x — собственный язык программирования с синтаксисом в стиле Pascal. "
    "Программы сохраняются в файлах с расширением .foenu-x и выполняются интерпретатором на Python.",

    "Язык Foenu-x появился как учебный эксперимент: маленький, но полностью рабочий. "
    "Блоки кода заключаются в begin и end, текст записывается между символами #, "
    "а вывод выполняется командой Foenu-x.",

    "Foenu-x — минималистичный интерпретируемый язык. Он не требует компиляции: "
    "написал файл .foenu-x — запустил через main.py. Все конструкции языка описаны в справочнике ниже.",

    "Идея языка Foenu-x: сочетание читаемого синтаксиса Pascal, динамических переменных "
    "как в Python и удобного вывода в духе BASIC. Проект находится в стадии БЕТА.",

    "Foenu-x спроектирован так, чтобы новый человек мог напечатать первую программу за минуту: "
    "одна строка Foenu-x text-(#Привет!#); — и мир поздоровался в ответ.",

    "Язык Foenu-x трактует программу как последовательность инструкций, разделённых символом ;. "
    "Комментарии начинаются с двух косых черт и продолжаются до конца строки.",
]

ARCHITECTURE = [
    "Интерпретатор Foenu-x устроен в три этапа. Первый — лексер (foenux/lexer.py): "
    "он читает исходный текст и разбивает его на токены: ключевые слова, числа, текст, операторы. "
    "Второй — парсер (foenux/parser.py): из токенов строится дерево разбора (AST) методом рекурсивного спуска. "
    "Третий — интерпретатор (foenux/interpreter.py): дерево обходится и выполняется.",

    "Лексер Foenu-x работает одним регулярным выражением: на каждой позиции ищется самая подходящая "
    "запись — комментарий, ключевое слово, число, текст в #скобках#, идентификатор или оператор. "
    "Счётчик строк ведётся по переводам строки, чтобы ошибки сообщались с номером строки.",

    "Парсер написан как класс с методами на каждый уровень приоритета операторов: or_expr, and_expr, "
    "equality, comparison, term, factor, unary, primary. Такое деление даёт правильное смешивание "
    "операций: сначала and, потом or, умножение раньше сложения, а унарный минус — раньше бинарного.",

    "Интерпретатор выполняет AST через диспетчеризацию: каждая инструкция — отдельный класс-узел "
    "(Print, VarDecl, Assign, If, While, FunctionDecl, Return), а вычисление выражений вынесено "
    "в метод eval. Окружение Environment — это словарь с ссылкой на родителя, что даёт области видимости.",

    "Функции в Foenu-x — объекты Function, хранящие тело функции и окружение, в котором она была "
    "объявлена (замыкание). При вызове создаётся дочернее окружение, параметры объявляются в нём, "
    "а return выбрасывает особое исключение ReturnSignal с возвращаемым значением.",

    "Ошибки разделены на два типа: FoenuSyntaxError — проблемы чтения кода (незакрытая скобка, "
    "лишний символ), и FoenuRuntimeError — проблемы выполнения (деление на ноль, необъявленная "
    "переменная). Обе несут номер строки, чтобы программист нашёл проблему мгновенно.",
]

STATUS_TEXTS = [
    "Статус проекта Foenu-x: БЕТА. Конфигурация: 1 компьютер, 0 серверов. "
    "Интерпретатор написан на Python и не требует внешних библиотек.",

    "Сейчас Foenu-x работает в статусе БЕТА на одном компьютере: серверов нет, "
    "облака нет, всё локально. Интерпретатор — чистый Python 3, запуск — одна команда.",

    "Проект Foenu-x развивается с нуля: 1 машина, 0 серверов, статус БЕТА. "
    "Это значит, что ядро уже способно выполнять реальные программы, "
    "но API и полный набор типов ещё могут меняться.",

    "Текущее положение дел: Foenu-x 26.10.10 в стадии БЕТА. Работает офлайн, "
    "на одном компьютере, без серверной части. Всё хранится в обычных файлах .foenu-x.",
]

PLANS_TEXTS = [
    "Дорожная карта Foenu-x: ядро на C++ для скорости, расширение для VS Code "
    "с подсветкой синтаксиса, таблицы, нормальная работа со строками, "
    "возможно свёртка в байт-код. Массивы и цикл for уже сделаны в 26.10.10.",

    "Что дальше для Foenu-x: типы (int, text, bool), модули (include), "
    "стандартная библиотека, компиляция в байт-код и, может быть, серверный режим "
    "для одновременной работы нескольких пользователей. Сейчас серверов ноль — "
    "язык намеренно локальный.",

    "Планы: расширить набор встроенных функций (математика, работа с файлами), "
    "сделать REPL с многострочным редактором, добавить генератор документации "
    "и, при желании, перенести горячие пути на C++.",
]

START_TEXTS = [
    "Чтобы начать работу с Foenu-x, достаточно Python 3.8+. Склонируй или скопируй папку проекта, "
    "открой терминал, перейди в каталог foenu-x и выполни python main.py examples\\hello.foenu-x.",

    "Первые шаги: создай файл my.foenu-x, напиши внутри Foenu-x text-(#Привет!#); "
    "и запусти python main.py my.foenu-x. Аргументов и библиотек устанавливать не нужно.",

    "Быстрый старт Foenu-x: 1) убедись, что установлен Python 3; "
    "2) запусти python main.py без аргументов — откроется REPL; "
    "3) набери Foenu-x text-(#Hello#); и нажми Enter. Для выхода — exit.",
]

QA_POOL = [
    ("Что такое Foenu-x?",
     "Foenu-x — собственный язык программирования. Интерпретатор написан на Python, "
     "синтаксис в стиле Pascal (begin/end), файлы имеют расширение .foenu-x, статус проекта — БЕТА."),
    ("Какое расширение у файлов языка?",
     "Расширение — .foenu-x. Именно такие файлы читает команда python main.py <файл>."),
    ("На каком языке написан интерпретатор?",
     "Интерпретатор написан на чистом Python 3 (без сторонних библиотек): лексер, парсер и исполнитель."),
    ("Какой статус проекта?",
     "Статус: БЕТА. Работает на 1 компьютере, серверов нет, всё локально."),
    ("Есть ли у языка серверная часть?",
     "Нет. 0 серверов: Foenu-x полностью локальный, файл запускается напрямую через интерпретатор."),
    ("Как вывести текст на экран?",
     "Командой Foenu-x: Foenu-x text-(#Привет, мир!#);. Текст заключён между символами #."),
    ("Что делает конструкция text-(...)?",
     "text-(выражение) превращает любое значение в текст: число станет строкой, результат вычисления — тоже."),
    ("Как объявить переменную?",
     "Через var: var счётчик be 0;. Тип указывать не нужно — переменная динамическая."),
    ("Чем отличается be от :=?",
     "be объявляет новую переменную (var x be 1;), а := переприсваивает значение уже существующей (x := 2;)."),
    ("Как записать условие?",
     "if условие then begin ... end else begin ... end;. Ключевое слово else необязательно."),
    ("Как записать цикл?",
     "while условие begin ... end;. Внутри можно менять переменные, участвующие в условии."),
    ("Как объявить функцию?",
     "function имя(параметры) begin ... return результат; end;. Вызов — имя(аргументы);."),
    ("Поддерживается ли рекурсия?",
     "Да. Функция может вызывать саму себя: замыкание хранит окружение, где функция была объявлена."),
    ("Как запустить команду операционной системы?",
     "Через CMD: CMD(#echo привет#);. Аргумент — обычный текст, команда выполняется средствами оболочки."),
    ("Какой приоритет у операторов?",
     "Сначала and, затем or, затем сравнения = и !=, потом > < >= <=, затем + -, потом * /, "
     "потом унарный минус и not, в конце — вызовы функций и скобки."),
    ("Поддерживаются ли дробные числа?",
     "Да: var доля be 2.5;. Арифметика смешивает целые и дробные, результат становится дробным."),
    ("Что будет при делении на ноль?",
     "Интерпретатор выдаст ошибку: Строка N: деление на ноль. Проверяй делитель перед операцией."),
    ("Можно ли сравнивать тексты?",
     "Да, сравнивается лексикографический порядок: if #аб# < #ба# then ... сработает."),
    ("Как писать комментарии?",
     "Двойной косой чертой: // это комментарий. Комментарий идёт до конца строки."),
    ("Как открыть REPL?",
     "Выполни python main.py без аргументов. Команды вводятся построчно, многострочные блоки "
     "begin/end буферизируются автоматически. Выход — exit."),
    ("Нужно ли ставить точку с запятой?",
     "Точка с запятой ставится после инструкций и необязательна: парсер её принимает, но и пропустит."),
    ("Работает ли кириллица в именах?",
     "Да: var счётчик be 10; — полноценная инструкция. Идентификаторы могут содержать буквы русского алфавита."),
    ("Есть ли типы данных?",
     "Нет статических типов: значения бывают числом, текстом или логическим (true/false). "
     "Тип определяется во время выполнения."),
    ("Как склеить текст и число?",
     "Оператором +: если один из операндов текст, происходит склейка: text-(#Число: #) + 42."),
    ("Что выведет Foenu-x 10 / 4?",
     "2.5: целоченное деление с остатком даёт дробный результат, точное — целое (10 / 2 = 5)."),
    ("Где лежат примеры?",
     "В папке examples/ проекта: hello.foenu-x, vars.foenu-x, functions.foenu-x, cmd.foenu-x, test_all.foenu-x."),
    ("Как запустить пример?",
     "python main.py examples\\vars.foenu-x — и увидишь вывод программы."),
    ("Можно ли вкладывать begin/end?",
     "Да, блоки вкладываются: условия внутри циклов, циклы внутри функций — всё поддерживается."),
    ("Что делает return?",
     "return возвращает значение из функции и сразу прекращает её выполнение. "
     "Без return функция вернёт nil."),
    ("Как выглядит Hello World?",
     "Foenu-x text-(#Hello, World!#); — одна строка, один вывод."),
    ("Есть ли логические операторы?",
     "Да: and, or, not, а значения true и false. Условия приводятся к истинности: ноль и пустой текст — ложь."),
    ("Что такое nil?",
     "nil — значение, которое возвращает функция без return. Так оно и печатается."),
    ("Как обрабатываются ошибки?",
     "Сообщение содержит номер строки: «Строка 3: переменная 'x' не объявлена». "
     "Синтаксические ошибки ловит парсер, смысловые — интерпретатор."),
    ("Компилируется ли Foenu-x?",
     "Нет, это интерпретируемый язык: код читается, разбирается на токены и выполняется напрямую."),
    ("Можно ли запускать Foenu-x на сервере?",
     "Технически да — это обычный скрипт на Python. Но в проекте 0 серверов: "
     "штатный режим — один локальный компьютер."),
    ("Как создать массив?",
     "Через квадратные скобки: var числа be [1, 2, 3];. Элементы разделяются запятыми, пустой массив — []."),
    ("Как обратиться к элементу массива?",
     "Через индекс в скобках: числа[0] — первый элемент. Счёт с нуля: первый элемент — 0, второй — 1."),
    ("Как изменить элемент массива?",
     "Присваиванием по индексу: числа[1] := 99;. Работает и чтение: Foenu-x числа[1];."),
    ("Как узнать длину массива или текста?",
     "Встроенной функцией len: len([1, 2, 3]) → 3, len(#привет#) → 6."),
    ("Как добавить и убрать элемент?",
     "push(массив, элемент) добавляет в конец, pop(массив) убирает последний и возвращает его."),
    ("Есть ли цикл со счётчиком?",
     "Да: for i := 1 to 5 begin ... end; — вперёд, for i := 5 downto 1 begin ... end; — назад. "
     "Границы включаются в цикл."),
    ("Что делают break и continue?",
     "break немедленно выходит из цикла, continue пропускает текущую итерацию и переходит к следующей."),
    ("Есть ли остаток от деления?",
     "Да, оператор %: 17 % 5 даёт 2. Приоритет такой же, как у * и /."),
    ("Какие встроенные функции есть?",
     "len, push, pop, upper, lower, abs, min, max, random(от, до), num(текст→число), input(приглашение)."),
    ("Как читать ввод пользователя?",
     "Функцией input: var ответ be input(#Твоё число: #);. Она возвращает текст — для сравнения с числом "
     "преврати его: num(ответ)."),
    ("Есть ли случайные числа?",
     "Да: random(1, 10) возвращает случайное целое от 1 до 10 включительно."),
    ("Можно ли индексировать текст?",
     "Да: #привет# [0] даёт один символ #п#. Изменить символ текста нельзя — только читать."),
]

ERRORS = [
    (
        "if x > 5 then begin\n  Foenu-x text-(#да#);\n",
        "Не закрыт блок: где else и end? Парсер выдаст «незакрытый блок: не хватает end».",
        "if x > 5 then begin\n  Foenu-x text-(#да#);\nend;\n",
    ),
    (
        "var x be 5\nx = 10;\nFoenu-x x;\n",
        "Присваивание в Foenu-x пишется через :=, а = — это сравнение.",
        "var x be 5;\nx := 10;\nFoenu-x x;\n",
    ),
    (
        "Foenu-x text-(#нет парного #);\n",
        "Текстовый литерал должен быть закрыт вторым символом # на той же строке.",
        "Foenu-x text-(#закрытый текст#);\n",
    ),
    (
        "Foenu-x недекларированная;\n",
        "Переменную нужно объявить до использования: var имя be значение;.",
        "var недекларированная be 1;\nFoenu-x недекларированная;\n",
    ),
    (
        "var делитель be 0;\nFoenu-x 100 / делитель;\n",
        "Деление на ноль — ошибка времени выполнения. Проверяй знаменатель.",
        "var делитель be 5;\nFoenu-x 100 / делитель;\n",
    ),
    (
        "Foenu-x текст + 5;\n",
        "Сравнение текста и числа запрещено, но + со склейкой работает: сначала преврати число в текст.",
        "Foenu-x text-(#значение: #) + 5;\n",
    ),
    (
        "while x begin\n  Foenu-x x;\nend;\n",
        "Условие while должно быть логическим выражением: x > 0, x < 10 и т. п.",
        "var x be 3;\nwhile x > 0 begin\n  Foenu-x x;\n  x := x - 1;\nend;\n",
    ),
    (
        "function f(a a) begin\n  return a;\nend;\n",
        "Параметры перечисляются через запятую: f(a, b).",
        "function f(a, b) begin\n  return a + b;\nend;\n",
    ),
    (
        "Foenu-x text-(#ошибка#)\n",
        "Инструкции принято закрывать ; — парсер её пропустит, но стиль проекта требует точку с запятой.",
        "Foenu-x text-(#ошибка#);\n",
    ),
    (
        "Foenu-x (1 + 2;\n",
        "Не закрыта скобка: каждая ( должна иметь парную ).",
        "Foenu-x (1 + 2);\n",
    ),
    (
        "var a be [1, 2, 3];\nFoenu-x a[5];\n",
        "Индекс вне диапазона: у массива из 3 элементов допустимы индексы 0..2.",
        "var a be [1, 2, 3];\nFoenu-x a[0];\n",
    ),
    (
        "for i := 1 5 begin\n  Foenu-x i;\nend;\n",
        "После первой границы цикла обязательно to (вперёд) или downto (назад).",
        "for i := 1 to 5 begin\n  Foenu-x i;\nend;\n",
    ),
]

ARTICLES = [
    ("Обзор языка", lambda: "\n\n".join(rnd.sample(INTROS, 2))),
    ("Архитектура интерпретатора", lambda: "\n\n".join(rnd.sample(ARCHITECTURE, 2))),
    ("Статус проекта", lambda: rnd.choice(STATUS_TEXTS) + "\n\n" + rnd.choice(PLANS_TEXTS)),
    ("Планы развития", lambda: rnd.choice(PLANS_TEXTS)),
    ("Быстрый старт", lambda: "\n\n".join(rnd.sample(START_TEXTS, 2))),
    ("Философия языка", lambda: (
        "Foenu-x маленький намеренно: чем меньше конструкций, тем быстрее человек понимает, "
        "как работает интерпретатор под капотом. Каждая фича языка — это повод заглядывать "
        "в исходники lexer.py, parser.py и interpreter.py и видеть её устройство целиком.\n\n"
        + rnd.choice(INTROS)
    )),
    ("Сравнение с другими языками", lambda: (
        "По духу Foenu-x напоминает Pascal (begin/end, var, function, return), "
        "по гибкости переменных — Python (типы не объявляются), "
        "по выводу — BASIC (Foenu-x print). Отличие — собственные литералы текста в #скобках# "
        "и команда CMD для запуска системных команд прямо из программы.\n\n" + rnd.choice(INTROS)
    )),
    ("Устройство файлов проекта", lambda: (
        "Проект foenu-x состоит из четырёх файлов кода: main.py (CLI и REPL), "
        "foenux/lexer.py (токенизатор), foenux/parser.py (AST и парсер), "
        "foenux/interpreter.py (выполнение). Папка examples/ хранит готовые программы, "
        "tools/ — утилиты разработки, data/ — сгенерированные материалы.\n\n" + rnd.choice(ARCHITECTURE)
    )),
    ("Что нового в v26.10.10", lambda: (
        "Релиз 26.10.10 (номер по дате) добавил в Foenu-x массивы [1, 2, 3] с индексацией "
        "с нуля и изменением элементов, цикл со счётчиком for i := от to до "
        "и обратный вариант downto, операторы break и continue, остаток от деления %, "
        "встроенные функции len, push, pop, upper, lower, abs, min, max, random, num "
        "и чтение ввода input(приглашение).\n\n"
        "На практике это значит: можно писать игры (guess_game.foenu-x — угадай число "
        "на input, random и num), обрабатывать списки данных, искать элементы, "
        "суммировать массивы через for. Раньше такие программы писались только "
        "на голых переменных и while.\n\n"
        "Технически: лексер научился токенам [ ] % и словам for/to/downto/break/continue, "
        "в парсере появились узлы ListNode, Index, IndexAssign, For, Break, Continue, "
        "а интерпретатор получил встроенные функции (BUILTIN_ARITY) и сигналы "
        "BreakSignal/ContinueSignal для выхода из цикла."
    )),
]

REFERENCE_ROWS = [
    ("Комментарий", "`// текст`"),
    ("Текст", "`#любой текст#`"),
    ("Вывод", "`Foenu-x выражение;`"),
    ("В текст", "`text-(выражение)`"),
    ("Переменная", "`var имя be значение;`"),
    ("Присваивание", "`имя := значение;`"),
    ("Массив", "`var a be [1, 2, 3];`"),
    ("Элемент массива", "`a[0]`"),
    ("Изменить элемент", "`a[0] := 5;`"),
    ("Условие", "`if ... then begin ... end else begin ... end;`"),
    ("Цикл", "`while условие begin ... end;`"),
    ("Цикл со счётчиком", "`for i := 1 to 5 begin ... end;`"),
    ("Обратный отсчёт", "`for i := 5 downto 1 begin ... end;`"),
    ("Выход из цикла", "`break;` и `continue;`"),
    ("Функция", "`function имя(арг) begin ... end;`"),
    ("Возврат", "`return значение;`"),
    ("Команда ОС", "`CMD(#команда#);`"),
    ("Ввод", "`input(#приглашение#)`"),
    ("Встроенные функции", "`len push pop upper lower abs min max random num`"),
    ("Логика", "`and`, `or`, `not`, `true`, `false`"),
    ("Арифметика", "`+ - * /` и остаток `%`"),
    ("Сравнение", "`= == !=` `> < >= <=`"),
    ("Скобки", "`( )` и `[ ]`"),
]

CHANGELOG = [
    "0.1 — появились токенизатор и вывод Foenu-x text-(...);",
    "0.2 — добавлены переменные var ... be и оператор :=;",
    "0.3 — реализованы if/then/else и while с begin/end;",
    "0.4 — появились функции и return;",
    "0.5 — добавлена команда CMD для запуска оболочки;",
    "0.6 — поддержаны кириллические идентификаторы;",
    "0.7 — введены текстовые литералы #...# и text-(...);",
    "0.8 — REPL с многострочным буфером begin/end;",
    "0.9 — понятные сообщения об ошибках с номерами строк;",
    "1.0 — выход в статус БЕТА: 1 компьютер, 0 серверов.",
    "26.10.10 — массивы [ ] и индексы, цикл for с to/downto, break и continue, "
    "оператор остатка %, встроенные функции (len, push, pop, upper, lower, abs, "
    "min, max, random, num), ввод input(); версия стала по дате релиза.",
]

EN_TEXTS = [
    "Foenu-x is a small experimental programming language with Pascal-like syntax. "
    "Programs are stored in files with the .foenu-x extension and executed by a Python interpreter.",

    "The Foenu-x interpreter is a classic three-stage pipeline: lexer, recursive-descent parser, "
    "and tree-walking evaluator. Each stage lives in its own module for clarity.",

    "In Foenu-x, text literals are wrapped in hash signs: text-(#Hello#). "
    "The print statement is the language name itself: Foenu-x expression.",

    "Foenu-x variables are dynamic. Declare them with var name be value, "
    "reassign with the := operator, and never worry about types again.",

    "Status: BETA. The project runs on a single computer with zero servers — "
    "everything is local, offline, and dependency-free.",

    "Control flow in Foenu-x follows Pascal: if condition then begin ... end else begin ... end, "
    "and while condition begin ... end. Blocks always close with the end keyword.",

    "Functions are first-class in the interpreter: they capture their defining environment, "
    "support recursion, and return values through the return statement.",

    "The CMD statement executes a shell command: CMD(#echo hi#); — "
    "the standard output of the command is printed to the console.",

    "Version 26.10.10 added arrays with zero-based indexing, the for loop with to "
    "and downto directions, break and continue, the modulo operator %, and built-in "
    "functions such as len, push, pop, upper, lower, abs, min, max, random and num.",

    "Reading user input is done with input: var answer be input(#Your number: #); "
    "It returns text, so convert it with num() before comparing with numbers. "
    "Together with random(1, 10) this is enough to write a guessing game.",
]


# ------------------------------------------------------- работа с кодом

def pick(count, *exclude):
    """Выбрать count различных имён переменных, исключая заданные."""
    pool = [n for n in NAMES if n not in exclude]
    return rnd.sample(pool, count)


def pick_params(count, *exclude):
    pool = [p for p in PARAMS if p not in exclude]
    return rnd.sample(pool, count)


def run_capture(code):
    """Выполнить программу Foenu-x и вернуть вывод (или None при ошибке)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            run_source(code)
    except Exception:
        return None
    return buf.getvalue().rstrip("\n")


def token_listing(src):
    try:
        toks = tokenize(src)
    except Exception:
        return ""
    rows = []
    for t in toks:
        if t.type == "EOF":
            continue
        value = t.value.replace("\n", "\\n")
        rows.append(f"{t.line:>3}  {t.type:<8} {value}")
    if not rows:
        return ""
    return "\n**Токены (листинг лексера):**\n\n```\n" + "\n".join(rows) + "\n```\n"


def code_section(code, runnable=True, with_tokens=False, comment=""):
    out = ""
    if comment:
        out += comment + "\n\n"
    out += "```foenu-x\n" + code.rstrip("\n") + "\n```\n"
    if runnable:
        result = run_capture(code)
        if result is not None:
            out += "\n**Фактический вывод интерпретатора:**\n\n```\n" + result + "\n```\n"
    else:
        out += "\n_Вывод зависит от операционной системы и не воспроизводится в корпусе._\n"
    if with_tokens:
        out += token_listing(code)
    return out


# ------------------------------------------------------- генераторы кода

def gen_prints():
    lines = ["// Вывод текста, чисел и их комбинаций"]
    used = set()
    for _ in range(rnd.randint(2, 5)):
        style = rnd.randrange(5)
        t = rnd.choice(TEXTS)
        n = rnd.randint(-50, 999)
        if style == 0:
            lines.append(f"Foenu-x text-(#{t}#);")
        elif style == 1:
            lines.append(f"Foenu-x {n};")
        elif style == 2:
            lines.append(f"Foenu-x text-(#{t}: #) + {n};")
        elif style == 3:
            free = [x for x in NAMES if x not in used]
            if not free:
                lines.append(f"Foenu-x text-(#{t}: #) + {n};")
                continue
            v = rnd.choice(free)
            used.add(v)
            lines.append(f"var {v} be #{t}#;\nFoenu-x text-(#{t} | #) + {v};")
        else:
            lines.append(f"Foenu-x text-(#{t}#) + text-(# #) + text-(#{t}#);")
    return "\n".join(lines), True


def gen_vars():
    a = rnd.randint(0, 100)
    b = rnd.randint(1, 50)
    op = rnd.choice(["+", "-", "*"])
    v1, v2, vr = pick(3)
    code = (
        "// Переменные и вычисления\n"
        f"var {v1} be {a};\n"
        f"var {v2} be {b};\n"
        f"var {vr} be {v1} {op} {v2};\n"
        f"Foenu-x text-(#{v1} = #) + {v1};\n"
        f"Foenu-x text-(#{v2} = #) + {v2};\n"
        f"Foenu-x text-(#итог: #) + {vr};\n"
        f"{vr} := {v1} + {v2};\n"
        f"Foenu-x text-(#после переприсваивания: #) + {vr};"
    )
    return code, True


def gen_if():
    x = rnd.randint(0, 30)
    k = rnd.randint(0, 30)
    t1, t2 = rnd.sample(TEXTS, 2)
    v = rnd.choice(NAMES)
    op = rnd.choice([">", "<", ">=", "<=", "=", "!="])
    code = (
        "// Условие if / then / else\n"
        f"var {v} be {x};\n"
        f"if {v} {op} {k} then begin\n"
        f"  Foenu-x text-(#{t1}: #) + {v};\n"
        f"end else begin\n"
        f"  Foenu-x text-(#{t2}: #) + {v};\n"
        f"end;"
    )
    return code, True


def gen_while():
    n = rnd.randint(2, 8)
    mode = rnd.randrange(3)
    if mode == 0:
        (v,) = pick(1)
        code = (
            "// Обратный отсчёт\n"
            f"var {v} be {n};\n"
            f"while {v} > 0 begin\n"
            f"  Foenu-x text-(#шаг #) + {v};\n"
            f"  {v} := {v} - 1;\n"
            f"end;\n"
            f"Foenu-x text-(#конец#);"
        )
    elif mode == 1:
        v, acc = pick(2)
        code = (
            "// Накопление суммы\n"
            f"var {v} be 0;\n"
            f"var {acc} be {n};\n"
            f"while {acc} > 0 begin\n"
            f"  {v} := {v} + {acc};\n"
            f"  {acc} := {acc} - 1;\n"
            f"end;\n"
            f"Foenu-x text-(#сумма от 1 до {n}: #) + {v};"
        )
    else:
        v, acc, res = pick(3)
        code = (
            "// Умножение повторением\n"
            f"var {v} be {rnd.randint(2, 9)};\n"
            f"var {acc} be {n};\n"
            f"var {res} be 1;\n"
            f"while {acc} > 0 begin\n"
            f"  {res} := {res} * {v};\n"
            f"  {acc} := {acc} - 1;\n"
            f"end;\n"
            f"Foenu-x text-(#степень: #) + {res};"
        )
    return code, True


def gen_func():
    kind = rnd.randrange(4)
    f = rnd.choice(FUNCS)
    a = rnd.randint(1, 9)
    b = rnd.randint(1, 9)
    if kind == 0:
        (p,) = pick_params(1)
        code = (
            "// Функция с одним параметром\n"
            f"function {f}({p}) begin\n"
            f"  return {p} * {rnd.randint(2, 9)} + {rnd.randint(0, 20)};\n"
            f"end;\n"
            f"Foenu-x {f}({a});\n"
            f"Foenu-x {f}({b});"
        )
    elif kind == 1:
        p, step = pick_params(2)
        code = (
            "// Функция с двумя параметрами\n"
            f"function {f}({p}, {step}) begin\n"
            f"  return {p} + {step};\n"
            f"end;\n"
            f"Foenu-x {f}({a}, {b});\n"
            f"Foenu-x {f}({a}, {b}) * 10;"
        )
    elif kind == 2:
        code = (
            "// Рекурсия: сумма чисел от 1 до n\n"
            "function сумма_до(n) begin\n"
            "  if n <= 1 then begin\n"
            "    return 1;\n"
            "  end;\n"
            "  return n + сумма_до(n - 1);\n"
            "end;\n"
            f"Foenu-x сумма_до({rnd.randint(2, 9)});"
        )
    else:
        code = (
            "// Рекурсия: факториал\n"
            "function факториал(n) begin\n"
            "  if n <= 1 then begin\n"
            "    return 1;\n"
            "  end;\n"
            "  return n * факториал(n - 1);\n"
            "end;\n"
            f"Foenu-x факториал({rnd.randint(2, 7)});"
        )
    return code, True


def gen_cmd():
    picked = rnd.sample(CMDS, k=rnd.randint(1, 3))
    lines = ["// Запуск команд операционной системы"]
    for c in picked:
        lines.append(f"CMD(#{c}#);")
    return "\n".join(lines), False


def gen_mixed():
    f_pool = [x for x in FUNCS if x not in NAMES]
    f = rnd.choice(f_pool)
    (v,) = pick(1, "итог")
    n = rnd.randint(3, 7)
    t = rnd.choice(TEXTS)
    code = (
        "// Комбинированная программа: функция + цикл + условие\n"
        f"function {f}(x) begin\n"
        "  if x > 4 then begin\n"
        "    return x * 2;\n"
        "  end else begin\n"
        "    return x + 5;\n"
        "  end;\n"
        "end;\n"
        "\n"
        f"var {v} be 1;\n"
        f"var итог be 0;\n"
        f"while {v} <= {n} begin\n"
        f"  итог := итог + {f}({v});\n"
        f"  {v} := {v} + 1;\n"
        "end;\n"
        f"Foenu-x text-(#{t}: #) + итог;"
    )
    return code, True


def gen_text_ops():
    t1, t2, t3 = rnd.sample(TEXTS, 3)
    n = rnd.randint(1, 99)
    v = rnd.choice(NAMES)
    code = (
        "// Текст: склейка и преобразование\n"
        f"var {v} be {n};\n"
        f"Foenu-x text-(#{t1} #) + {v};\n"
        f"Foenu-x text-(#{t1}#) + text-(# #) + text-(#{t2}#) + text-(# #) + text-(#{t3}#);\n"
        f"Foenu-x text-(#как текст: #) + text-({v});"
    )
    return code, True


def gen_arrays():
    vals = [rnd.randint(1, 99) for _ in range(rnd.randint(3, 5))]
    lst = ", ".join(str(v) for v in vals)
    (acc,) = pick(1, "индекс")
    mode = rnd.randrange(3)
    if mode == 0:
        body = (
            f"var числа be [{lst}];\n"
            f"var {acc} be 0;\n"
            "for i := 0 to len(числа) - 1 begin\n"
            f"  {acc} := {acc} + числа[i];\n"
            "end;\n"
            f"Foenu-x text-(#сумма: #) + {acc};\n"
            f"Foenu-x text-(#длина: #) + len(числа);"
        )
    elif mode == 1:
        (idx,) = pick(1, "значение")
        body = (
            f"var числа be [{lst}];\n"
            f"var {idx} be {rnd.randint(0, len(vals) - 1)};\n"
            "числа[0] := 100;\n"
            f"Foenu-x text-(#первый: #) + числа[0];\n"
            f"Foenu-x text-(#элемент {idx}: #) + числа[{idx}];"
        )
    else:
        body = (
            f"var данные be [{lst}];\n"
            "push(данные, 777);\n"
            f"Foenu-x text-(#длина с push: #) + len(данные);\n"
            "Foenu-x pop(данные);\n"
            f"Foenu-x text-(#длина с pop: #) + len(данные);"
        )
    code = "// Массивы: создание, индексы, push и pop\n" + body
    return code, True


def gen_for():
    n = rnd.randint(3, 7)
    mode = rnd.randrange(3)
    if mode == 0:
        code = (
            "// Цикл for с нарастающим счётчиком\n"
            "var сумма be 0;\n"
            f"for i := 1 to {n} begin\n"
            "  сумма := сумма + i;\n"
            "end;\n"
            f"Foenu-x text-(#сумма 1..{n}: #) + сумма;"
        )
    elif mode == 1:
        code = (
            "// Обратный цикл downto\n"
            f"for i := {n} downto 1 begin\n"
            "  Foenu-x text-(#осталось #) + i;\n"
            "end;\n"
            "Foenu-x text-(#поехали#);"
        )
    else:
        code = (
            "// Цикл for по встроенной функции len\n"
            f"var строка be #{rnd.choice(TEXTS)}#;\n"
            "for i := 0 to len(строка) - 1 begin\n"
            "  Foenu-x строка[i];\n"
            "end;"
        )
    return code, True


def gen_break():
    limit = rnd.randint(3, 6)
    mode = rnd.randrange(3)
    if mode == 0:
        code = (
            "// break выходит из цикла\n"
            f"for i := 1 to 100 begin\n"
            f"  if i = {limit} then begin\n"
            "    Foenu-x text-(#хватит: #) + i;\n"
            "    break;\n"
            "  end;\n"
            "end;\n"
            "Foenu-x text-(#после цикла#);"
        )
    elif mode == 1:
        code = (
            "// continue пропускает нечётные\n"
            "var чётная_сумма be 0;\n"
            "for i := 1 to 10 begin\n"
            "  if i % 2 != 0 then begin\n"
            "    continue;\n"
            "  end;\n"
            "  чётная_сумма := чётная_сумма + i;\n"
            "end;\n"
            "Foenu-x text-(#сумма чётных: #) + чётная_сумма;"
        )
    else:
        code = (
            "// break в while\n"
            f"var осталось be {limit};\n"
            "while true begin\n"
            "  осталось := осталось - 1;\n"
            "  if осталось = 0 then begin\n"
            "    break;\n"
            "  end;\n"
            "end;\n"
            "Foenu-x text-(#готово#);"
        )
    return code, True


def gen_builtins():
    mode = rnd.randrange(4)
    t = rnd.choice(TEXTS)
    a = rnd.randint(1, 30)
    if mode == 0:
        code = (
            "// Текстовые функции\n"
            f"Foenu-x upper(#{t}#);\n"
            f"Foenu-x lower(#{t.upper()}#);\n"
            f"Foenu-x len(#{t}#);"
        )
    elif mode == 1:
        code = (
            "// Математические функции\n"
            f"Foenu-x abs({-a});\n"
            f"Foenu-x min({a}, {a + rnd.randint(1, 20)});\n"
            f"Foenu-x max({a}, {a + rnd.randint(1, 20)});"
        )
    elif mode == 2:
        code = (
            "// Случайное число\n"
            "var бросок be random(1, 6);\n"
            "Foenu-x text-(#бросок кубика: #) + бросок;"
        )
    else:
        code = (
            "// num превращает текст в число\n"
            f"var текст be #{a}#;\n"
            "Foenu-x num(текст) + 1;"
        )
    return code, True


PROGRAM_GENS = [
    (gen_prints, 3),
    (gen_vars, 3),
    (gen_if, 3),
    (gen_while, 3),
    (gen_func, 3),
    (gen_cmd, 1),
    (gen_mixed, 2),
    (gen_text_ops, 2),
    (gen_arrays, 3),
    (gen_for, 3),
    (gen_break, 2),
    (gen_builtins, 3),
]

PROGRAM_FUNCS = [g for g, w in PROGRAM_GENS]
PROGRAM_WEIGHTS = [w for g, w in PROGRAM_GENS]


# ------------------------------------------------------- секции корпуса

def section_article(i):
    title, builder = rnd.choice(ARTICLES)
    return f"\n---\n\n## Раздел {i}. {title}\n\n{builder()}\n"


def section_reference(i):
    rows = rnd.sample(REFERENCE_ROWS, k=rnd.randint(6, len(REFERENCE_ROWS)))
    head = f"\n---\n\n## Раздел {i}. Справочник синтаксиса\n\n"
    head += "| Конструкция | Запись |\n|---|---|\n"
    head += "\n".join(f"| {a} | {b} |" for a, b in rows)
    head += "\n"
    if rnd.random() < 0.5:
        head += "\nПриоритет операторов (от низшего к высшему): `or` → `and` → `= == !=` → `> < >= <=` → `+ -` → `* /` → унарные → вызовы и скобки.\n"
    return head


def section_qa(i):
    picked = rnd.sample(QA_POOL, k=rnd.randint(3, 7))
    out = f"\n---\n\n## Раздел {i}. Вопросы и ответы\n\n"
    for q, a in picked:
        out += f"**В:** {q}\n\n**О:** {a}\n\n"
    return out


def section_errors(i):
    wrong, why, right = rnd.choice(ERRORS)
    out = f"\n---\n\n## Раздел {i}. Типичная ошибка\n\n"
    out += "**Неправильно:**\n\n```foenu-x\n" + wrong.rstrip("\n") + "\n```\n\n"
    out += f"**Почему это ошибка:** {why}\n\n"
    out += "**Как исправить:**\n\n```foenu-x\n" + right.rstrip("\n") + "\n```\n"
    return out


def section_program(i):
    gen = rnd.choices(PROGRAM_FUNCS, weights=PROGRAM_WEIGHTS, k=1)[0]
    code, runnable = gen()
    with_tokens = rnd.random() < 0.18
    comment = rnd.choice([
        "**Пример программы на Foenu-x.**",
        "**Разбор примера.**",
        "Ниже — программа, выполненная интерпретатором проекта:",
        "**Практика:** попробуй изменить числа и предсказать вывод.",
        "",
    ])
    out = f"\n---\n\n## Раздел {i}. Пример программы\n\n"
    out += code_section(code, runnable=runnable, with_tokens=with_tokens, comment=comment)
    return out


def section_changelog(i):
    picks = rnd.sample(CHANGELOG, k=rnd.randint(4, len(CHANGELOG)))
    picks.sort(key=lambda s: tuple(int(x) for x in s.split(" ")[0].split(".")))
    out = f"\n---\n\n## Раздел {i}. История версий Foenu-x\n\n"
    out += "\n".join(f"- {p}" for p in picks)
    out += "\n\nТекущая версия — 26.10.10, статус БЕТА.\n"
    return out


def section_english(i):
    picks = rnd.sample(EN_TEXTS, k=rnd.randint(2, 4))
    out = f"\n---\n\n## Раздел {i}. Foenu-x in English\n\n"
    out += "\n\n".join(picks) + "\n"
    return out


SECTION_GENS = [
    (section_article, 3),
    (section_reference, 2),
    (section_qa, 3),
    (section_errors, 2),
    (section_program, 6),
    (section_changelog, 1),
    (section_english, 2),
]
SECTION_FUNCS = [g for g, w in SECTION_GENS]
SECTION_WEIGHTS = [w for g, w in SECTION_GENS]


def build_header():
    return f"""# Foenu-x — корпус знаний языка программирования

Документ сгенерирован автоматически (tools/generate_corpus.py) как обучающий
материал для нейросети. Содержит статьи, справочники, вопросы и ответы,
типичные ошибки и множество примеров кода. Все примеры выполнены настоящим
интерпретатором языка, поэтому вывод корректен.

## Метаданные проекта

| Поле | Значение |
|---|---|
| Название языка | Foenu-x |
| Версия | **26.10.10** |
| Расширение файлов | `.foenu-x` |
| Интерпретатор | Python 3 (лексер → парсер → исполнитель) |
| Синтаксис | Pascal-стиль: `begin` / `end` |
| Вывод | `Foenu-x выражение;` |
| Текст | `#литерал#`, преобразование `text-(...)` |
| Команды ОС | `CMD(#команда#)` |
| Статус | **БЕТА** |
| Инфраструктура | 1 компьютер, 0 серверов, всё локально |
| Пример запуска | `python main.py examples\\hello.foenu-x` |

## Пример первой программы

```foenu-x
// hello.foenu-x
Foenu-x text-(#Hello, World!#);

var имя be #Foenu-x#;
var счётчик be 3;

while счётчик > 0 begin
  Foenu-x text-(#Привет, #) + имя;
  счётчик := счётчик - 1;
end;
```

Ниже — корпус из сгенерированных разделов.
"""


def main():
    target = int(TARGET_MB * 1024 * 1024)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    section = 0

    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        header = build_header()
        f.write(header)
        written += len(header.encode("utf-8"))

        while written < target:
            section += 1
            gen = rnd.choices(SECTION_FUNCS, weights=SECTION_WEIGHTS, k=1)[0]
            block = gen(section)
            f.write(block)
            written += len(block.encode("utf-8"))
            if section % 200 == 0:
                print(
                    f"[генератор] разделов: {section}, "
                    f"размер: {written / 1024 / 1024:.2f} / {TARGET_MB:.1f} МБ",
                    file=sys.stderr,
                    flush=True,
                )

        footer = (
            "\n---\n\n## Конец корпуса\n\n"
            "Корпус Foenu-x завершён. Краткая сводка: язык Foenu-x, расширение .foenu-x, "
            "интерпретатор на Python, синтаксис begin/end, статус БЕТА, "
            "1 компьютер, 0 серверов.\n"
        )
        f.write(footer)
        written += len(footer.encode("utf-8"))

    print(f"[генератор] готово: {OUT}")
    print(f"[генератор] разделов: {section}")
    print(f"[генератор] размер: {written} байт ({written / 1024 / 1024:.2f} МБ)")


if __name__ == "__main__":
    main()
