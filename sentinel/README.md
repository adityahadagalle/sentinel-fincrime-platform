# SENTINEL — Real-Time Financial Crime Detection & Autonomous Investigation Platform

**SENTINEL** is an enterprise-grade, real-time financial crime detection, dynamic case management, and autonomous investigation platform. Built for financial intelligence units (FIUs) and compliance teams, SENTINEL ingests high-velocity transaction streams, executes deterministic hybrid risk scoring, constructs interactive multi-hop financial network graphs, orchestrates a 5-stage automated investigation pipeline, and enforces strict governance boundaries between automated execution and human analyst authorization.

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Problem Statement](#-problem-statement)
3. [Innovation & Core Concepts](#-innovation--core-concepts)
4. [Key Capabilities](#-key-capabilities)
5. [System Architecture](#-system-architecture)
6. [End-to-End Transaction Flow](#-end-to-end-transaction-flow)
7. [Real-Time Monitoring & Telemetry](#-real-time-monitoring--telemetry)
8. [Risk Scoring Engine](#-risk-scoring-engine)
9. [5-Stage Automated Investigation Pipeline](#-5-stage-automated-investigation-pipeline)
10. [Autonomous Policy & Action Engine](#-autonomous-policy--action-engine)
11. [Human Approval Boundary & Governance](#-human-approval-boundary--governance)
12. [Dynamic Case Management & Lifecycle](#-dynamic-case-management--lifecycle)
13. [Multi-Hop Graph & Network Intelligence](#-multi-hop-graph--network-intelligence)
14. [Audit Trail & Compliance Export](#-audit-trail--compliance-export)
15. [Qwen / Ollama Advisory Intelligence](#-qwen--ollama-advisory-intelligence)
16. [Technology Stack](#-technology-stack)
17. [Repository Structure](#-repository-structure)
18. [Dependencies & Requirements](#-dependencies--requirements)
19. [Environment Configuration](#-environment-configuration)
20. [Local Installation & Setup](#-local-installation--setup)
21. [Local Run Instructions](#-local-run-instructions)
22. [API Reference](#-api-reference)
23. [WebSocket Event Reference](#-websocket-event-reference)
24. [Testing & Quality Assurance](#-testing--quality-assurance)
25. [Development Notes](#-development-notes)
26. [Security & Governance Boundaries](#-security--governance-boundaries)
27. [Current Limitations](#-current-limitations)
28. [Future Extension Areas](#-future-extension-areas)

---

## 🎯 Project Overview

SENTINEL bridges the critical gap between real-time transaction monitoring and complex forensic investigations. By combining deterministic rule scoring, a rule-guided ML emulator, multi-hop graph topology analysis, an automated 5-agent investigation pipeline, and an advisory LLM interface (Qwen 3), SENTINEL enables security analysts to detect mule chains, circular flows, and funnel accounts in milliseconds, while enforcing regulatory compliance and complete auditability.

---

## ⚠️ Problem Statement

Modern financial crime (money laundering, mule networks, rapid velocity attacks, authorized push payment fraud) operates at sub-second speeds across multi-layered account networks. Traditional anti-money laundering (AML) platforms suffer from:

- **Slow Manual Triage**: High alert volumes overload compliance analysts.
- **Siloed Investigations**: Transactions evaluated in isolation miss multi-hop mule chains.
- **Uncontrolled Automation**: Blind automated freezes risk false-positive account lockouts and regulatory non-compliance.
- **Black-Box AI**: Unexplainable LLM recommendations violate regulatory transparency mandates.

SENTINEL solves this by decoupling **Deterministic Policy Enforcement** from **Advisory AI Intelligence**, ensuring all financial enforcement is strictly governed while empowering analysts with automated forensic synthesis.

---

## 💡 Innovation & Core Concepts

1. **Human-in-the-Loop Governance Boundary**: Hard enforcement rules (such as Account Freezes) require explicit human operator authorization (`REQUIRES_OPERATOR_ACTION`), while routine actions (monitoring, escalation, STR filings) can execute autonomously when Automate Mode is enabled.
2. **Deterministic 5-Stage Investigation Pipeline**: An asynchronous multi-agent orchestrator runs Evidence Collection, Contextual Analysis, Regulatory Assessment, Audit Explanation, and Analyst Decision Support, persisting immutable stage reports.
3. **Investigation Confidence Index**: A deterministic metric (0.0 to 100.0) combining evidence completeness (35%), agent agreement (40%), and source diversity (25%) minus contradiction penalties, measuring evidence strength rather than raw fraud probability.
4. **Advisory LLM Integration**: Qwen 3 (via local Ollama) acts purely as an advisory analyst assistant. It receives pre-sanitized context from the 5 investigation stages and can **never** trigger account freezes or alter database states.
5. **Dual Storage Flexibility**: Operates in zero-setup **In-Memory Store** mode for rapid local development, or switches seamlessly to **PostgreSQL + Alembic** for production durability.

---

## 🚀 Key Capabilities

- **Real-Time Transaction Ingestion**: Sub-millisecond evaluation of incoming UPI, IMPS, NEFT, CARD, and SWIFT transactions.
- **Hybrid Risk Scoring**: Evaluates amount deviations, time anomalies (10 PM – 6 AM), new receiver flags, active call indicators, cross-border status, velocity spikes, and crypto involvement.
- **Multi-Hop Topology Detection**: Identifies 6 distinct network patterns: Normal Payment, 3-Hop Layering, 5-Hop Mule Chains, Funnel Accounts, Fan-Out Dispersion, and Circular Flows.
- **Interactive Cytoscape Graph Workstation**: Visualizes fraud money flows, lead node suspect identification, node freezing, and real-time recoverable asset calculation.
- **Attack Mode Simulator**: Generates connected 5-hop, 6-node suspicious cascades for live demonstration and stress testing.
- **Compliance-Grade Audit Export**: Generates 16-field UTF-8 BOM CSV audit logs with formula injection protection (`='`, `@'`).

---

## 🏗️ System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           TRANSACTION STREAM                                      │
│               (Internal Generator / Simulator / REST API Endpoint)                │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │
                                         ▼
                             ┌──────────────────────┐
                             │  POST /transaction   │
                             │ (FastAPI Ingestion)  │
                             └───────────┬──────────┘
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATION PIPELINE                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 1. Persistence & Account State Initialization                                     │
│ 2. Hybrid Risk Scoring (Rule Engine + Rule-Guided ML Emulator)                    │
│ 3. Case Linking & Graph Topology Building                                         │
│ 4. Deterministic Autonomous Policy Evaluation                                     │
│ 5. Simulated Action Execution & State Transition                                 │
│ 6. Asynchronous 5-Stage Investigation Pipeline Execution                          │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│     DATA STORAGE ADAPTER LAYER    │       │     WEBSOCKET BROADCAST MANAGER   │
├───────────────────────────────────┤       ├───────────────────────────────────┤
│ - In-Memory Store (Development)   │       │ Pushes real-time events:          │
│ - PostgreSQL Store (Production)   │       │ - tx_scored                       │
│ - Alembic Schema Migrations       │       │ - case_updated                    │
└──────────────────┬────────────────┘       │ - transaction.action              │
                   │                        │ - automation.action.executed      │
                   │                        └──────────────────┬────────────────┘
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                REACT FRONTEND                                     │
├───────────────────────────────────────────────────────────────────────────────────┤
│ - Feed Page: Real-time transaction stream with risk indicators                    │
│ - Analytics Dashboard: Telemetry KPIs, Investigation Confidence, Risk Trends     │
│ - Cases Workbench: Active investigations, Golden Timers, Disposition Modal        │
│ - Graph Workstation: Interactive Cytoscape network visualization & Node Control   │
│ - Qwen Intelligence Panel: Advisory AI synthesis and human analyst briefing       │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 End-to-End Transaction Flow

1. **Ingestion**: Transaction received at `POST /transaction`.
2. **Scoring**: `score_transaction()` calculates rule score; `predict_ml_score()` generates correlated ML emulator score.
3. **Policy Evaluation**: `evaluate_autonomous_policy()` checks risk thresholds, case state, and `automation_mode`.
4. **Action Execution**: `execute_simulated_action()` updates account state (`ACTIVE`, `FROZEN`, `BLOCKED`, `MONITORING`, `ACTIONED`) and logs 21-field audit record with idempotency check.
5. **Investigation Pipeline**: `investigation_orchestrator` runs 5 analytical stages asynchronously for high-risk cases.
6. **Real-time Sync**: `ConnectionManager` broadcasts events (`tx_scored`, `case_updated`, `transaction.action`) to React clients over WebSockets.
7. **Analyst Review**: Compliance analysts inspect cases, view Cytoscape graphs, read Qwen advisory reports, and submit stateful dispositions (`POST /cases/{case_id}/disposition`).

---

## 📊 Real-Time Monitoring & Telemetry

The React frontend maintains a persistent WebSocket connection (`useWebSocket.js`) with automatic fallback to polling (`/cases` every 2s) if disconnected.

- **System Status Bar**: Displays status (`LIVE`, `POLLING`, `RECONNECTING`, `OFFLINE`).
- **Live Alert Toasts**: Pops toasts for fresh (< 30s) high-risk transactions (`sentinel_alert`).
- **Action Toasts**: Notifies operators when actions are executed or require manual authorization (`sentinel_action`).

---

## ⚖️ Risk Scoring Engine

SENTINEL uses a hybrid deterministic scoring model (`app/engines/scoring_engine.py`) combined with a **Rule-Guided ML Emulator** (`app/services/ml_risk_engine.py`).

### Rule-Based Weighting

| Factor | Weight | Trigger Condition |
| :--- | :--- | :--- |
| **New Receiver** | 35% | First time transferring to recipient account |
| **Amount Deviation** | 30% | Transfer amount exceeds historical monthly average |
| **Time Anomaly** | 20% | Off-hours transaction (10 PM – 6 AM) |
| **Active Call Flag** | 15% | Device on active phone call during transaction |

### Dynamic Boost Telemetry

- **Velocity Spike**: +40 score boost
- **Cross-Border Transfer**: +50 score boost
- **Device / Location Change**: +40 score boost
- **Crypto-Related**: +50 score boost
- **Remote Access Active**: +50 score boost
- **Scripted Fraud Behavior**: +40 score boost

### Rule-Guided ML Emulator

Produces a correlated ML score ($r > 0.95$) tracking the rule score with band-proportional variation:
- **High Risk ($\ge 80$)**: $\pm 5$ variation
- **Medium Risk ($\ge 50$)**: $\pm 10$ variation
- **Low Risk ($< 50$)**: $\pm 15$ variation

*Note: The ML engine runs in Emulator mode by default to guarantee stability without binary dependency issues.*

---

## 🔍 5-Stage Automated Investigation Pipeline

When a high-risk case is created, `investigation_orchestrator.py` asynchronously executes 5 dependency-ordered stages:

1. **EVIDENCE (`evidence_agent.py`)**: Collects empirical evidence across transaction metadata, historical baselines, counterparty flows, network graphs, and recovery amounts.
2. **CONTEXTUAL (`contextual_agent.py`)**: Evaluates behavioral patterns (mule cascades, velocity spikes, rapid off-boarding).
3. **REGULATORY (`regulatory_agent.py`)**: Assesses PMLA/AML regulatory indicators, STR reporting implications, and heuristic risk indices.
4. **AUDIT_EXPLANATION (`audit_explanation_agent.py`)**: Generates step-by-step audit narratives, key findings, and data gap analyses.
5. **DECISION_SUPPORT (`analyst_agent.py`)**: Synthesizes findings into review priority ratings (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and recommended human disposition options.

### Investigation Confidence Index Formula

$$\text{Score} = \text{clamp}\left(\text{round}\left(0.35 \cdot C + 0.40 \cdot A + 0.25 \cdot D - 1.0 \cdot K, 1\right), 0.0, 100.0\right)$$

- $C$: Evidence Completeness % (coverage across 5 core evidence dimensions)
- $A$: Agent Severity Agreement % (consensus across evaluating agents)
- $D$: Source Diversity % (unique evidence sources)
- $K$: Contradiction Count Penalty (conflicts between CRITICAL and LOW ratings)

---

## 🤖 Autonomous Policy & Action Engine

`evaluate_autonomous_policy()` in `app/engines/autonomous_policy_engine.py` enforces safety rules before any action is executed:

- **Fail-Closed Design**: Rejects payload on missing transaction data, invalid risk scores, or closed case states (`CLOSED_CONFIRMED_FRAUD`, `CLOSED_FALSE_POSITIVE`).
- **Automate Mode Switch**:
  - **Automate OFF**: Routine actions default to `DO_NOT_EXECUTE` (`POL-MODE-OFF`). Manual intervention required.
  - **Automate ON**: Autonomous execution authorized for `MONITOR`, `ENHANCED_MONITORING`, `ESCALATE_ANALYST_REVIEW`, `BLOCK`, `REJECT_TRANSACTION`, `FILE_STR`, `CLOSE_ACCOUNT`.

---

## 🛡️ Human Approval Boundary & Governance

> [!IMPORTANT]
> **Account Freeze Safety Rule**:
> `FREEZE` actions **NEVER** execute autonomously.
> Even when Automate Mode is ON and a transaction has a CRITICAL risk score ($\ge 85$), the policy engine returns:
> `execution_status: "REQUIRES_OPERATOR_ACTION"`
> 
> An account freeze can **ONLY** be executed when a human analyst explicitly clicks **Freeze** in the UI or invokes `POST /action/freeze` / `POST /cases/{case_id}/transactions/{tx_id}/freeze`.

---

## 📁 Dynamic Case Management & Lifecycle

### Case Statuses

- **`NEW`**: Automatically created upon high-risk transaction detection.
- **`HIGH_RISK`**: Multiple suspicious transactions linked to the case graph.
- **`ACTIONED`**: Simulated action or manual disposition executed.
- **`MONITORING`**: Placed under surveillance.
- **`CLOSED` / `CLOSED_CONFIRMED_FRAUD`**: Resolved as confirmed fraud.
- **`CLOSED_FP` / `CLOSED_FALSE_POSITIVE`**: Resolved as false positive.

### Recovery Calculation

$$\text{Recoverable Amount} = \sum \text{Balances in non-withdrawn, non-frozen accounts}$$
$$\text{Recovery \%} = \frac{\text{Recovered Assets} + \text{Recoverable Amount}}{\text{Total Fraud Exposure}} \times 100$$

---

## 🕸️ Multi-Hop Graph & Network Intelligence

SENTINEL builds connected investigation graphs (`app/engines/graph_engine.py`) visualized using **Cytoscape.js** (`GraphCanvas.jsx`):

- **Lead Node Detection**: Account with the highest incoming transaction volume flagged as primary suspect.
- **Graph Topology Patterns**:
  - **Pattern A (Normal)**: Direct sender-receiver transfer.
  - **Pattern B (3-Hop / 5-Hop Mule Chain)**: Rapid multi-account layering chain.
  - **Pattern C (Funnel)**: Multiple victim accounts pooling into a single funnel account.
  - **Pattern D (Fan-Out)**: Single source dispersing funds to multiple destination accounts.
  - **Pattern E (Circular Flow)**: Closed-loop money cycling ($A \to B \to C \to D \to A$).

---

## 📜 Audit Trail & Compliance Export

SENTINEL logs immutable 21-field audit records for every mode change, transaction scoring event, autonomous decision, and analyst disposition.

### CSV Export Feature (`GET /export/sentinel_audit.csv`)

- **Authoritative Data Merging**: Combines repository events, in-memory actions, and case disposition histories.
- **Dual Section Report**:
  1. *SENTINEL Complete Action Audit Log* (16 canonical fields: Timestamp, Audit ID, Case ID, Tx ID, Account ID, Risk Score, Risk Level, Action, Execution Mode, Actor, Action Status, Previous State, Resulting State, Reason, Policy Rule ID, Operator ID).
  2. *SENTINEL Transaction Feed Audit*.
- **Security Sanitization**: Prepends `'` to leading formula characters (`=`, `+`, `-`, `@`, `\t`, `\r`) to prevent CSV Injection in Microsoft Excel. Includes UTF-8 BOM (`\ufeff`).

---

## 🧠 Qwen / Ollama Advisory Intelligence

SENTINEL integrates local **Qwen 3 (8B)** via Ollama (`app/services/ollama_service.py` & `app/routes/intelligence.py`):

- **Endpoint**: `http://localhost:11434/api/chat`
- **Role**: **Advisory Intelligence Only**.
- **Data Boundary**: Sanitized context containing non-sensitive graph topology, primary transaction summaries, and outputs from the 5 deterministic investigation stages.
- **Strict Constraints**: Qwen's output is parsed into structured JSON (`AIAnalysisResponse`). It **cannot** trigger actions, access database credentials, or override policy engine decisions.
- **Graceful Fallback**: If Ollama is uninstalled or offline, the API returns `status: "unavailable"` without breaking the core application or blocking startup.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **ASGI Server**: Uvicorn
- **Concurrency**: Python `asyncio` & WebSockets
- **ORM / Database**: SQLAlchemy 2.0 (AsyncSession), PostgreSQL (`asyncpg`, `psycopg2-binary`), Alembic migrations
- **Validation**: Pydantic v2
- **Advisory LLM Client**: Standard library `urllib.request` (zero third-party LLM SDK dependencies)

### Frontend
- **Framework**: React 18 & Vite 5
- **Styling**: TailwindCSS & PostCSS
- **Graph Visualization**: Cytoscape.js & `cytoscape-dagre` layout
- **Analytics Charts**: Recharts
- **Icons**: Lucide React
- **Routing**: React Router v6

---

## 📂 Repository Structure

```
sentinel/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py              # Risk scoring weights & parameters
│   │   │   ├── constants.py           # Enums & constants
│   │   │   ├── data_store.py          # In-memory store dict
│   │   │   └── models/                # Core domain schemas
│   │   ├── db/
│   │   │   ├── config.py              # PostgreSQL database settings
│   │   │   └── session.py             # AsyncSession engine & factory
│   │   ├── engines/
│   │   │   ├── scoring_engine.py      # Rule-based risk scoring
│   │   │   ├── case_manager.py        # Case linking & creation
│   │   │   ├── graph_engine.py        # Cytoscape graph builder
│   │   │   ├── recovery_engine.py     # Asset recovery calculation
│   │   │   ├── response_policy_engine.py
│   │   │   └── autonomous_policy_engine.py # Phase 16 safety & policy rules
│   │   ├── models/                    # SQLAlchemy database entities
│   │   ├── repositories/
│   │   │   ├── base.py                # AbstractCaseRepository interface
│   │   │   ├── in_memory.py           # In-memory store adapter
│   │   │   ├── postgres.py            # PostgreSQL database adapter
│   │   │   └── dependencies.py        # FastAPI Dependency Injection
│   │   ├── routes/
│   │   │   └── intelligence.py        # Qwen / Ollama advisory endpoints
│   │   ├── services/
│   │   │   ├── orchestrator.py        # Transaction pipeline orchestrator
│   │   │   ├── ml_risk_engine.py      # Rule-Guided ML Emulator
│   │   │   ├── simulated_action_executor.py # Action executor & audit logger
│   │   │   ├── investigation_orchestrator.py # 5-Stage investigation pipeline
│   │   │   ├── evidence_agent.py      # Stage 1 Evidence Agent
│   │   │   ├── contextual_agent.py    # Stage 2 Contextual Agent
│   │   │   ├── regulatory_agent.py    # Stage 3 Regulatory Risk Agent
│   │   │   ├── audit_explanation_agent.py # Stage 4 Audit Explanation Agent
│   │   │   ├── analyst_agent.py       # Stage 5 Decision Support Agent
│   │   │   ├── case_lifecycle_agent.py# Case disposition service
│   │   │   ├── mock_apis.py           # Mock agency APIs
│   │   │   └── ollama_service.py      # Ollama / Qwen HTTP client
│   │   └── utils/
│   │       └── id_generator.py        # Unique ID generator
│   ├── alembic/                       # Database migration scripts
│   ├── simulator/
│   │   └── simulator.py               # Transaction stream generator
│   ├── tests/                         # 37 comprehensive test suites
│   ├── main.py                        # FastAPI entry point & WebSocket server
│   └── requirements.txt               # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/                # Reusable UI components
│   │   │   ├── ActionButton.jsx
│   │   │   ├── ActionTakenToast.jsx
│   │   │   ├── AnalystEvidenceViewer.jsx
│   │   │   ├── AttackModeToggle.jsx
│   │   │   ├── AutomateModeToggle.jsx
│   │   │   ├── CaseCard.jsx
│   │   │   ├── CenterFlow.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── FactorBreakdown.jsx
│   │   │   ├── GoldenTimer.jsx
│   │   │   ├── InvestigationSidebar.jsx
│   │   │   ├── InvestigationWorkflowGraph.jsx
│   │   │   ├── LiveAlertToast.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── RiskBadge.jsx
│   │   │   ├── RiskScoreTrend.jsx
│   │   │   └── SystemStatusBar.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js        # Global WebSocket & polling store
│   │   ├── modules/
│   │   │   └── GraphModule/           # Cytoscape graph visualization module
│   │   ├── pages/
│   │   │   ├── Feed.jsx               # Real-time transaction feed
│   │   │   ├── Dashboard.jsx          # Analytics & Telemetry dashboard
│   │   │   ├── Cases.jsx              # Case workbench & investigation stages
│   │   │   └── Graph.jsx              # Interactive graph workstation
│   │   ├── services/
│   │   │   └── exportAuditLog.js      # Frontend audit export trigger
│   │   ├── roleStore.js               # Simple role state management
│   │   ├── App.jsx                    # Navigation & layout router
│   │   ├── main.jsx                   # React entry point
│   │   └── index.css                  # Global Tailwind CSS styles
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 📦 Dependencies & Requirements

### Required Runtimes
- **Python**: `3.10+` (Tested on Python 3.13.13)
- **Node.js**: `16+` (Tested on Node.js v24.16.0)
- **npm**: `8+` (Tested on npm 11.13.0)

### Backend Dependencies (`requirements.txt`)
- `fastapi` (Web framework)
- `uvicorn` (ASGI server)
- `pydantic` (Data validation)
- `websockets` (WebSocket protocol support)
- `sqlalchemy>=2.0.0` (Async ORM)
- `asyncpg>=0.28.0` (Async PostgreSQL driver)
- `psycopg2-binary>=2.9.0` (PostgreSQL driver)
- `alembic>=1.12.0` (Database migrations)
- `requests` (Simulator HTTP requests)

### Frontend Dependencies (`package.json`)
- `react` & `react-dom` (`^18.2.0`)
- `react-router-dom` (`^6.22.2`)
- `vite` (`^5.1.4`)
- `tailwindcss` (`^3.4.1`)
- `cytoscape` (`^3.28.1`) & `cytoscape-dagre` (`^4.0.1`)
- `recharts` (`^2.12.2`)
- `lucide-react` (`^0.344.0`)
- `clsx` & `tailwind-merge`

---

## ⚙️ Environment Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SENTINEL_MODE` | `development` | Operating mode (`development` uses in-memory store; `production` requires PostgreSQL) |
| `DATABASE_URL` | *None* | PostgreSQL connection string (e.g. `postgresql+asyncpg://user:pass@localhost:5432/sentinel`) |
| `CORS_ORIGINS` | *Localhost defaults* | Comma-separated list of allowed CORS origins |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL for local Ollama service |
| `OLLAMA_MODEL` | `qwen3:8b` | Model name for advisory Qwen intelligence |
| `OLLAMA_TIMEOUT` | `60` | Request timeout in seconds for Ollama API calls |
| `SENTINEL_STALE_RUN_THRESHOLD_SECONDS` | `600` | Stale investigation run recovery threshold |

---

## 🔧 Local Installation & Setup

### 1. Repository Setup
```bash
git clone https://github.com/adityahadagalle/sentinel-fincrime-platform.git
cd sentinel-fincrime-platform/sentinel
```

### 2. Backend Environment Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd ../frontend

# Install Node modules
npm install
```

---

## 🏃 Local Run Instructions

To run SENTINEL locally, start the components in separate terminal windows:

### Terminal 1: Backend FastAPI Server
```bash
cd sentinel/backend
# Activate virtual environment if not active
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # macOS/Linux

python main.py
```
*Backend will start on **http://localhost:8000** (Swagger API Docs at **http://localhost:8000/docs**).*

### Terminal 2: Frontend React Application
```bash
cd sentinel/frontend
npm run dev
```
*Frontend will start on **http://localhost:5173**.*

### Terminal 3: (Optional) Transaction Simulator
```bash
cd sentinel/backend
# Activate virtual environment if not active
.\venv\Scripts\Activate.ps1  # Windows

python simulator/simulator.py
```
*Pumps simulated multi-scenario transactions into the backend at 6 tx/min.*

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Application & database health check |
| `POST` | `/transaction` | Ingest and score a new transaction |
| `GET` | `/cases` | Retrieve all investigation cases |
| `GET` | `/cases/{case_id}` | Retrieve specific case details & payload |
| `GET` | `/cases/{case_id}/graph` | Fetch Cytoscape graph structure for a case |
| `POST` | `/cases/{case_id}/investigate` | Trigger/re-run 5-stage investigation pipeline |
| `GET` | `/cases/{case_id}/investigation` | Get comprehensive investigation read model |
| `POST` | `/cases/{case_id}/disposition` | Submit analyst disposition (state transition) |
| `GET` | `/cases/{case_id}/history` | Fetch complete case disposition & audit history |
| `POST` | `/action/freeze` | Execute operator-authorized account freeze |
| `GET` | `/automation-mode` | Get current Automate Mode status |
| `POST` | `/automation-mode` | Enable/disable Automate Mode |
| `POST` | `/attack-mode` | Trigger 5-hop attack chain simulation |
| `POST` | `/simulate/multi_hop_scenario/{id}` | Trigger multi-hop scenarios (Scenarios 1–6) |
| `GET` | `/analytics/overview` | Fetch comprehensive analytics & telemetry KPIs |
| `GET` | `/export/sentinel_audit.csv` | Download complete 16-field CSV audit log |
| `GET` | `/intelligence/health` | Check local Ollama reachability |
| `POST` | `/intelligence/analyze` | Request Qwen 3 advisory case analysis |

---

## ⚡ WebSocket Event Reference

Connect to `ws://localhost:8000/ws`.

| Event Name | Description |
| :--- | :--- |
| `connected` | Initial connection confirmation (`status: "LIVE"`) |
| `tx_scored` | Emitted whenever a transaction is scored |
| `case_updated` | Emitted whenever a case payload or status updates |
| `transaction.action` | Emitted when an action is evaluated or executed |
| `automation.action.executed` | Emitted on successful autonomous action execution |
| `automation.action.requires_operator` | Emitted when FREEZE requires human approval |
| `automation.mode.changed` | Emitted when Automate Mode is toggled ON/OFF |

---

## 🧪 Testing & Quality Assurance

SENTINEL includes 37 automated test suites under `sentinel/backend/tests/`.

### Running Tests

```bash
cd sentinel/backend
.\venv\Scripts\python.exe -m unittest discover -s tests
```

### Test Coverage Highlights

- `test_phase16_autonomous_engine.py`: Validates deterministic policy rules & fail-closed safety.
- `test_investigation_orchestrator.py`: Validates 5-stage pipeline ordering & stage persistence.
- `test_investigation_confidence.py`: Validates deterministic Investigation Confidence calculation.
- `test_cases_ws_csv_pg.py`: Validates CSV export field structure, formula injection escaping, and UTF-8 BOM.
- `test_ollama_intelligence.py`: Validates Qwen advisory data boundaries and error handling.
- `test_postgres_integration.py`: Validates database repository operations and Alembic schema alignment.

---

## 📝 Development Notes

- **Zero DB Setup by Default**: In development mode, SENTINEL defaults to in-memory storage (`data_store.py`). No PostgreSQL database server is required to run the full application locally.
- **Hot Module Replacement**: Vite automatically reloads frontend changes instantly during development.
- **StatReload**: Uvicorn automatically reloads backend Python changes on save.

---

## 🔐 Security & Governance Boundaries

1. **Non-Autonomous Freezes**: FREEZE actions are strictly gated behind human operator approval.
2. **Deterministic Precedence**: AI recommendations from Qwen can **never** override policy decisions or execute code.
3. **Data Sanitization**: Prompt contexts sent to Ollama are stripped of passwords, tokens, API keys, and environment variables.
4. **CSV Injection Protection**: All string fields in CSV audit exports starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are escaped with `'`.

---

## ⚠️ Current Limitations

- **Simulated Financial APIs**: Actions against banks, telecom providers, and law enforcement are simulated via local state changes (`mock_apis.py`).
- **Rule-Guided ML Emulator**: Default ML scoring uses a correlated statistical emulator rather than a trained binary classifier pickle file.
- **Local Ollama Dependency**: Qwen intelligence requires a local installation of Ollama running `qwen3:8b`. (If missing, the UI gracefully indicates advisory AI is unavailable).

---

## 🔮 Future Extension Areas

- **Live Bank Core Integrations**: Connect mock API handlers to real ISO 20022 / Open Banking APIs.
- **Production ML Model Deployment**: Integrate ONNX Runtime or XGBoost model serving into `ml_risk_engine.py`.
- **Advanced Graph Algorithms**: Implement Louvain community detection and PageRank centrality directly in `graph_engine.py`.
- **Multi-Tenant Authorization**: Expand `roleStore.js` into JWT-based OAuth2 / OIDC role-based access control.

---

*SENTINEL FinCrime Platform — Real-Time Detection, Autonomous Investigation, Strict Governance.*
