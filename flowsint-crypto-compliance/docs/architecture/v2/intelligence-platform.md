# RFC-0004 Intelligence Platform

**Статус:** Complete (foundation) · **Дата:** 2026-07-08

## Обзор

11 аналитических движков работают через `IntelligenceOrchestrator` поверх Knowledge Graph (RFC-0003).

```
Knowledge Graph → Engines → Findings → IngestPipeline → Evidence
```

## Движки

| Движок | Модуль | Зрелость |
|--------|--------|----------|
| Blockchain | `intelligence/engines.py` | BTC/ETH/TRON/SOL + planned LTC/BNB/Polygon |
| OSINT | `intelligence/engines.py` | Scalpel categories |
| Registry | `intelligence/engines.py` | sovereign_registry, OFAC |
| Behavioral | `intelligence/engines.py` | pass-through, dispersion |
| Entity Resolution | delegates `entity_resolution.py` | production |
| Correlation | KG neighbors + shared IDs | production |
| Attribution | `attribution_engine.py` | production |
| Risk | aggregate findings + explain | production |
| Timeline | `case_timeline` CQRS | production |
| Explainable AI | rules + alternatives | production |
| Recommendation | next steps for analyst | production |

## API

| Метод | Путь |
|-------|------|
| GET | `/api/platform/v2/intelligence/manifest` |
| POST | `/api/platform/v2/intelligence/analyze` |

## Интеграция

- `pipeline_chain.py` — стадия **analytics** вызывает `run_intelligence_analysis()`
- `finskalp_investigator.py` — через Appendix A pipeline chain

## Тесты

```bash
uv run pytest flowsint-crypto-compliance/tests/test_intelligence_platform.py -q
```

## Переменные

Наследуются от RFC-0003: `FINSKALP_ENTITY_STORE`, `FINSKALP_FUSION_MODE`.
