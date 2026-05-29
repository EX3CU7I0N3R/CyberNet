# DECISIONS.md

## Decision Record Format

Every architectural decision must follow:

* Decision ID
* Date
* Status
* Context
* Decision
* Alternatives Considered
* Consequences

Status values:

* Active
* Superseded
* Experimental
* Rejected

---

# ADR-001

Date: 2026-05-29

Status: Active

Title: Graph-First Behavioral Architecture

## Context

Traditional network tools focus on packets, alerts, or signatures.

The project goal is to understand behavioral state and network evolution.

## Decision

Adopt a graph-first architecture where:

Packets
→ Events
→ Flows
→ Hosts
→ Relationships
→ Graph State

Graph state becomes the primary analytical abstraction.

## Alternatives Considered

* Flow-centric architecture
* Alert-centric architecture
* Signature-first IDS model

## Consequences

Positive:

* Enables replay
* Enables diffing
* Enables topology analysis

Negative:

* Additional abstraction layers
* Increased metadata requirements

---

# ADR-002

Date: 2026-05-29

Status: Active

Title: Directional Flow Modeling

## Context

Bidirectional flows hide initiator behavior.

Behavioral analytics require initiator/responder semantics.

## Decision

Flows are directional.

Example:

Host A → Host B

and

Host B → Host A

are distinct flow entities.

## Alternatives Considered

* Traditional bidirectional sessions

## Consequences

Positive:

* Better attribution
* Better beacon analysis
* Better replay accuracy

Negative:

* Increased flow count

---

# ADR-003

Date: 2026-05-29

Status: Active

Title: Deterministic Replay Requirement

## Context

Future replay and diff engines require stable event ordering.

## Decision

Every packet receives:

* replay_sequence_id
* timeline_index

These identifiers must remain stable through all layers.

## Alternatives Considered

* Timestamp-only replay

## Consequences

Positive:

* Deterministic replay
* Snapshot consistency

Negative:

* Additional storage overhead

---

# ADR-004

Date: 2026-05-29

Status: Active

Title: Explainable Scoring

## Context

Risk scores without explanation reduce analyst trust.

## Decision

All scores must expose contributing factors.

Examples:

* Host risk
* Relationship risk
* Graph risk

## Alternatives Considered

* Black-box scoring

## Consequences

Positive:

* Transparency
* Analyst trust

Negative:

* Additional metadata

---

# ADR-005

Date: 2026-05-29

Status: Active

Title: Backend-First Development

## Context

Visualization is not the source of truth.

The graph engine must remain independent.

## Decision

Frontend development begins only after:

* Graph State
* Snapshot Engine
* Diff Engine

are stable.

## Alternatives Considered

* UI-first architecture

## Consequences

Positive:

* Stable backend
* Reusable exports

Negative:

* Delayed visual feedback

---

# ADR-006

Date: 2026-05-29

Status: Active

Title: No Machine Learning Dependency

## Context

The project prioritizes explainability.

## Decision

Use deterministic behavioral analytics.

Machine learning remains optional and deferred.

## Alternatives Considered

* Early anomaly detection models

## Consequences

Positive:

* Explainability
* Reproducibility

Negative:

* Reduced anomaly discovery capability

---

# ADR-007

Date: 2026-05-29

Status: Active

Title: Validation Before Layer 5

## Context

Graph State Engine exists but has unresolved validation concerns.

Examples:

* Community detection quality
* Centrality pollution
* Snapshot quality

## Decision

Introduce Phase 4.6 Validation before beginning Layer 5.

## Consequences

Positive:

* Higher confidence
* Reduced technical debt

Negative:

* Delays new feature development
