## 1. Executive Summary

Layer 5 is the first analyst-facing behavioral intelligence layer of the platform. It transforms Layer 1-4 outputs into actionable reasoning by detecting behavioral deltas, correlating them into attack hypotheses, building evidence-driven narratives, and ranking investigation candidates.

This design defines a modular, scalable Layer 5 architecture that answers:
- What changed?
- Why did it change?
- Does it matter?
- What attack hypotheses explain it?
- What should an analyst investigate next?

---

## 2. Layer 5 Mission

Layer 5 mission:

- Deliver behavioral delta analysis from graph-aware temporal snapshots
- Generate evidence-driven attack hypotheses instead of binary detections
- Prioritize findings based on risk, criticality, and graph impact
- Provide analyst-ready outputs that explain why a behavior is suspicious
- Create a stable foundation for future investigation, replay, visualization, detection expansion, and reporting layers

---

## 3. Complete Module Architecture

### Core Modules

1. `Delta Ingestion & Normalization`
   - Responsibility: consume Layer 1-4 outputs, normalize entity identifiers, align snapshots, and build change-ready state
   - Inputs: `Host Profiles`, `Relationships`, `Graph State`, `Temporal Snapshots`, `Behavioral Metrics`
   - Outputs: normalized delta-ready data, snapshot alignment references, provenance metadata
   - Dependencies: graph snapshot store, profile store, metric service

2. `Behavioral Baseline Manager`
   - Responsibility: maintain immediate and historical baselines for hosts, relationships, protocols, fanout, and persistence
   - Inputs: aligned snapshots, historical graph state, host/relationship metadata
   - Outputs: immediate baseline state, 30-day learned behavior models, deviation thresholds
   - Dependencies: snapshot history store, baseline model store, asset inventory

3. `Behavioral Delta Engine`
   - Responsibility: detect change events for hosts, relationships, communities, and topology against both snapshot and baseline references
   - Inputs: normalized snapshot deltas, immediate baseline, historical baseline, graph metrics
   - Outputs: `BehavioralDelta` records
   - Dependencies: delta normalization, baseline manager, graph metrics, community detection

4. `Attack Correlation Engine`
   - Responsibility: convert deltas and state into attack hypotheses
   - Inputs: `BehavioralDelta`, `Host Profiles`, `Relationships`, `Graph State`, `Temporal Snapshots`, `Hypothesis Registry`
   - Outputs: `AttackHypothesis`, candidate evidence bundles
   - Dependencies: delta engine, hypothesis registry, evidence chain manager, threat model definitions

5. `Narrative Builder`
   - Responsibility: link related hypotheses into coherent attack narratives and campaign sequences
   - Inputs: multiple `AttackHypothesis`, `EvidenceChain`, graph context, campaign templates
   - Outputs: `AttackNarrative`
   - Dependencies: attack correlation engine, evidence chain manager, narrative templates

6. `Evidence Chain Manager`
   - Responsibility: build and score evidence chains that explain hypotheses, including supporting and contradictory evidence
   - Inputs: hypothesis candidates, supporting telemetry, contradictory signals, provenance, external context
   - Outputs: `EvidenceChain` objects, explanation metadata
   - Dependencies: correlation engine, data model registry

7. `Investigation Prioritization Engine`
   - Responsibility: rank findings into prioritized investigation candidates
   - Inputs: hypotheses, evidence chains, narratives, graph impact metrics, asset criticality data
   - Outputs: `InvestigationCandidate`, `AttackNarrative`
   - Dependencies: narrative builder, evidence chain manager, asset criticality registry, priority scoring config

8. `Output & Interface Layer`
   - Responsibility: expose results to analysts and future layers
   - Inputs: all Layer 5 artifacts
   - Outputs: structured API payloads, export packages, dashboard payloads, event stream messages
   - Dependencies: storage backplane, API layer, messaging bus

### Data Flow

1. `Layer 1-4` produces:
   - canonical events
   - directional flows
   - behavioral metrics
   - host profiles
   - relationships
   - graph state
   - temporal snapshots

2. `Behavioral Baseline Manager` ingests snapshot history and learned behavior, producing immediate and historical baselines

3. `Delta Ingestion & Normalization` aligns current and prior snapshots with baseline references

4. `Behavioral Delta Engine` identifies changes against both direct snapshot deltas and baseline deviations:
   - hosts
   - relationships
   - communities
   - topology

5. `Attack Correlation Engine` maps deltas to hypotheses

6. `Narrative Builder` links related hypotheses into coherent attack narratives

7. `Evidence Chain Manager` assembles supporting and contradictory evidence for each hypothesis

8. `Investigation Prioritization Engine` scores and ranks findings

9. `Output & Interface Layer` exposes:
   - prioritized findings
   - evidence chains
   - narratives
   - APIs for future layers

### Internal Dependencies

- `Behavioral Delta Engine` depends on `Behavioral Baseline Manager`
- `Attack Correlation Engine` depends on `Behavioral Delta Engine` and `Hypothesis Registry`
- `Narrative Builder` depends on `Attack Correlation Engine` and `Evidence Chain Manager`
- `Evidence Chain Manager` depends on `Attack Correlation Engine`
- `Investigation Prioritization Engine` depends on `Narrative Builder`, `Evidence Chain Manager`, and `Graph State` metrics
- `Output Layer` depends on all upstream modules

### Scalability and Modularity

- Use snapshot partitioning by time window or segment
- Separate detection logic from scoring logic
- Keep hypothesis definitions decoupled from evidence scoring
- Support “plugin-style” addition of new hypotheses via content-driven rules

---

## 4. Behavioral Delta Design

### Baseline Comparison Strategy

- The Behavioral Delta Engine compares current snapshot deltas to both an immediate snapshot baseline and a historical learned baseline.
- The immediate baseline is derived from `Snapshot N-1` and `Snapshot N`, capturing normal short-term dynamics and reducing churn from expected changes.
- The historical baseline is a learned behavior model, typically spanning 30 days, that captures normal host, relationship, protocol, fanout, and persistence patterns.
- All host, relationship, community, and topology changes are evaluated against both direct snapshot deltas and baseline deviations.
- This prevents routine operational changes, like Windows update traffic, from being misclassified as security-relevant external expansion, protocol emergence, or risk increase.

### Host Change Detection

1. New host
   - Detection strategy: host appears in current snapshot but not prior snapshot or baseline
   - Required telemetry: host identifiers, first seen timestamp, initial flow count, source asset tagging
   - Thresholds: active for ≥2 intervals OR ≥3 flows to distinct peers within snapshot window
   - Confidence factors: repeated activity, role consistency, host belonging to monitored namespace
   - False positives: DHCP churn, planned provisioning, cloud burst instances

2. Removed host
   - Detection strategy: host present prior, absent current, and no activity for a configured quiet window
   - Required telemetry: last-seen timestamp, offline marker, expected asset lifecycle
   - Thresholds: silent for ≥2 snapshot windows or no inbound/outbound activity for 30+ minutes
   - Confidence factors: no recent planned maintenance, known asset decommission list
   - False positives: legitimate shutdowns, network segmentation changes

3. Risk increase
   - Detection strategy: host risk score rises by delta threshold between snapshots
   - Required telemetry: risk score components, recent anomaly counts, relationship severity
   - Thresholds: score increase ≥15 percentage points or ≥30% relative increase
   - Confidence factors: multiple supporting signals, sustained trend
   - False positives: one-off noisy flow burst, transient scan

4. Risk decrease
   - Detection strategy: host risk score decreases by threshold
   - Required telemetry: risk score time series, resolved relationships, cleanup activity
   - Thresholds: score drop ≥15 percentage points or ≥30% relative decrease
   - Confidence factors: reduction in high-risk relationships, confirmed benign behavior
   - False positives: masking due to missing telemetry

5. Role change
   - Detection strategy: host’s service profile shifts significantly
   - Required telemetry: protocol/service distribution, port histogram, host label/role baseline
   - Thresholds: ≥25% of traffic moves to a new protocol family or new service cluster
   - Confidence factors: new persistent relationships, sustained protocol use
   - False positives: app migration, service patching, role transition windows

6. Protocol change
   - Detection strategy: new protocol enters host profile or prior dominant protocol drops
   - Required telemetry: protocol usage, port/protocol mapping, flow-level protocol signatures
   - Thresholds: new protocol share ≥20% of host traffic or drop of prior protocol ≥40%
   - Confidence factors: persistent use over multiple snapshots, cross-host corroboration
   - False positives: protocol fallback, transient scanning

7. Persistence change
   - Detection strategy: host’s persistence score changes through relationship duration and interval consistency
   - Required telemetry: relationship lifetime, interval stability, session counts
   - Thresholds: persistence score delta ≥20%
   - Confidence factors: consistent external endpoint contact or long-lived internal session
   - False positives: long-lived backup sessions, streaming services

### Relationship Change Detection

1. New relationship
   - Strategy: relationship absent before, present now
   - Telemetry: endpoints, protocol, bytes, duration, session count
   - Thresholds: relationship observed across ≥2 packets and active for ≥1 minute
   - Confidence: persistence across snapshot boundary, not ephemeral
   - False positives: transient port scans, broadcast retries

2. Removed relationship
   - Strategy: relationship disappears after prior persistence
   - Telemetry: last active timestamp, relationship lifespan
   - Thresholds: no reappearance for next snapshot interval
   - Confidence: previously stable relationship
   - False positives: temporary outage, retry behavior

3. Persistence increase
   - Strategy: relationship persistence score rises
   - Telemetry: interval count, duration change, flow count
   - Thresholds: persistence score delta ≥30%
   - Confidence: correlated with host risk or external contact
   - False positives: new legitimate long-lived service

4. External relationship emergence
   - Strategy: an external endpoint enters the internal graph and persists
   - Telemetry: peer classification, geo/ASN context, external vs internal label
   - Thresholds: new external endpoint with ≥2 sustained sessions or ≥5 flows
   - Confidence: unusual endpoint, new port/protocol mix
   - False positives: cloud service dependency, external SaaS

5. Protocol evolution
   - Strategy: protocol set for relationship changes meaningfully
   - Telemetry: protocol transition, port/protocol mapping
   - Thresholds: newly introduced protocol becomes ≥20% of relationship traffic
   - Confidence: repeated use, related host profile changes
   - False positives: benign protocol upgrade or service migration

### Community Change Detection

1. New community
   - Strategy: community detection identifies new cluster not present in prior graph
   - Telemetry: host membership, edge density, community label
   - Thresholds: cluster contains ≥3 hosts and persists for ≥2 snapshots
   - Confidence: stable internal edge set, persistent community attribute
   - False positives: temporary event-driven grouping

2. Community growth
   - Strategy: community size increases significantly
   - Telemetry: number of hosts, new edges, join rate
   - Thresholds: size growth ≥25% or absolute addition ≥3 hosts
   - Confidence: persistent new relationships, homogeneous role pattern
   - False positives: seasonal workgroup changes

3. Community shrink
   - Strategy: size reduction beyond normal churn
   - Telemetry: host removals, edge loss
   - Thresholds: size reduction ≥25% or removal of ≥3 hosts
   - Confidence: edge loss concentrated in same segment
   - False positives: scheduled network reconfiguration

4. Community split
   - Strategy: one community splits into two or more stable subcommunities
   - Telemetry: modularity score, edge cut ratio
   - Thresholds: post-split communities have ≥80% internal cohesion and >30% fewer shared edges
   - Confidence: persistent split pattern
   - False positives: temporary load-balancing changes

5. Community merge
   - Strategy: two or more communities fuse into a larger stable group
   - Telemetry: new inter-community relationships, merged density
   - Thresholds: merged community size increase ≥20% and edge density rise
   - Confidence: repeated cross-community traffic
   - False positives: legitimate cross-domain collaboration

### Topology Change Detection

1. New hub
   - Strategy: node centrality climbs past hub threshold
   - Telemetry: degree centrality, betweenness, eigenvector, flow fan-out
   - Thresholds: degree above percentile threshold and centrality delta ≥30%
   - Confidence: multiple diverse relationships, stable position in graph
   - False positives: newly onboarded server or service gateway

2. New isolate
   - Strategy: active node becomes isolated from core traffic
   - Telemetry: degree count, community membership, current activity
   - Thresholds: degree ≤1 while still generating host activity
   - Confidence: sustained isolation over snapshot interval
   - False positives: endpoint under maintenance or segmentation

3. External expansion
   - Strategy: external boundary of graph enlarges
   - Telemetry: external endpoint count, new external community size
   - Thresholds: external edge count growth ≥30%
   - Confidence: external endpoint persistence and new geolocation
   - False positives: new SaaS adoption

4. Centrality increase
   - Strategy: node’s centrality score rises significantly
   - Telemetry: centrality time series, support edges
   - Thresholds: relative centrality increase ≥25%
   - Confidence: accompanied by role or relationship changes
   - False positives: normal scaling of network services

5. Centrality decrease
   - Strategy: node centrality drops markedly
   - Telemetry: lost edges, community role change
   - Thresholds: relative decrease ≥25%
   - Confidence: sustained reduction, not transient failover
   - False positives: load redistribution, planned failover

---

## 5. Attack Correlation Design

### General Engine Design

The `Attack Correlation Engine` consumes:
- `BehavioralDelta`
- `Host Profiles`
- `Relationships`
- `Graph State`
- `Temporal Snapshots`
- `Hypothesis Registry`

It produces `AttackHypothesis` records using:
- signature-like behavioral models
- graph-aware context
- evidence score aggregation
- severity and confidence calculations

Each hypothesis is evidence-driven, not deterministic, and includes recommended investigation actions.

### Hypothesis Registry

- The Attack Correlation Engine does not hard-code hypothesis logic. It references a `Hypothesis Registry` so detection models remain content-driven.
- The registry defines each hypothesis in a structured form with signals, severity, confidence weights, and recommendation templates.
- Example structure:
  - `beaconing`:
    - `signals`:
      - `periodicity`
      - `persistence`
    - `severity`: `high`
    - `confidence_weights`:
      - `interval_consistency`: 0.4
      - `external_persistence`: 0.3
      - `risk_delta`: 0.3
- The registry enables Layer 9 content expansion and keeps hypothesis definitions maintainable.

### Attack Campaign Model and Narrative Builder

- The platform must recognize that attacker behavior is a chain of related hypotheses, not independent signals.
- The `Narrative Builder` consumes multiple `AttackHypothesis` and `EvidenceChain` objects to construct a coherent `AttackNarrative`.
- Campaign model examples:
  - `Port Scan` → `SMB Discovery` → `RPC Movement` → `Beaconing`
  - `Host Sweep` → `Authentication Abuse` → `Persistent TLS` → `Large Outbound Transfer`
- The narrative builder uses relationship graph context, temporal sequence, and asset criticality to link hypotheses into a single story.
- `AttackNarrative` becomes the primary output for analyst investigation when multiple hypotheses form a campaign.

---

### Reconnaissance Hypotheses

1. Port Scan
   - Required signals: many distinct destination ports from a single source to one victim, short-lived relationships, low payload
   - Supporting evidence: new relationship count spike, low persistence per connection, port diversity
   - Confidence: based on source port-to-target ratio, scan cadence, absence of follow-on data transfer
   - Severity: low if internal asset, medium if target is critical or external
   - Recommended actions: identify scanning host, review host role, check related external contacts, compare against known maintenance windows

2. Host Sweep
   - Required signals: repeated connection attempts from one source to the same port across many hosts
   - Supporting evidence: sequential endpoint list, same destination port, minimal data
   - Confidence: host count threshold, interval clustering, source persistency
   - Severity: medium for sensitive zones, high if on critical application port
   - Recommended actions: inspect source asset, verify normal network discovery behavior, check for lateral movement preparation

3. Service Enumeration
   - Required signals: repeated service-specific probes, new service handshake attempts, targeted service port access from one source
   - Supporting evidence: stateful protocol exchange, repeated service banner or handshake behavior, relationship metadata
   - Confidence: service-specific success patterns, host role mismatch
   - Severity: medium
   - Recommended actions: validate service ownership, inspect target host for unusual service discovery, review preceding reconnaissance deltas

---

### Initial Access Hypotheses

1. Authentication Abuse
   - Required signals: unusual access attempts to authentication services, novel source-host pairing, new relationship to auth endpoints
   - Supporting evidence: increased auth traffic, host risk elevation, service access pattern changes
   - Confidence: auth endpoint relevance, repeated failed or anomalous login sessions
   - Severity: medium-high
   - Recommended actions: examine auth service logs, validate source host identity, check account usage patterns

2. Brute Force
   - Required signals: repeated login attempts to same account or host, high failure ratio, short interval bursts
   - Supporting evidence: multiple auth flows, relationship persistence to auth endpoint, host role targeting
   - Confidence: failure ratio >70%, burst count above threshold, target importance
   - Severity: high
   - Recommended actions: isolate source, inspect adjacent hosts, correlate with known brute-force tooling patterns, escalate to credential/security team

3. Credential Stuffing
   - Required signals: repeated login attempts across multiple accounts from same source, moderate success, multiple auth targets
   - Supporting evidence: distribution of auth attempts, source reuse, host profile unusualness
   - Confidence: same source reused across accounts, success signaled by session persistence
   - Severity: high
   - Recommended actions: review account access, verify password reuse risk, check for breached credential sets, involve identity team

---

### Command & Control Hypotheses

1. Beaconing
   - Required signals: periodic external connections from a host, low payload, consistent intervals
   - Supporting evidence: low interval variance, persistent external relationship, risk escalation
   - Confidence: interval stability score, external endpoint classification, lack of benign control-plane traffic
   - Severity: high
   - Recommended actions: map external endpoint, inspect host for additional suspicious behavior, collect timeline, evaluate against threat intelligence

2. Persistent TLS
   - Required signals: long-lived TLS sessions to external endpoint, repeated reconnections, unusual server identity
   - Supporting evidence: session duration, relationship persistence, certificate anomalies or unusual SNI
   - Confidence: TLS duration + endpoint persistence, external classification
   - Severity: high
   - Recommended actions: inspect TLS flow metadata, check endpoint reputation, review host outbound policy, validate business justification

3. Reverse Shell Behavior
   - Required signals: outbound interactive session followed by reverse access patterns, new inbound connections correlated to prior outbound contact
   - Supporting evidence: internal host role risk increase, chained relationships to same external IP, shell-like port usage
   - Confidence: chain coherence across snapshots, host risk profile, session persistence
   - Severity: high
   - Recommended actions: isolate suspect host, correlate with process/endpoint telemetry if available, analyze session chronology, validate with external threat intel

---

### Lateral Movement Hypotheses

1. SMB Movement
   - Required signals: new or increasing SMB relationships between hosts, authentication service access, repeated file share attempts
   - Supporting evidence: host profile Windows/SMB role, relationship persistence, community spread
   - Confidence: protocol identification, host role relevance, path progress
   - Severity: high
   - Recommended actions: examine destination host criticality, review account activity, identify pivot path, inspect neighboring hosts

2. RPC Movement
   - Required signals: DCE/RPC or MSRPC traffic patterns to new hosts, service enumeration preceding access
   - Supporting evidence: RPC endpoint calls, relationship persistence, internal host propagation
   - Confidence: protocol-specific telemetry, host role alignment
   - Severity: high
   - Recommended actions: map RPC sessions, validate with service ownership, search for additional RPC-based movement, escalate if domain services targeted

3. Internal Propagation
   - Required signals: chain of new relationships across multiple hosts, growing community size, hazard propagation from an initial host
   - Supporting evidence: cascade pattern, shared attack path, rising community risk
   - Confidence: propagation coherence, host risk continuity
   - Severity: high
   - Recommended actions: identify source host, segment affected community, check adjacent hosts, block suspicious lateral traffic paths

---

### Exfiltration Hypotheses

1. DNS Tunneling
   - Required signals: high volume of DNS queries to external domains, anomalous query length/entropy, persistent external DNS relationships
   - Supporting evidence: query pattern irregularity, relationship persistence, low payload but high query count
   - Confidence: entropy metrics, abnormal DNS relationship emergence
   - Severity: high
   - Recommended actions: inspect DNS query payloads/domains, validate against expected DNS behavior, coordinate with DNS/security team

2. Data Staging
   - Required signals: internal host(s) moving data to staging servers or data staging hosts, repeated internal transfers, new host role changes
   - Supporting evidence: host profile changes, internal relationship persistence, growing data aggregation behavior
   - Confidence: staging host role, volume patterns, community involvement
   - Severity: high
   - Recommended actions: identify staging locations, review file transfer patterns, validate business purpose, survey related hosts

3. Large Outbound Transfer
   - Required signals: outbound relationship with bytes exceeding normative thresholds, unusual destination, sustained transfer
   - Supporting evidence: high-volume flow, protocol mismatch, risk elevated host
   - Confidence: volume relative to baseline, destination classification
   - Severity: critical
   - Recommended actions: capture transfer details, isolate outbound channel, validate destination, initiate incident response if confirmed

---

## 6. Evidence Chain Framework

### Framework Principles

- Evidence must be explicit, traceable, and anchored to raw behavioral signals
- Hypotheses are expressed as “possible” or “likely”, not “detected”
- Each chain must separately capture supporting evidence and contradictory evidence
- Contradictory evidence reduces chain confidence and may lower severity or priority
- Confidence is derived from evidence weights, hypothesis priors, and contradiction impact
- Chains must be human-readable and machine-queryable

### Contradictory Evidence Engine

- The Evidence Chain Manager operates an explicit contradiction engine that classifies evidence items as supporting or contradictory.
- Contradictory evidence examples include known benign endpoints, maintenance windows, or documented update traffic.
- If contradictory evidence is present, the chain computes a negative confidence impact and records the reason.
- Example:
  - Supporting: `periodic intervals`, `persistent TLS`
  - Contradictory: `known Microsoft update CDN`, `benign service endpoint`

### Evidence Chain Structure

- `EvidenceChain`
  - `chainId`
  - `hypothesisId`
  - `entityContext` (hosts, relationships, communities)
  - `evidenceItems`
  - `chainScore`
  - `confidence`
  - `summary`
  - `createdAt`
  - `updatedAt`

- `EvidenceItem`
  - `evidenceId`
  - `type` (behavioral, temporal, topological, contextual, external)
  - `source` (delta, profile, snapshot, threat intel)
  - `detail`
  - `timestamp`
  - `weight`
  - `confidenceImpact`

### Evidence Categories

- Behavioral: risk delta, role change, protocol change
- Temporal: persistence increase, interval regularity, timeline progression
- Topological: new hub, community merge, centrality shift
- Contextual: host asset score, external classification, service role
- External: threat intelligence tags, known malicious endpoint match

### Chain Generation

1. Start with a candidate `AttackHypothesis`
2. Collect all relevant `BehavioralDelta` records
3. Augment with host and relationship context
4. Score each evidence item
5. Build a narrative describing the sequence of events
6. Compute overall chain confidence and score

### Confidence Strategy

- Base confidence = hypothesis prior
- Evidence contribution = weighted sum of evidence item scores
- Adjust for:
  - evidence redundancy
  - contradictory signals
  - context strength
- Normalize to a 0–100 range
- Represent as percentage with explicit justification

### Severity Strategy

- Compute severity from:
  - asset criticality
  - attack type impact
  - evidence strength
  - graph/topology implications
- Map to:
  - Informational
  - Low
  - Medium
  - High
  - Critical

### Example Evidence Chain

Host: `10.2.28.88`

Evidence:
- `Persistent TLS relationship` to external IP
- `Low interval variance` across 6 snapshots
- `Risk escalation` from 40 to 78
- `External communication persistence` to new external peer

Hypothesis:
- `Possible C2 Beaconing`

Confidence:
- `82%`

Interpretation:
- The chain shows a sustained external contact pattern combined with a rising host risk profile and a stable beaconing interval. It does not assert malware, only that observed behavior aligns with command-and-control hypotheses.

---

## 7. Investigation Prioritization Framework

### Priority Factors

- `Risk delta`
  - magnitude of host or relationship risk change
  - rapid escalation carries more weight

- `Host criticality`
  - asset value
  - role in business or infrastructure
  - exposure level
  - derived from a `criticality_score` (0-100)

- `Criticality score`
  - a 0-100 score derived from asset class and operational importance
  - domain controller, authentication service, file server, workstation, and external host are scored differently
  - this score heavily influences priority and escalation decisions

- `Relationship criticality`
  - external exposure
  - protocol sensitivity
  - persistence and volume

- `Community impact`
  - number of hosts affected
  - community growth/shrink patterns
  - segmentation breach potential

- `Graph impact`
  - hub emergence
  - centrality shifts
  - new isolates or expansion points

- `Attack confidence`
  - hypothesis confidence score
  - coherence of evidence chain

### Scoring Methodology

1. Compute sub-scores:
   - `Behavioral Risk Score`
   - `Asset Criticality Score`
   - `Relationship Impact Score`
   - `Community Impact Score`
   - `Graph Topology Score`
   - `Attack Confidence Score`

2. Weighted aggregation:
   - `PriorityScore = w1*Risk + w2*Criticality + w3*Relationship + w4*Community + w5*Graph + w6*Confidence`

3. Define thresholds:
   - `Critical`: ≥ 90
   - `High`: 70–89
   - `Medium`: 50–69
   - `Low`: 30–49
   - `Informational`: < 30

4. Apply overrides:
   - any hypothesis involving critical asset + high confidence → escalate to `Critical`
   - community spread into segmented zones → elevate priority
   - external C2 + data exfiltration signals → elevate priority

### Priority Levels

- `Informational`
  - low impact, low confidence
  - useful for awareness, not immediate action

- `Low`
  - suspicious but not urgent
  - likely candidate for monitoring or routine validation

- `Medium`
  - worthy of analyst review
  - may require follow-up investigation

- `High`
  - strong evidence, relevant asset, or suspicious propagation
  - should be prioritized in triage

- `Critical`
  - high confidence on high-value asset
  - indicates likely attack path or active compromise

### Investigation Candidate Outputs

- `InvestigationCandidate`
  - candidate id
  - priority level
  - candidate score
  - associated hypotheses
  - impacted entities
  - recommended next steps
  - rationale summary
  - status

- Candidate ranking supports:
  - sorting
  - grouping by attack path
  - analyst assignment
  - feedback capture

---

## 8. Data Models

### BehavioralDelta

- Required fields:
  - `deltaId`
  - `entityType` (`host`, `relationship`, `community`, `topology`)
  - `deltaType` (`new`, `removed`, `increase`, `decrease`, `split`, `merge`, etc.)
  - `entityId`
  - `sourceSnapshotId`
  - `targetSnapshotId`
  - `detectedAt`
  - `confidence`
  - `metrics` (structured numeric payload)
  - `summary`

- Optional fields:
  - `hostId`, `relationshipId`, `communityId`, `topologyMetric`
  - `contextTags`
  - `relatedDeltas`
  - `baselineComparison`

### AttackHypothesis

- Required fields:
  - `hypothesisId`
  - `hypothesisType`
  - `title`
  - `summary`
  - `impactedEntities`
  - `confidence`
  - `severity`
  - `createdAt`
  - `status`

- Optional fields:
  - `evidenceChainId`
  - `supportingEvidenceIds`
  - `relatedDeltaIds`
  - `recommendedActions`
  - `referenceTags` (e.g., attack technique families)
  - `criticalityScore` (0-100 derived from impacted asset class)

### EvidenceChain

- Required fields:
  - `chainId`
  - `hypothesisId`
  - `evidenceItems`
  - `confidence`
  - `score`
  - `summary`
  - `createdAt`

- Optional fields:
  - `contradictoryEvidence`
  - `externalContext`
  - `sourceMetadata`
  - `version`

### InvestigationCandidate

- Required fields:
  - `candidateId`
  - `priorityLevel`
  - `priorityScore`
  - `associatedHypothesisIds`
  - `impactedHosts`
  - `impactedRelationships`
  - `recommendedNextSteps`
  - `createdAt`
  - `assetCriticalityScore` (aggregated 0-100 score reflecting the highest-value assets in scope)

- Optional fields:
  - `analystNotes`
  - `status` (`new`, `in_review`, `actioned`, `closed`)
  - `assignedTo`
  - `resolutionSummary`

### AttackNarrative

- Required fields:
  - `narrativeId`
  - `title`
  - `summary`
  - `confidence`
  - `severity`
  - `timeline`
  - `supportingEvidence`
  - `impactedAssets`
  - `recommendedActions`

- Optional fields:
  - `attackPath`
  - `relatedCandidates`
  - `threatContext`
  - `analystGuidance`

### Relationships Between Entities

- `BehavioralDelta` → may link to one or more `AttackHypothesis`
- `AttackHypothesis` → has one `EvidenceChain`
- `EvidenceChain` → references multiple `EvidenceItem`
- `InvestigationCandidate` → aggregates one or more `AttackHypothesis`
- `AttackNarrative` → summarizes `InvestigationCandidate` and key evidence

### Object Lifecycle

- `BehavioralDelta`
  - created each snapshot comparison
  - enriched with context
  - archived after full correlation

- `AttackHypothesis`
  - created from delta evidence
  - scored and prioritized
  - reviewed/updated as more data arrives
  - closed when investigation resolves or stale

- `EvidenceChain`
  - built at hypothesis creation
  - revised if supporting evidence changes
  - retained for auditability and explainability

- `InvestigationCandidate`
  - created from prioritized hypotheses
  - reviewed by analyst
  - status transitions: `new` → `in_review` → `actioned`/`closed`

- `AttackNarrative`
  - generated for analyst communication
  - persists as summary of the investigation candidate
  - used by future reporting layers

---

## 9. Analyst Workflow

### End-to-end Journey

1. `PCAP Upload`
   - analyst submits PCAP
   - system verifies capture integrity and metadata

2. `Behavioral Reconstruction`
   - Layers 1-4 parse packets, build canonical events, flows, host profiles, relationships, graph state, snapshots

3. `Behavioral Changes`
   - Layer 5 ingests snapshots and detects `BehavioralDelta` changes

4. `Attack Hypotheses`
   - Layer 5 correlates deltas into `AttackHypothesis`
   - evidence chains are assembled

5. `Investigation Priorities`
   - findings are scored, ranked, and converted into `InvestigationCandidate`
   - priority labels assigned

6. `Evidence Review`
   - analyst reviews prioritized candidates
   - inspects evidence chain details, timelines, and impacted assets

7. `Analyst Decision`
   - analyst chooses:
     - investigate deeper
     - validate as benign
     - escalate
     - archive
   - feedback captured for future tuning

### Detailed Analyst Flow

- Analyst sees a ranked summary of top candidates first
- Each candidate includes:
  - hypothesis title
  - risk delta
  - impacted hosts
  - evidence summary
  - priority level
- Analyst clicks into a candidate to see:
  - supporting evidence
  - related behavioral deltas
  - host/relationship topology changes
  - attack narrative
- Analyst assesses:
  - whether the behavior aligns with known activity
  - whether the host is critical
  - whether evidence is sufficient for response
- Analyst takes action:
  - mark as `requires attention`
  - request further packet or event investigation
  - add notes and close if benign
- The system retains analyst decisions to inform later tuning and potential machine-learned ranking

---

## 10. Success Metrics

### Accuracy

- `Hypothesis precision` = confirmed true hypotheses / total hypotheses presented
- `Hypothesis recall` = confirmed true hypotheses / known attack behaviors present
- `Evidence coverage` = percentage of hypotheses with full evidence chains

### Explainability

- `Traceability score` = percentage of hypotheses with complete evidence item provenance
- `Analyst confidence rating` from survey or feedback
- `Narrative clarity` = ratio of candidates with human-readable summaries

### Investigation Usefulness

- `Time to first actionable finding`
- `Percentage of top candidates that lead to analyst-reported investigations`
- `Reduction in time to triage compared to raw PCAP analysis`

### False Positive Reduction

- `False positive rate` per hypothesis family
- `Candidate noise ratio` = low-priority artifacts generated per useful investigation
- `Triage load reduction` from candidate ranking

### Analyst Efficiency

- `Average investigation throughput`
- `Mean time to decision`
- `Number of candidates resolved per analyst hour`
- `Analyst adoption rate` for Layer 5 outputs

---

## 11. Risks & Limitations

- `Incomplete PCAPs`: missing packets can hide behavior or create false deltas
- `Baseline drift`: normal environment changes may be misclassified as suspicious
- `Encrypted traffic`: limited visibility into payload-level behavior
- `Protocol parsing gaps`: unknown protocols reduce accuracy of correlation
- `Threshold sensitivity`: static thresholds may require frequent tuning
- `Ambiguous behavior`: legitimate admin activity may mimic attack patterns
- `Graph scale`: very large graphs may slow delta detection if not partitioned
- `Over-correlation`: linking unrelated deltas into spurious hypotheses
- `Evidence bias`: strong indicators may overshadow important weaker signals

---

## 12. Future Layer Integration Strategy

### Layer 6: Investigation Engine
- Expose:
  - `InvestigationCandidate` API
  - evidence chain query interface
  - hypothesis lifecycle hooks
- Support:
  - case creation from prioritized candidates
  - automated analyst playbooks
  - feedback loop into priority scoring

### Layer 7: Replay Engine
- Expose:
  - timeline anchors from `Temporal Snapshots`
  - delta event series
  - relationship change playback
- Support:
  - replay of behavior associated with hypotheses
  - drill-down from candidate to exact packet/flow intervals

### Layer 8: Visualization Platform
- Expose:
  - graph state snapshots
  - community and topology change overlays
  - evidence chain heatmaps
- Support:
  - analyst-facing dashboards
  - interactive exploration of delta-driven attack paths

### Layer 9: Detection Content Expansion
- Expose:
  - hypothesis definition registry
  - evidence template catalog
  - threshold configuration interface
- Support:
  - addition of new attack types
  - tuning without code changes
  - content-driven correlation updates

### Layer 10: Incident Reporting
- Expose:
  - narrative export packages
  - investigation summaries
  - confidence-severity metadata
- Support:
  - automated incident reports
  - SLA-aligned escalation documents
  - audit-ready explanation artifacts

---

## 13. Recommended Implementation Roadmap

### Phase 1: Foundational Layer 5
- Define data schemas for deltas, hypotheses, evidence, candidates, narratives
- Build `Delta Ingestion & Normalization`
- Implement host and relationship delta detection
- Validate on existing PCAPs

### Phase 2: Correlation Engine
- Implement initial attack hypothesis models
- Build evidence chain framework
- Create confidence and severity scoring components

### Phase 3: Prioritization and Output
- Implement investigation prioritization
- Build candidate ranking and priority labels
- Design analyst output structures and API payloads

### Phase 4: Validation and Tuning
- Test with representative PCAPs and analyst feedback
- Tune thresholds and weightings
- Measure against success metrics

### Phase 5: Integration Readiness
- Create future-layer interfaces
- Document API contracts for Layers 6–10
- Build export and packaging capabilities

### Phase 6: Operationalization
- Deploy with monitoring for false positives and performance
- Capture analyst decisions for continuous improvement
- Iterate on detection content and hypothesis coverage

---