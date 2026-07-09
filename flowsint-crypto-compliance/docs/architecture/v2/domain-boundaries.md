# Границы доменов — as-is → to-be

## Acquisition

| As-is | To-be | Действие |
|-------|-------|----------|
| `scalpel/engine.py` | Scalpel plugin family | Publish `OsintMentionFound` only |
| `live_collectors.py` | Live collector plugins | No direct fusion calls |
| `chains/*.py` | Blockchain connector plugins | `WalletDetected`, `TransactionImported` |

## Fusion

| As-is | To-be | Действие |
|-------|-------|----------|
| `finskalp_investigator.py` orchestration | `FusionPipeline` stages | Route via events |
| `fusion_confidence.py` | Fusion stage `confidence` | Keep algorithm |
| `multihop_fusion.py` | Acquisition + Fusion subgraph | Emit `GraphExpanded` |

## Knowledge

| As-is | To-be | Действие |
|-------|-------|----------|
| `db_models.OsintFinding` | `finskalp_evidence` | Dual-write M1 |
| `wallet_neo4j.py` | KG projection | Single label map |
| `evidence_graph.py` | In-memory → event-sourced | Deprecate direct graph |

## Analytics

| As-is | To-be | Действие |
|-------|-------|----------|
| `attribution_engine.py` | Analytics service | Read entities, emit `RiskUpdated` |
| `illegal_flow.py` | Pattern plugin | `PatternDetected` |
| `xgboost_risk.py` | Risk plugin | No HTTP in scoring |

## Investigation

| As-is | To-be | Действие |
|-------|-------|----------|
| `ComplianceCase` | Case entity + workflow | Unify with Investigation |
| `operations_center.py` | Investigation projection | Remove in-memory M3 |
| `compliance_rbac.py` | Platform domain | Gateway enforcement |

## Presentation

| As-is | To-be | Действие |
|-------|-------|----------|
| `web_server.py` monolith | Thin BFF or remove | M3 |
| `flowsint-api` | **Single gateway** | Canonical |
| `flowsint-app` | UI only | No business rules |

## Запрещённые связи (enforce in review)

```text
Presentation ──X──> Acquisition HTTP
Analytics ──X──> TronGrid
Fusion ──X──> PDF generator
OSINT collector ──X──> ComplianceCase ORM
```
