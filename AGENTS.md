# AGENTS.md

Указатели для агентов. Только навигация: статус, ветки и задачи сюда не пишутся.

- Словарь домена: `CONTEXT.md`. Термины — только оттуда.
- Решения и почему так: `docs/adr/` (формат — `docs/adr/README.md`).
- Правила кода для ревью: `CODING_STANDARDS.md`.
- Тикеты и сценарии ведёт Antagor: `.agents/antagor/`.
- Стандарт CLI: https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator/src/branch/main/skills/cli-builder/reference/standard.md
- Гейт перед коммитом: `uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@v1.25.0#subdirectory=gate" rb-release check`.
- Добавил, переименовал или удалил публичное имя модуля — обнови docstring файла: Antagor сверяет его с содержимым и отклоняет задачу.
