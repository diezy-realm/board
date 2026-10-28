---
id: sprint-15
type: sprint
goal: Wiring serve gateway yang hilang (TLS/mTLS, public-bind, path_prefix, tunnel) dipulihkan dan tunnel diekstrak ke crate galleon-tunnel
category: Hardening
status: planning
start:
end:
author: kirocrew
---
# Sprint 15 — Wiring Serve Gateway & Ekstraksi galleon-tunnel

> **Sprint Goal:** Wiring serve gateway yang hilang (TLS/mTLS, public-bind, path_prefix, tunnel) dipulihkan dan tunnel diekstrak ke crate galleon-tunnel.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-102 (todo, agy):** Gateway: pulihkan TLS/mTLS listener + peringatan public bind — menunggu PR TASK-059 merged
2. **TASK-103 (blocked, agy):** Gateway: pulihkan path_prefix — menunggu PR TASK-102 merged
3. **TASK-104 (blocked, agy):** Gateway: pulihkan start tunnel — menunggu PR TASK-103 merged
4. **TASK-105 (blocked, agy):** Ekstraksi crates/galleon-tunnel + aturan dependency_direction — menunggu PR TASK-104 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-102 s.d. TASK-105) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-092` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Jawab Q8 dan Q9 PRD-002. Sprint ini hanya bergantung pada TASK-059 (Sprint 10). RULES §7 hanya mengizinkan satu sprint aktif; bila TLS ingin lebih cepat, Owner boleh mengaktifkan Sprint 15 setelah Sprint 10 selesai, tetapi TIDAK otomatis (sprint-11 harus di-`hold` dulu; prosedur di RULES amandemen A4) (pengecualian urutan, dicatat di `notes` SPRINT.md sesuai RULES amendment §A4). Bila dikerjakan sebelum Sprint 14, TASK-096 perlu rebase.

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-017.md`
- Backlog Item: `product-backlog/backlog/BL-092.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
