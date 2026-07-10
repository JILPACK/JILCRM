# JIL CRM v2.0 — Odoo 18 Module

Enterprise CRM for **JIL Pack** packaging group. Covers the full customer lifecycle:
lead capture → scoring → assignment → nurturing → sales pipeline → booking → project
tracking → invoicing → recovery, plus an AI chatbot and unified context MCP.

## Features

| Domain | Models |
|--------|--------|
| **Lead Management** | Capture forms, scoring rules (NLP/behavior/demographic), assignment rules (round-robin/load/score/hybrid), multi-stage pipeline |
| **Sales** | Deal tracking, sales forecasting, automated follow-ups, quotation-to-invoice flow |
| **AI Chatbot** | Intent matching, conversation flows, session management, analytics |
| **Consultation Booking** | Availability calendar, booking with reminders |
| **Project Tracking** | Milestones, tasks, Gantt-style progress |
| **Workflow Automation** | Trigger-based rules (create/write/stage/score/cron), email sequences, notifications |
| **Dashboards & KPIs** | Configurable dashboards, computed KPIs with period-over-period trend |
| **Context MCP** | Unified customer context across all touchpoints with sync, ingestion, governance, audit |
| **Support / Claims / Transport / Recovery** | Tickets, reclamations, logistics tracking, receivables recovery |
| **BPMN** | Business process modeling with pools, lanes, elements, flows |

## Requirements

- **Odoo 18.0** community (installed at `odoo/` directory)
- **Python 3.12**
- **PostgreSQL 16**
- **Dependencies**: `openpyxl` (for data import)

## Quick Start

```bash
# 1. Install openpyxl (for data import)
pip install openpyxl

# 2. Start server (uses - odoo.conf, NOT the original)
python odoo\odoo-bin server -c "odoo.conf" -d odoo_jil_crm --http-port=8069 --log-level=info -u jil_crm


# 3. Open browser at http://localhost:8069
#    Login: admin / admin
```

**Important**: always use the `- odoo.conf` config — the original `Odoo CRM AI\` directory has a different `addons_path`.

## Data Import

The file `Data.xlsx` contains real business data:
- 1,200+ products (9 categories)
- 933 chart of accounts
- Clients & suppliers
- 251 sales documents, 335 purchase documents
- 443 BOMs, transports

```bash
# Run import via Odoo shell:
python odoo-bin shell -c odoo.conf -d odoo_jil_crm
>>> from scripts.import_data import run
>>> run(env)
```

## Module Structure

```
jil_crm/
├── models/          (25 Python files, one per model)
│   ├── crm_lead.py, crm_stage.py, lead_scoring.py, ...
│   ├── context_mcp_core.py, context_mcp_event.py
│   ├── workflow_automation.py, email_sequence.py, notification_trigger.py
│   ├── claim.py, transport.py, recovery.py, support_ticket.py
│   └── ...
├── views/           (22 XML view files)
├── wizard/          (5 wizard models + views)
├── security/        (75+ ACLs, multi-company record rules)
├── data/            (9 data files: stages, sequences, KPIs, scoring
│                    rules, workflows, chatbot intents, BPMN, cron)
├── report/          (PDF/Excel reporting)
└── scripts/         (data import utility)
```

## Architecture

- **37 models** across 9 business domains
- **19 model files** → restructured into **25 single-model files**
- **75+ ACL entries** with user/manager group separation
- **Multi-company** record rules on leads, claims, transports, recovery, tickets
- Computed KPI values with real period-over-period trend (not fake 0.85x)
- Batch `read_group` replaces N+1 `search_count` patterns
- `ast.literal_eval` replaces `eval()` for domain parsing (security)
- Cron jobs for Chatbot Analytics and Conversion Metrics (daily)
