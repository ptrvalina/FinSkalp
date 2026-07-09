# RFC-0006: Intelligence Engine

**RFC-0006 · Intelligence Engine**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0004](RFC-0004-intelligence-platform.md), [RFC-0005](RFC-0005-investigation-platform.md) |
| Реализация | `platform/v2/intelligence_engine/` |
| Completion | [`rfc0006-completion.md`](../architecture/v2/rfc0006-completion.md) |

---

## Предисловие

Архитектура платформы определяет способ хранения информации. Интеллектуальная ценность определяется способностью автоматически превращать данные в знания.

После реализации RFC-0006 FinSkalp становится системой анализа знаний — фактов, гипотез и взаимосвязей.

---

## Глава 1. Философия Intelligence

Пять вопросов: что произошло? почему? кто участвовал? что связано? что проверить?

---

## Глава 2. Intelligence Pipeline

14 стадий: Source → Collector → … → Report. Реализация: `intelligence_engine/pipeline.py`, `orchestrator.py`.

---

## Глава 3. Fusion Intelligence

12 измерений на каждый факт: источник, тип, достоверность, связи, конфликты, дубликаты, приоритет, контекст, влияние, entity, evidence, graph.

---

## Главы 4–10

| Глава | Модуль |
|-------|--------|
| Pattern Engine | `patterns.py` |
| Behavior Engine | `behavior.py` |
| Hypothesis Engine | `hypotheses.py` |
| Recommendation | orchestrator + RFC-0004 |
| Explainable | `explain` в result |
| Intelligence Score | `scores.py` — 8 метрик |
| Intelligence Memory | `memory.py` |

---

## API

- `GET /api/platform/v2/intelligence-engine/manifest`
- `POST /api/platform/v2/intelligence-engine/run`

---

## Эпилог

FinSkalp помогает структурировать знания, выявлять закономерности и строить объяснимые гипотезы.
