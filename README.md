# Foenu-x

Свой язык программирования. Интерпретатор на Python, синтаксис в стиле Pascal (`begin`/`end`), текст в `#скобках#`, запуск команд оболочки через `CMD(...)`.

- Расширение файлов: **`.foenu-x`**
- Версия: **1.0**

## Запуск

```powershell
cd "Python Проекты\foenu-x"

python main.py examples\hello.foenu-x   # выполнить файл
python main.py                          # REPL (для выхода: exit)
```

Нужен Python 3.8+. Дополнительных библиотек нет.

## Пример

```pascal
// hello.foenu-x
Foenu-x text-(#Hello, World!#);

var имя be #Foenu-x#;
var счётчик be 3;

while счётчик > 0 begin
  Foenu-x text-(#Привет, #) + имя;
  счётчик := счётчик - 1;
end;

CMD(#echo команда выполнена#);
```

## Синтаксис

| Конструкция | Запись |
|---|---|
| Комментарий | `// текст` |
| Текст | `#любой текст#` |
| Вывод | `Foenu-x выражение;` |
| В текст | `text-(выражение)` |
| Переменная | `var имя be значение;` |
| Присваивание | `имя := значение;` |
| Условие | `if ... then begin ... end else begin ... end;` |
| Цикл | `while условие begin ... end;` |
| Функция | `function имя(арг) begin ... end;` |
| Возврат | `return значение;` |
| Команда ОС | `CMD(#команда#);` |
| Логика | `and`, `or`, `not`, `true`, `false` |
| Операторы | `+ - * /`, `= == !=`, `> < >= <=` |

## Структура проекта

```
foenu-x/
├── main.py              # CLI + REPL
├── foenux/
│   ├── lexer.py         # токенизатор
│   ├── parser.py        # AST + рекурсивный спуск
│   └── interpreter.py   # выполнение AST
├── tools/
│   └── generate_corpus.py  # генератор обучающего корпуса
├── data/
│   └── foenu-x-corpus.md   # корпус знаний ~40 МБ (для нейросети)
└── examples/
    ├── hello.foenu-x    # Hello World
    ├── vars.foenu-x     # переменные, условия, циклы
    ├── functions.foenu-x# функции
    ├── cmd.foenu-x      # запуск команд ОС
    └── test_all.foenu-x # тест всех возможностей
```

## Обучающий корпус (для нейросети)

`data/foenu-x-corpus.md` — сгенерированный корпус ~40 МБ: статьи, справочники,
45 тыс. вопросов-ответов, типичные ошибки и 18 тыс. примеров кода.
Каждый пример реально выполнен интерпретатором, поэтому вывод корректен.

```powershell
python tools\generate_corpus.py      # перегенерировать 40 МБ
python tools\generate_corpus.py 0.5  # тестовый прогон
```

Документация на HTML: `HTML Страницы/foenu-x/index.html`.
