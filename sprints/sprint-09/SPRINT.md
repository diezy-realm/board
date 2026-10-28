---
id: sprint-09
type: sprint
goal: Keputusan Rust-only tertulis di repo, steering agent berhenti mengarahkan ke Go, celah terminal Go ditutup sementara, dan guard CI melarang file Go baru
category: Governance
status: active
start: 2026-10-29
end: 2026-10-31
author: kirocrew
---
# Sprint 09 — Governance Rust-only & Kontainmen Go

> **Sprint Goal:** Keputusan Rust-only tertulis di repo, steering agent berhenti mengarahkan ke Go, celah terminal Go ditutup sementara, dan guard CI melarang file Go baru.

> **Diaktifkan 2026-10-29 oleh Owner.** Checklist `RULES-amendment-2026-10-29.md` §A3: (1) sprint-08 `closed` dan 48 dari 48 task `done`; (2) PRD-002 `approved` (Owner), SPEC-011 `approved` (Lead); (3) default Q1–Q9 diterima Owner, Q7 (`target_release`) belum diisi dan tidak memblokir sprint ini; (4) `python3 validate.py --all` = ALL VALID sebelum dan sesudah aktivasi; (5) `start`/`end` terisi.

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
0. **Hotfix build (disisipkan 2026-10-29, jalur terpisah dari rantai governance):**
   - **TASK-049 (todo, agy):** Selektor `-p zerocode`->`galleoncode` di Dockerfile*, Containerfile, PKGBUILD
   - **TASK-050 (blocked, agy):** Selektor yang sama di workflow rilis, test xtask, setup.bat, script dev — menunggu PR TASK-049 merged
   Alasan: package `zerocode`/`zerorelay` tidak ada lagi sejak #92/#93, sehingga build image dan rilis gagal (SPEC-011 §H). Tidak bergantung pada TASK-051..057.
1. **TASK-051 (done, kirocrew):** Audit baseline fakta Go/Rust pada testing@3f3a729
2. **TASK-052 (todo, agy):** Commit dokumen keputusan Rust-only + banner Superseded
3. **TASK-053 (blocked, agy):** Steering .github: hapus instruksi Go — menunggu PR TASK-052 merged
4. **TASK-054 (blocked, agy):** Steering .gemini/.kiro/AGENTS.md: hapus instruksi Go — menunggu PR TASK-053 merged
5. **TASK-055 (blocked, agy):** Kontainmen Go: bind 127.0.0.1 + Bearer fail-closed pada eksekusi terminal — menunggu PR TASK-054 merged
6. **TASK-056 (blocked, agy):** Guard CI scripts/ci/check_no_go.sh (mode diff/full) — menunggu PR TASK-055 merged
7. **TASK-057 (todo, kirocrew):** Terapkan RULES/TEMPLATES amendment ke board

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-049, TASK-050, TASK-051 s.d. TASK-057) berstatus `done` dengan Report (`reports/RPT-xxx.md`) berisi output perintah verifikasi apa adanya.
- [ ] DoD `BL-086` terpenuhi.
- [ ] Tidak ada file Go baru (`scripts/ci/check_no_go.sh diff`, mulai Sprint 09).
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate hijau.

## Langkah Lead
- TASK-057 berassignee `kirocrew`; bridge tidak mengambilnya. Sprint ini baru tertutup otomatis bila TASK-057 `done` (RULES amandemen A7).
- TASK-052 dikerjakan Lead lewat PR `feat/docs-rust-only-governance-docs` (instruksi banner dikoreksi); statusnya `review` dan ditutup oleh `board_switch.py review` saat PR merged.

## Langkah Owner
- Tambahkan `bash scripts/ci/check_no_go.sh diff` ke `~/Apps/dev-ci/repos/galleon-fleet/gates.sh` setelah TASK-056 merged.
- Sebelum mengaktifkan sprint ini: tandai `done`/tutup sprint-04..08 yang masih terbuka (lihat RPT-108 §Masalah Terbuka); `sprint-manager.py close NN` meng-carry-over task belum selesai ke sprint berikutnya.

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-011.md`
- Backlog Item: `product-backlog/backlog/BL-086.md`
- User Story: `product-backlog/stories/US-009.md`
- PRD: `product-backlog/prd/PRD-002.md`
- Keputusan: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018
- Riset: `research/RES-2026-10-29-rust-single-language-baseline.md`, `research/RES-2026-10-29-rust-engineering-standards.md`
