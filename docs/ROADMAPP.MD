# ROADMAP.md

## Current State

Phase 4 Validation

Status: Active

Reason:
Layer 4 functionality exists but requires formal validation before Layer 5 begins.

---

## Phase 4.6 Validation

Objectives:

* Unit testing
* Integration testing
* Replay verification
* Hash stability verification
* Snapshot correctness verification
* Benchmark creation

Exit Criteria:

* ≥80% critical-path test coverage
* Deterministic replay verified
* Stable graph generation verified
* Performance baseline documented

---

## Phase 5 Temporal Diff Engine

Objectives:

* Snapshot comparison
* Node emergence detection
* Edge emergence detection
* Risk escalation tracking
* Change magnitude scoring

Deliverables:

* SnapshotDiff model
* Diff engine
* Export format
* Validation suite

---

## Phase 6 Investigation Engine

Objectives:

* Timeline reconstruction
* Evidence correlation
* Investigation context generation

---

## Phase 7 Visualization Support

Objectives:

* Replay payload generation
* Graph animation support
* Frontend integration guidance

---

## Phase 8 Scale & Operations

Objectives:

* Streaming ingestion
* Large PCAP support
* Memory optimization
* Operational deployment support

---

## Deferred Items

* Machine learning
* Threat intelligence enrichment
* Graph databases
* SOAR integrations

These remain optional until Layers 1-8 are stable.
