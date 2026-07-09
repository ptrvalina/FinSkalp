# RFC-0007 Integration & Connectors — 100% Completion Checklist

Дата: 2026-07-09

## Принципы (Глава 1)

- ✅ Connector First — единый контракт `Connector`
- ✅ Запрет прямой мутации KG / risk / ER

## Категории (Глава 2)

- ✅ Blockchain (7 production + XMR planned)
- ✅ Blockchain Intelligence Providers (7 licensed)
- ✅ Public Explorers (6)
- ✅ Registry (4)
- ✅ OSINT (10)
- ✅ Document (6)

## Контракт (Глава 3)

- ✅ connect / authenticate / health / collect / normalize / validate / publish / shutdown

## Жизненный цикл (Глава 4)

- ✅ `run_pipeline` — mandatory normalize + validate before publish

## Нормализация (Глава 5)

- ✅ Canonical fields: entity_type, entity_value, source_type, confidence

## Качество источников (Глава 6)

- ✅ `SourceQualityProfile` на каждый коннектор

## Управление (Глава 7)

- ✅ Descriptor: version, author, license, status, apis, error_log

## SDK (Глава 8)

- ✅ `BaseConnector` + `sdk_manifest()`

## Безопасность (Глава 9)

- ✅ `integration_security_manifest()`

## API

- ✅ `GET /connectors/manifest`
- ✅ `POST /connectors/{id}/health`
- ✅ `POST /connectors/{id}/collect`

## Тесты

- ✅ `tests/test_rfc0007_connectors.py`
