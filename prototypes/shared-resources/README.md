# Shared Resource Library — Prototype v3

A self-contained browser prototype for reviewing how Resource Scout shared records appear alongside existing office resources.

## Run

Open [index.html](index.html) in Safari or another modern browser. No server, build step, dependency installation, API key, or production system is required.

## Demonstrate shared changes

1. Select **Provo** and open **Addiction** in the Missionary view.
2. Switch to **Admin → Vetter**; select the **SAMHSA National Helpline** shared record.
3. Change its description and/or demo vetting status and save.
4. Select **Mesa** and return to Missionary → Addiction. The same shared record appears with the updated details.

The two office views read a **single canonical shared object inside this HTML application**, not two independently edited office copies. Changes are stored in this browser's localStorage and are **not synchronized across browsers, devices, independently deployed TSO office files, or Scout production**. Multi-device synchronization and permissioned publication would require a shared data service.

## Prototype data

- **Provo:** Office-maintained records adapted from `michaelbendio/wsrs-tso`, `source-data/provo-resource-package/tso-resources.json`. This is a compact demonstration copy, not a complete round-trip representation of original fields.
- **Mesa:** Research candidates adapted from `michaelbendio/resource-scout`, `deliveries/mesa-four-categories-20260925/prepared-resources.json`. It is a **partial September 2026 research snapshot**, not the current accepted/vetted operational Mesa resource list. Some recovery-related Housing candidates are also shown under Addiction for demonstration.
- **Shared:** Illustrative nationwide/federal, state, county, and city resources with geography-based visibility. Geographic visibility does not establish individual service eligibility.
- **PDFs:** PDF attachments, embedded PDF bytes, and direct PDF links are omitted. Records that consist only of PDF material are excluded.

Program names and public source links are included for prototyping only. Eligibility, services, contact details, opening hours, and referral pathways require fresh human verification before a real referral. The demo's verification statuses are not production approval.

## Scope and safety

Standalone design prototype only. No database writeback, automatic import into office packages, production vetting, or remote sharing service. Keep future edits and exploratory tests on this branch until separately reviewed.
