---
id: sprint-13
type: sprint
goal: Go, proto, strangler, dan gRPC SystemGateway dihapus dari repo; CI melarang Go secara penuh
category: Decommission
status: planning
start:
end:
author: kirocrew
---
# Sprint 13 — Penghapusan Go & gRPC

> **Sprint Goal:** Go, proto, strangler, dan gRPC SystemGateway dihapus dari repo; CI melarang Go secara penuh.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-088 (todo, agy):** Hapus strangler, gRPC SystemGateway, build.rs, tonic/prost gateway — menunggu PR TASK-087 merged
2. **TASK-089 (blocked, agy):** Hapus proto/ + [engine] galleoncode + rename GoTurnRequest — menunggu PR TASK-088 merged
3. **TASK-090 (blocked, agy):** git rm engine/, go.work, web/data — menunggu PR TASK-089 merged
4. **TASK-091 (blocked, agy):** CI: hapus engine-ci, deteksi Go, guard full, test tier 3-lapis — menunggu PR TASK-090 merged
5. **TASK-092 (blocked, agy):** Dokumen: banner/arsip dokumen Go — menunggu PR TASK-091 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-088 s.d. TASK-092) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-090` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Setelah TASK-091: ganti `check_no_go.sh diff` menjadi `full` di `gates.sh`.
- Catat SHA terakhir yang memuat Go (RPT TASK-090).

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-015.md`
- Backlog Item: `product-backlog/backlog/BL-090.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
