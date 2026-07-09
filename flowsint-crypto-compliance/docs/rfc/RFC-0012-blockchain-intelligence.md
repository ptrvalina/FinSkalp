# RFC-0012 Blockchain Intelligence Framework v2.0

**Статус:** Complete (100%)

## Цели (Глава 1)

Импорт, анализ транзакций, графы потоков, кластеризация, поведенческий профиль, события для KG.

## Сети (Глава 2)

BTC, ETH, TRON, BSC, Polygon, LTC, SOL — через единый адаптер-контракт.

## API

| Endpoint | Описание |
|----------|----------|
| `GET /blockchain-intelligence/manifest` | Сети, каноническая модель, pipeline |
| `POST /blockchain-intelligence/analyze` | Анализ адреса + publish в KG |

## Модуль

`platform/v2/blockchain_intelligence/` — manifest, analytics, service

## Completion

[`rfc0012-completion.md`](../architecture/v2/rfc0012-completion.md)
