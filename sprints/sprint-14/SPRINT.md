---
id: sprint-14
type: sprint
goal: Lint workspace diwarisi semua crate dengan ratchet, doctest berjalan, sccache kondisional, drift nama ClawCrew dibersihkan, Sonar Rust kondisional
category: Hygiene
status: planning
start:
end:
author: kirocrew
---
# Sprint 14 — Higiene Rust & Tooling

> **Sprint Goal:** Lint workspace diwarisi semua crate dengan ratchet, doctest berjalan, sccache kondisional, drift nama ClawCrew dibersihkan, Sonar Rust kondisional.

> **Status `planning`:** sprint ini disiapkan lebih awal dan **tidak dijalankan bridge** sampai Owner mengubahnya menjadi `active` (prosedur aktivasi: `RULES-amendment-2026-10-29.md` §A3).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-093 (todo, agy):** Fondasi lint: clippy.toml + pasang check_production_unwrap — menunggu PR TASK-092 merged
2. **TASK-094 (blocked, agy):** Lint batch A: crate kecil mewarisi [lints] workspace — menunggu PR TASK-093 merged
3. **TASK-095 (blocked, agy):** Lint batch B: crate menengah — menunggu PR TASK-094 merged
4. **TASK-096 (blocked, agy):** Lint batch C: crate besar + root — menunggu PR TASK-095 merged
5. **TASK-097 (blocked, agy):** Lane doctest + komentar nextest — menunggu PR TASK-096 merged
6. **TASK-098 (blocked, agy):** sccache kondisional + CARGO_INCREMENTAL=0 — menunggu PR TASK-097 merged
7. **TASK-099 (blocked, agy):** Drift nama: --exclude clawcrew-desktop, homepage, brand gate — menunggu PR TASK-098 merged
8. **TASK-100 (blocked, agy):** Sonar Rust kondisional (default Q4) — menunggu PR TASK-099 merged
9. **TASK-101 (blocked, agy):** Terapkan rust-conventions amendment — menunggu PR TASK-100 merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-093 s.d. TASK-101) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-091` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Owner
- Jawab Q4 (Sonar) dan URL `homepage` (TASK-099).
- Tambahkan `check_production_unwrap.py` dan `brand_gate.sh` ke `gates.sh` setelah TASK-093/TASK-099.

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-016.md`
- Backlog Item: `product-backlog/backlog/BL-091.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
