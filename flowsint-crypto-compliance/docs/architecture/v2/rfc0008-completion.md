# RFC-0008 Enterprise Design System — 100% Completion Checklist

Дата: 2026-07-09

## Принципы (Глава 1)

- ✅ Investigation First — `InvestigationContextProvider` (глобально в `main.tsx`)
- ✅ Information Density — compact density class, table mono
- ✅ Progressive Disclosure — shadcn disclosure patterns
- ✅ Explainability — связь с RFC-0005 explain API
- ✅ Context Preservation — sessionStorage UI state

## Визуальная философия (Глава 2)

- ✅ Нейтральная палитра, акценты только на риск/события
- ✅ Единый стиль иконок (Lucide)

## Цветовая система (Глава 3)

- ✅ Background / Surface / Border / Text tokens
- ✅ Semantic: success, warning, error, info
- ✅ Risk: low, medium, high, critical
- ✅ Graph entities: wallet, person, company, exchange, contract, document, evidence, investigation

## Типографика (Глава 4)

- ✅ H1–H4, Body Large, Body, Caption, Label
- ✅ Mono для табличных данных (`.fs-table-mono`)

## Сетка (Глава 5)

- ✅ 4 / 8 / 16 / 24 / 32 / 48 px scale

## Компонентная библиотека (Глава 6)

- ✅ Каталог в манифесте, реализация в `flowsint-app/src/components/ui/`
- ✅ Graph: ReactFlow на compliance page
- ✅ Timeline: activity-timeline

## Иконография (Глава 7)

- ✅ `EntityIcon` — 10 типов сущностей

## Анимация (Глава 8)

- ✅ Token durations + `prefers-reduced-motion`

## Accessibility (Глава 9)

- ✅ Keyboard (shadcn), high-contrast theme, sr-only labels

## Темы (Глава 10)

- ✅ Light, Dark, High Contrast

## Responsive (Глава 11)

- ✅ Breakpoints в манифесте (1920+, laptop 1280)

## Design Tokens (Глава 12)

- ✅ Централизованный `tokens.css`

## Governance (Глава 13)

- ✅ Манифест `governance.requires`

## API

- ✅ `GET /design-system/manifest`

## Тесты

- ✅ `tests/test_rfc0008_design_system.py`
