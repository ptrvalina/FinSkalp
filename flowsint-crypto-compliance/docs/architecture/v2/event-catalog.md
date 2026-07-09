# Каталог событий v2

Схема: `platform/v2/events.py` · шина: `platform/v2/event_bus.py`

## Acquisition (L1)

| Event | Payload keys |
|-------|----------------|
| `WalletDetected` | address, chain, source |
| `TransactionImported` | tx_hash, chain, amount |
| `DocumentUploaded` | document_id, mime, case_id |
| `OCRCompleted` | document_id, text_preview |
| `OsintMentionFound` | mention_type, value, collector_id |
| `RegistryRecordImported` | registry_id, chain, address |
| `SanctionHitDetected` | list_name, matched_value |

## Fusion (L2)

| Event | Payload keys |
|-------|----------------|
| `RawDataValidated` | acquisition_event_id |
| `DataNormalized` | entity_type, canonical_key |
| `DuplicateSuppressed` | duplicate_of, fingerprint |
| `EntityEnriched` | entity_id, enrichments |
| `AttributionApplied` | entity_id, label, confidence |
| `ConfidenceCalculated` | composite_pct, explain[] |
| `FusedIntelligenceReady` | entity_ids[], case_id |

## Knowledge (L3)

| Event | Payload keys |
|-------|----------------|
| `EntityCreated` | entity_id, entity_type |
| `EntityMerged` | survivor_id, merged_ids[] |
| `RelationEstablished` | relation_id, type |
| `GraphExpanded` | root_entity_id, hop |
| `EntityVersionCommitted` | entity_id, version |

## Analytics (L4)

| Event | Payload keys |
|-------|----------------|
| `RiskUpdated` | entity_id, score, explain |
| `PatternDetected` | pattern_id, entities[] |
| `TimelineUpdated` | entity_id, events_count |
| `AICompleted` | task_id, summary, citations[] |

## Investigation (L5)

| Event | Payload keys |
|-------|----------------|
| `CaseOpened` | case_id, case_ref |
| `EvidenceCreated` | evidence_id, case_id, hash |
| `CaseTransition` | case_id, from_status, to_status |
| `ReviewSubmitted` | entity_id, verdict |
| `ReportGenerated` | case_id, format |

## Legacy bridge

События v1 (`case_new`, `fusion_completed`, …) продолжают публиковаться через `ComplianceEventBus`.  
`PlatformEventBus.publish()` дублирует в v2 stream `finskalp:events:v2` + legacy stream для совместимости UI.
