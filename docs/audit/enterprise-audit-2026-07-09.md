# FinSkalp — Enterprise Audit (2026-07-09) · Индекс

Полный аудит текущей реализации FinSkalp (только чтение, без изменений кода). Архитектура принята как базовый актив; предлагаются исключительно эволюционные, обратносовместимые улучшения. Не затрагиваются: домены, API, RFC, имена сервисов, UI, отчёты, существующие пайплайны.

## Документы

1. **[Enterprise Gap Report](enterprise-gap-report.md)** — карта компонентов (works/stub/absent), сравнение с Enterprise Investigation Platform, реестр из 25 разрывов (описание/влияние/риск/сложность/приоритет).
2. **[Architecture Hardening Plan](architecture-hardening-plan.md)** — по каждому из 9 компонентов (Blockchain Intelligence, ICF, CRIF, RDE, ECCF, EIA, ASPP, ESA, IDOO): техдолг, узкие места, масштабирование, отказоустойчивость, безопасность + эволюционные шаги.
3. **[Enterprise Report Upgrade Plan](enterprise-report-upgrade-plan.md)** — повышение 4 отчётов (Screening/SAR/Forensic/Seizure) до enterprise: 10 новых секций, обратносовместимо + конкретные изменения UI/шаблонов.
4. **[Workspace Enhancement Roadmap](workspace-enhancement-roadmap.md)** — 8 новых компонентов рабочего места (Case Dashboard, Timeline, Evidence Drawer, Risk Panel, AI Context Panel, Graph Insights, Alert Center, Task Board) поверх текущего стека и API.
5. **[Enterprise Readiness Roadmap](enterprise-readiness-roadmap.md)** — 12 направлений (Security, Audit, RBAC, Evidence, API, Monitoring, Logging, CI/CD, Backup, DR, Scalability, Observability) и план 30/60/90/180 дней.

## Ключевой вывод

FinSkalp — зрелый **production-candidate** с когерентной RFC-архитектурой (0000–0022) и реальным ядром расследования. Основной разрыв между «100% в completion-доках» и enterprise-продом: **персистентность evidence/audit + WORM**, **закрытие демо-плоскости auth/RBAC**, **реальные данные реестров/sanctions**, **единая сущность Case/Evidence**, **prod-инфра (backup/DR/observability)**. Все разрывы закрываются эволюционно.

## Связанные материалы
- Существующий реестр техдолга: [`technical-debt.md`](technical-debt.md)
- RFC-книга: [`../rfc/README.md`](../rfc/README.md)
- Completion-доки: [`../architecture/v2/`](../architecture/v2/)

> Только аудит и roadmap. Изменения кода не выполнялись.
