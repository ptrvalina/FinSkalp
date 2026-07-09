# Data flow map — RFC-0002 Platform v2

## End-to-end investigation flow

```mermaid
flowchart LR
    subgraph L1["L1 Acquisition"]
        S[Scalpel collectors]
        O[On-chain adapters]
        R[Registry / sanctions]
    end
    subgraph L2["L2 Fusion"]
        FP[FusionPipeline]
    end
    subgraph L3["L3 Knowledge"]
        ERE[EntityResolutionEngine]
        KG[KnowledgeGraphStore]
        EC[Evidence Center]
    end
    subgraph L4["L4 Analytics"]
        RS[Risk scoring]
    end
    subgraph L5["L5 Investigation"]
        IW[InvestigationWorkspace]
    end
    subgraph L6["L6 Presentation"]
        API[flowsint-api /api/platform/v2]
        DEMO[demo BFF :8877]
    end
    subgraph Events["Event backbone"]
        PEB[PlatformEventBus]
        PES[PlatformEventSubscriber]
        PG[(finskalp_platform_events)]
    end

    S --> FP
    O --> FP
    R --> FP
    FP --> PEB
    IW --> PEB
    EC --> KG
    ERE --> KG
    PEB --> PG
    PEB --> PES
    PES --> KG
    PES --> EC
    KG --> RS
    API --> IW
    API --> FP
    DEMO -.deprecated.-> API
```

## Write paths

| Source | Legacy store | v2 canonical | Event |
|--------|--------------|--------------|-------|
| `persist_osint_finding` | `osint_findings` | `finskalp_evidence` (dual-write) | — |
| `FinSkalpInvestigator` | investigation cache | `finskalp_entities` | `CaseOpened`, `RiskUpdated`, fusion stages |
| `ComplianceService.create_case` | `compliance_cases` | case Entity | `CaseOpened` |
| Scalpel collect | — | entities + evidence | `OsintMentionFound` |
| Analyst confirm/reject | `compliance_entity_labels` | wallet Entity attrs | `ReviewSubmitted` |
| `PlatformEventBus.publish` | Redis `finskalp:events:v2` | `finskalp_platform_events` | all |

## Read paths (CQRS)

| Endpoint | Source |
|----------|--------|
| `GET /api/platform/v2/cases/{case_ref}/timeline` | `finskalp_platform_events` |
| `GET /api/platform/v2/architecture` | plugin registry + schema manifest |
| Investigation UI graph | Neo4j `Finskalp*` labels (unified projection) |

## Package map

```
platform/v2/
  canonical.py          # Entity, Evidence
  events.py             # PlatformEvent catalog
  event_bus.py          # publish → Redis + Postgres + subscriber
  event_subscriber.py   # knowledge projection handlers
  evidence_center.py    # OsintFinding → finskalp_evidence
  entity_resolution.py  # signal → Entity merge
  knowledge_store.py    # Postgres upsert
  investigation_workspace.py  # Case bridge
  neo4j_projection.py   # unified graph labels
  fusion_pipeline.py    # L2 stages
  plugin_registry.py    # Scalpel factories
  gateway.py            # shared handlers
```
