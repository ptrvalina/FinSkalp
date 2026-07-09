# LIVE INTEGRATION STATUS

Этот файл описывает формат live-таблицы статуса интеграции Platform v2.

Источник истины: `flowsint_crypto_compliance.platform.v2.integration.status`.
Markdown-таблица формируется функцией `render_status_markdown_table()` поверх `get_integration_status()`.

## Колонки

- `Компонент` — модуль или интеграционный слой Platform v2.
- `Статус` — `working`, `partial` или `stub`.
- `Реальные данные` — `yes`, `partial` или `no`.
- `Что подключить` — переменные окружения и/или внешние сервисы, нужные для live-режима.

## Как сгенерировать

```bash
cd flowsint-crypto-compliance
python -c "from flowsint_crypto_compliance.platform.v2.integration.status import render_status_markdown_table; print(render_status_markdown_table())"
```

## Текущий шаблон

| Компонент | Статус | Реальные данные | Что подключить |
| --- | --- | --- | --- |
| blockchain | working/partial | yes/partial/no | TRONGRID_API_KEY, public blockchain RPC/explorer APIs, DATABASE_URL |
| ICF | working | partial/no | real connector APIs / data providers |
| CRIF | partial | partial | official registries, sanctions feeds, registry APIs |
| RDE | working | partial/no | blockchain intelligence, CRIF registries, DATABASE_URL |
| ECCF | working | partial | persistent evidence storage backend |
| EIA | working/partial | yes/partial | OPENAI_API_KEY |
| ASPP | working | no | external plugin/webhook consumers |
| ESA | working | no | IdP / SIEM / secret manager |
| IDOO | working | partial | Postgres, Redis, Neo4j, Celery workers |
| EGPR | working | no | RFC/ADR external workflows if needed |
| KG | working/partial | yes/partial | DATABASE_URL |
| event bus | working | yes | REDIS_URL |
| celery | working/partial | yes/no | CELERY_BROKER_URL or REDIS_URL, running Celery worker |
