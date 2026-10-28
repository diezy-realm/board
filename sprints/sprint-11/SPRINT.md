---
id: sprint-11
type: sprint
goal: Semua endpoint dashboard berkonsumen dilayani crate galleon-fleet-core di gateway Rust dengan bentuk JSON sama dan nilai jujur
category: Migration
status: planning
start:
end:
author: kirocrew
---
# Sprint 11 — Port Fleet API ke galleon-fleet-core

> **Sprint Goal:** Semua endpoint dashboard berkonsumen dilayani crate galleon-fleet-core di gateway Rust dengan bentuk JSON sama dan nilai jujur.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-066 (todo, agy):** Scaffold crate galleon-fleet-core — menunggu PR TASK-065 merged
2. **TASK-067 (blocked, agy):** FleetStore: penyimpanan atomik + data dir + impor sekali — menunggu PR TASK-066 merged
3. **TASK-068 (blocked, agy):** Koleksi: allowlist 15 nama camelCase + policies/riskTiers — menunggu PR TASK-067 merged
4. **TASK-069 (blocked, agy):** Snapshot nyata (default Q2) — menunggu PR TASK-068 merged
5. **TASK-070 (blocked, agy):** Seed dari engine/data (default Q6) + hapus extract-seed.mjs — menunggu PR TASK-069 merged
6. **TASK-071 (blocked, agy):** Metrik fleet + deck-bell — menunggu PR TASK-070 merged
7. **TASK-072 (blocked, agy):** Policies + perbaiki scan root no_duplicate_risk_tier — menunggu PR TASK-071 merged
8. **TASK-073 (blocked, agy):** System metrics, network, processes — menunggu PR TASK-072 merged
9. **TASK-074 (blocked, agy):** QR code (SVG) + executive briefing — menunggu PR TASK-073 merged
10. **TASK-075 (blocked, agy):** Git status proyek — menunggu PR TASK-074 merged
11. **TASK-076 (blocked, agy):** Harbor providers — menunggu PR TASK-075 merged
12. **TASK-077 (blocked, agy):** Diagnostics dari doctor::diagnose — menunggu PR TASK-076 merged
13. **TASK-078 (blocked, agy):** Terminal exec: auth -> SecurityPolicy -> approval -> audit — menunggu PR TASK-077 merged
14. **TASK-079 (blocked, agy):** Quartermaster: klasifikasi intent + balasan deterministik — menunggu PR TASK-078 merged
15. **TASK-080 (blocked, agy):** Quartermaster: jalur agent Rust (default Q3) — menunggu PR TASK-079 merged
16. **TASK-081 (blocked, agy):** Mount router fleet + test bentuk kontrak — menunggu PR TASK-080 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-066 s.d. TASK-081) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-088` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Jawab Q1, Q2, Q3, Q6 PRD-002 sebelum aktivasi (default dipakai bila tidak).

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-013.md`
- Backlog Item: `product-backlog/backlog/BL-088.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
