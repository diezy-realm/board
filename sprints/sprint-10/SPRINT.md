---
id: sprint-10
type: sprint
goal: Router gateway Rust memulihkan rute berkonsumen (admin, pairing, webhook), layer keamanan, test tabel rute, dan fixture kontrak dari Go direkam sebelum Go dihapus
category: Hardening
status: planning
start:
end:
author: kirocrew
---
# Sprint 10 — Pemulihan Router Gateway & Kontrak

> **Sprint Goal:** Router gateway Rust memulihkan rute berkonsumen (admin, pairing, webhook), layer keamanan, test tabel rute, dan fixture kontrak dari Go direkam sebelum Go dihapus.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-058 (todo, agy):** Inventaris konsumen API (consumer-inventory.md) — menunggu PR TASK-056 merged
2. **TASK-059 (blocked, agy):** Gateway: body limit, timeout, security headers, ConnectInfo — menunggu PR TASK-058 merged
3. **TASK-060 (blocked, agy):** Gateway: pulihkan rute pairing — menunggu PR TASK-059 merged
4. **TASK-061 (blocked, agy):** Gateway: pulihkan rute admin (localhost-only) — menunggu PR TASK-060 merged
5. **TASK-062 (blocked, agy):** Gateway: rute channel opsional + webhook SOP — menunggu PR TASK-061 merged
6. **TASK-063 (blocked, agy):** Gateway: aktifkan kembali test yatim src/tests.rs — menunggu PR TASK-062 merged
7. **TASK-064 (blocked, agy):** Gateway: test tabel rute (insta + matriks 401) — menunggu PR TASK-063 merged
8. **TASK-065 (blocked, agy):** Rekam fixture kontrak dari Go (tanpa file Go baru) — menunggu PR TASK-064 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-058 s.d. TASK-065) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-087` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Bila toolchain Go tidak ada di mesin agent, jalankan `scripts/contract/record_go_fixtures.sh` di mesin lokal (TASK-065).

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-012.md`
- Backlog Item: `product-backlog/backlog/BL-087.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
