# FinSkalp — Enterprise Report Upgrade Plan

**Тип:** План повышения отчётов до enterprise (аудит + конкретные изменения UI/шаблонов; без изменений кода в рамках этого документа)
**Дата:** 2026-07-09
**Принцип:** текущие отчёты — основа продукта. **Не удалять** Screening / SAR / Forensic / Seizure. Не менять структуру расследования и API генерации отчётов. Все улучшения — **обратносовместимые** (аддитивные ключи, опц. параметры, template-gated блоки).

---

## 1. Точка отсчёта

| Отчёт | `report_type` (URL `?type=`) | Builder | Шаблон |
|---|---|---|---|
| Screening | `address` | `FinSkalpReportBuilder.build_address_report` | `finskalp_address.html.j2` |
| SAR | `sar` | `SarReportBuilder.build` | `finskalp_sar.html.j2` |
| Forensic | `forensic` | `build_forensic_report_v2` + `enrich_forensic_report` | `finskalp_forensic.html.j2` |
| Seizure | `seizure` | `SeizureReportBuilder.build` | `finskalp_seizure.html.j2` |

Оркестратор: `FinSkalpInvestigator.investigate()`. Рендер: Jinja2 → HTML → WeasyPrint (fallback HTML). **Forensic v2 — эталон** (17+ секций, включая Executive Summary, Risk Breakdown, Timeline, Evidence Inventory, Digital Signature).

**Ключевой безопасный паттерн (уже используется):** `enrich_forensic_report()` дописывает ключи в dict **без изменения сигнатур** билдеров; шаблоны используют `{% if report.X %}` — отсутствующие ключи не ломают рендер.

---

## 2. Матрица «10 enterprise-секций × 4 отчёта»

Легенда: ✅ есть · ◑ частично · ➕ добавить (presentation) · 🔌 нужно новое подключение данных.

| Секция | Screening | SAR | Forensic | Seizure | Источник данных |
|---|---|---|---|---|---|
| Executive Summary | ◑ | ✅ | ✅ | ➕ | screening summary, fusion scores, enrich narrative |
| Risk Breakdown | ◑ | ◑ | ✅ | ➕ | `risk_score_breakdown`; 🔌 RDE factors |
| Confidence Matrix | ◑ | ➕ | ◑ | ➕ | attribution tiers; 🔌 RDE `calculate_confidence()` |
| Graph Legend | ➕ | ➕ | ➕ | ➕ | `svg_graph_style` цветовая семантика |
| Evidence Quality | ◑ | ◑ | ✅ | ◑ | `evidence_inventory`; 🔌 ECCF quality/timeline |
| Timeline Improvements | ◑ | ◑ | ◑ | ➕ | on-chain ts; 🔌 ECCF `get_evidence_timeline` + `phases` |
| Explainability | ➕ | ➕ | ◑ | ➕ | 🔌 RDE `build_explanation` / EIA outline |
| Investigation Statistics | ◑ | ◑ | ◑ | ➕ | `phases`, `volume_stats`, `metrics` |
| Recommendations | ✅ | ✅ | ✅ | ✅ | эвристики билдеров; можно обогатить RDE prioritization |
| Report Metadata | ◑ | ◑ | ✅ | ◑ | cover, `digital_signature`, `database_versions` |

**Вывод:** Forensic v2 уже почти enterprise. Остальные 3 отчёта подтягиваются в основном **презентационно** (перенос уже вычисленных helper'ов) + 4 секции требуют подключения платформенных данных (RDE/ECCF/EIA).

---

## 3. Стратегия (обратносовместимая)

### 3.1 Общий модуль enterprise-секций
Создать `reporting/enterprise_sections.py` (**новый файл**, ничего не ломает) — набор чистых функций, принимающих уже существующие входные dict'ы (`screening`, `fusion_report`, опц. `rde_result`, `eccf_timeline`) и возвращающих секции:
- `build_executive_summary(...)`, `build_risk_breakdown(...)`, `build_confidence_matrix(...)`, `build_graph_legend(...)`, `build_evidence_quality(...)`, `build_timeline(...)`, `build_explainability(...)`, `build_investigation_statistics(...)`, `build_recommendations(...)`, `build_report_metadata(...)`.

Часть уже существует в `forensic_enrichment.py` (`build_risk_score_breakdown`, `compute_overall_confidence`, `build_activity_timeline`) — **вынести в общий модуль** и переиспользовать в SAR/address/seizure.

### 3.2 Единый пост-процессинг-хук
Добавить опц. шаг после каждого билдера в `FinSkalpInvestigator.investigate()`:
```
report = SarReportBuilder().build(...)
report = enrich_enterprise_sections(report, context)   # новый, опц., аддитивный
```
`enrich_enterprise_sections` дописывает ключи (`executive_summary`, `risk_breakdown`, `confidence_matrix`, `graph_legend`, `evidence_quality`, `enterprise_timeline`, `explainability`, `investigation_statistics`, `report_metadata`). Существующие ключи не трогаются. При отсутствии данных секция не добавляется.

### 3.3 Единый top-level `report_metadata`
Добавить опц. ключ `report_metadata` во все билдеры (id, версия движка, case_ref, сгенерировано, локаль, хеш конфигурации, версии БД). Общий Jinja-partial `_report_metadata.html.j2` инклюдится в 4 шаблона.

### 3.4 Подключение платформенных данных (data plumbing)
- **Confidence Matrix / Explainability:** вызвать `run_rde_assessment` (read-only) в `investigate()` и передать `rde_result` в enrichment. RDE уже имеет `calculate_confidence()` и `build_explanation()`.
- **Timeline / Evidence Quality:** подтянуть `ECCFService.get_evidence_timeline()` и quality-скор из ECCF в `evidence_inventory`.
- **Graph Legend:** экспортировать цветовую семантику из `svg_graph_style` как структурированные метаданные легенды.

Все вызовы — read-only, за флагом; при недоступности подсистемы отчёт формируется как сейчас.

---

## 4. Конкретные изменения по секциям

| Секция | Изменение в билдере | Изменение в шаблоне | Источник |
|---|---|---|---|
| Executive Summary | `report["executive_summary"] = build_executive_summary(...)` для address/seizure (в forensic/sar есть) | `{% if report.executive_summary %}` блок вверху | screening + fusion |
| Risk Breakdown | Переиспользовать `build_risk_score_breakdown` в SAR/address | таблица компонентов риска | screening findings, 🔌 RDE factors |
| Confidence Matrix | `report["confidence_matrix"] = build_confidence_matrix(rde_result, attribution)` | матрица «измерение × уверенность %» | 🔌 RDE `calculate_confidence` |
| Graph Legend | `report["graph_legend"] = build_graph_legend()` | легенда узлов/рёбер рядом с графом | `svg_graph_style` |
| Evidence Quality | Слить ECCF-quality в `evidence_inventory` | колонка «качество/tier» | 🔌 ECCF |
| Timeline | `report["enterprise_timeline"] = build_timeline(phases, eccf_timeline)` | вертикальный timeline с типами событий | `phases` + 🔌 ECCF |
| Explainability | `report["explainability"] = build_explainability(rde_result)` | блок «почему такой риск» | 🔌 RDE/EIA |
| Investigation Statistics | `report["investigation_statistics"] = build_investigation_statistics(...)` | сводка (кол-во сущностей, source_status, длительность фаз) | `phases`, `volume_stats`, `metrics` |
| Recommendations | обогатить из RDE prioritization (опц.) | уже есть, расширить | эвристики + RDE |
| Report Metadata | `report["report_metadata"] = build_report_metadata(...)` всем 4 | общий partial `_report_metadata.html.j2` | билдеры |

---

## 5. Конкретные изменения UI

**Демо-стенд (`demo/static/`):**
- Вью «Отчёты 115-ФЗ» (`#reportsRegistry`) — добавить бейджи новых секций в карточке отчёта; кнопки скачивания не меняются (`?type=` сохраняется).
- В превью отчёта показывать оглавление enterprise-секций.

**flowsint-app:**
- Вкладка `reports` в `AnalystWorkspaceShell` сейчас stub — превратить в реальный список отчётов через существующий `complianceService.reportPdfUrl(caseId)` и platform v2, **без смены роутинга**.
- Переиспользовать `enterprise-ui.tsx` (`EnterprisePanel`, `RiskBadge`, `ExplainabilityDrawer`) для инлайн-предпросмотра Risk Breakdown / Explainability из данных отчёта.

**ECCF-связка:** при отдаче PDF вызывать `record_report_usage()` (side-effect, форма dict не меняется) — для аудита использования доказательств.

---

## 6. i18n

- Расширить `report_i18n.py` за пределы FZ115: паттерн зеркала ключей `_ru` → `_en` для новых enterprise-секций (аддитивно, RU остаётся primary).

---

## 7. Гарантии обратной совместимости

- ❌ Не менять обязательные kwargs билдеров и `FinSkalpInvestigationRequest`.
- ❌ Не менять строки `report_type` в URL (`?type=forensic` и т.д.).
- ✅ Только опц. ключи в выходных dict'ах.
- ✅ Только template-gated (`{% if %}`) блоки.
- ✅ `_normalize_forensic_report()` расширять, не заменять.
- ✅ Подключения RDE/ECCF/EIA — read-only и за флагом; отчёт формируется даже при их отсутствии.

**Порядок внедрения:** (1) общий модуль + `report_metadata` во всех 4; (2) перенос risk_breakdown/timeline/confidence из forensic в SAR/address/seizure (presentation); (3) подключение RDE/ECCF (data plumbing) для Confidence Matrix, Explainability, Timeline, Evidence Quality; (4) UI-обновления и i18n.
