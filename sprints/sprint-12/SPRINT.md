---
id: sprint-12
type: sprint
goal: Web, Desktop (Tauri), dan Nginx memakai gateway Rust dengan alur pairing dan satu pintu request ber-Bearer; smoke E2E tanpa proses Go
category: Migration
status: planning
start:
end:
author: kirocrew
---
# Sprint 12 — Klien Web, Tauri, Nginx ke Gateway Rust

> **Sprint Goal:** Web, Desktop (Tauri), dan Nginx memakai gateway Rust dengan alur pairing dan satu pintu request ber-Bearer; smoke E2E tanpa proses Go.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-082 (todo, agy):** Web: satu pintu request() ber-Bearer + proxy Vite ke gateway Rust — menunggu PR TASK-081 merged
2. **TASK-083 (blocked, agy):** Web: layar pairing (PairingGate) — menunggu PR TASK-082 merged
3. **TASK-084 (blocked, agy):** Web: devices, sembunyikan learning/remedy, tipe null — menunggu PR TASK-083 merged
4. **TASK-085 (blocked, agy):** Tauri: satu command api_request + CSP — menunggu PR TASK-084 merged
5. **TASK-086 (blocked, agy):** Nginx: upstream ke gateway Rust — menunggu PR TASK-085 merged
6. **TASK-087 (blocked, agy):** Smoke E2E dashboard tanpa Go — menunggu PR TASK-086 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-082 s.d. TASK-087) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-089` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Jawab Q5 PRD-002 sebelum aktivasi.

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-014.md`
- Backlog Item: `product-backlog/backlog/BL-089.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
