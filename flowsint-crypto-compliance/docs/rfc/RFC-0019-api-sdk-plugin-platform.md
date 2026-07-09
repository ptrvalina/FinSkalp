# RFC-0019: API, SDK & Plugin Platform v2.0

**RFC-0019 · ASPP · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0002](RFC-0002-enterprise-architecture.md), [RFC-0007](RFC-0007-integration-connectors.md), [RFC-0009](RFC-0009-rbac-harmonization.md) |
| Реализация | `platform/v2/aspp/` |
| Completion | [`rfc0019-completion.md`](../architecture/v2/rfc0019-completion.md) |

---

## Предисловие

ASPP — единая платформа API, SDK и плагинов FinSkalp v2.0.

**API First, Plugin First — расширения через манифест, без форков ядра.**

---

## Глава 1. API First

Все подсистемы экспонируют REST-контракт через `/api/platform/v2/*`. Каталог маршрутов: `GET /aspp/rest-catalog`.

## Глава 2. Plugin First

Плагины регистрируются через `PluginManifest` с permissions, dependencies, health, events, config.

## Глава 3. Gateway

Аутентификация, rate limiting, routing, audit — `gateway_manifest.py`.

## Глава 4. REST

`rest_catalog.py` — OpenAPI-style каталог всех маршрутов v2.

## Глава 5. GraphQL (stub)

Read-only запросы для дашборда расследования — `graphql_schema.py`.

## Глава 6. gRPC (stub)

Внутренние сервисы — `grpc_manifest.py`.

## Глава 7. Event Bus

Каталог событий с версией и schema ref — `event_catalog.py`.

## Глава 8–9. Plugin Platform

10 категорий `PluginCategory`, `plugin_manager.py` расширяет `plugin_registry`.

## Глава 10. SDK

Python, TypeScript, Go, Java — manifests в `sdk_*.py`.

## Глава 11. Security

OAuth2/JWT/RBAC/ABAC/mTLS — `security_manifest.py`.

## Глава 12. Versioning

Semver `2.0.0` — `versioning.py`.

## Глава 13. Webhooks

Подписка и доставка (stub + retry) — `webhooks.py`.

## Глава 14. Marketplace

Каталог расширений: connectors, rules, reports, viz, AI, templates.

## Глава 15. Developer Portal

Документация, sandbox, changelog — `developer_portal.py`.

## Глава 16. Monitoring

Метрики API и плагинов — `monitoring.py`.

## Глава 18. Constraints

Запрещённые действия плагинов — `constraints.py`.

---

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/aspp/manifest` | Манифест ASPP |
| GET | `/aspp/rest-catalog` | REST каталог |
| GET | `/aspp/events` | Каталог событий |
| GET | `/aspp/marketplace` | Маркетплейс |
| GET | `/aspp/developer-portal` | Портал разработчика |
| POST | `/aspp/webhooks/subscribe` | Подписка webhook |
| GET | `/aspp/webhooks` | Список подписок |
| GET | `/aspp/monitoring` | Метрики |
| POST | `/aspp/plugins/register` | Регистрация плагина |

---

## Celery

`aspp_deliver_webhooks` — beat 300s, доставка pending webhooks.
