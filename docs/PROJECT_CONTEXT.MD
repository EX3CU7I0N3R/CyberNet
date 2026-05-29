# PROJECT_CONTEXT.md

## Project Overview

PCAPModels is a behavioral network telemetry and graph intelligence platform that transforms packet captures (PCAPs) into progressively higher-level analytical representations.

The platform is designed around deterministic, explainable analysis rather than machine learning driven classification.

The primary objective is to enable analysts to move from raw packets to actionable behavioral understanding while maintaining reproducibility, auditability, and transparency.

---

## Mission

Convert network traffic into:

1. Canonical packet events
2. Directional communication flows
3. Host behavioral profiles
4. Network relationship graphs
5. Temporal behavioral evolution
6. Investigation-ready intelligence

---

## Core Principles

### Analyst First

The platform assists investigation.

The platform does not make final security decisions.

### Deterministic Processing

Identical input data must produce identical output.

### Explainability

Every score, indicator, and conclusion must be traceable to observable evidence.

### Layered Architecture

Each layer adds abstraction without destroying lower-layer evidence.

### Backend First

Visualization is a consumer of platform outputs, not part of core analysis.

---

## Current Status

Current Stable Layer: Layer 4

Completed:

* Layer 1 Packet Ingestion
* Layer 2 Flow Intelligence
* Layer 3 Host Intelligence
* Layer 4 Graph State

Planned:

* Layer 5 Temporal Diff Engine
* Layer 6 Investigation Engine
* Layer 7 Visualization Support
* Layer 8 Scale & Operations

---

## Success Criteria

* Deterministic outputs
* Explainable risk indicators
* Temporal network visibility
* Efficient processing of enterprise PCAPs
* Frontend-agnostic exports

---

## Known Constraints

* Batch PCAP processing only
* No decryption of encrypted traffic
* No machine learning dependencies
* No database dependency
* No frontend dependency

---

## Repository Governance

This document is the authoritative source describing project purpose and scope.

Architectural details belong in ARCHITECTURE.md.

Implementation history belongs in AI_LOG.md.
