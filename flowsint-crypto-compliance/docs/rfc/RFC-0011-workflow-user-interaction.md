# RFC-0011 Workflow & User Interaction Logic v2.0

**Статус:** Complete (100%)

## Философия OICD

Observe → Investigate → Correlate → Decide

## Жизненный цикл (13 обязательных этапов)

От создания дела до архивирования — ни один этап не пропускается.

## API

| Endpoint | Описание |
|----------|----------|
| `GET /workflow/manifest` | OICD, lifecycle, business rules, KPI |
| `GET /workflow/first-login` | Брифинг первого входа (Гл.3) |
| `GET /workflow/state?case_ref=` | Текущая фаза и прогресс lifecycle |
| `GET /workflow/recommendations?case_ref=` | Рекомендации с объяснениями (Гл.9) |
| `POST /workflow/start` | Автозапуск collectors после seed (Гл.4) |
| `GET|PUT /workflow/recovery` | Recovery workflow (Гл.16) |

## Event-driven (Гл.17)

UI-события: WalletOpened, GraphLoaded, TimelineUpdated, EvidenceLinked, RiskCalculated, RecommendationCreated, ReportUpdated

## Completion

[`rfc0011-completion.md`](../architecture/v2/rfc0011-completion.md)
