---
id: sprint-05
type: sprint
goal: Ramping runtime per modul via strangler pattern (T3-05 / BR-D1) untuk memindahkan domain logic ke Go engine dan menyusutkan clawcrew-runtime
category: Refactoring
status: closed
start: 2026-10-27
end: 2026-10-27
author: kirocrew
---
# Sprint 05 — Ramping Runtime & Strangler Pattern (T3-05 / BR-D1)

> **Sprint Goal:** Melakukan penyusutan modular pada `clawcrew-runtime` menggunakan pola strangler pattern (T3-05 / BR-D1). Mengisolasi domain logic eksekusi turn, session loop, dan memory orchestration ke engine Go (`engine/`), menyisakan runtime Rust sebagai layer adapter yang ramping dan ringan.

## Cakupan Utama & Rencana Tiket (Dev Task 3)
1. **T3-05a (Strangler Layer):** Pembuatan interface boundary antara gateway dan orchestrator Go.
2. **T3-05b (Agent Turn Slimming):** Refactoring `clawcrew-runtime/src/agent/turn/` untuk mendelegasikan eksekusi turn ke engine Go.
3. **T3-05c (Module Decoupling):** Pembersihan modul runtime yang sudah tidak terpakai pasca-migrasi.
4. **T3-05d (Terminal Outcome Hardening):** Perbaiki `strangler_runner.rs` agar EOF stream prematur (tanpa event `TurnCompleted`) tidak lagi dilaporkan sebagai sukses palsu (audit kode 2026-10-27, lihat SPEC-010).
5. **T3-05e (Context Propagation):** Tentukan owner history (Rust vs Go session store) dan propagasikan `context_window` strangler yang saat ini selalu kosong, atau dokumentasikan kosong-by-design (audit kode 2026-10-27, lihat SPEC-010).

## Dependensi & Prasyarat
- **Prasyarat:** Sprint 04 (Hardening & E2E Testing) harus berstatus `done` dan terverifikasi hijau 100%.
- **Memblokir:** Sprint 06 (Retargeting Eval Harness) dan Sprint 08 (Rename Massal).
- **Internal T3-05d/e:** TASK-048 (T3-05e) `blocked` menunggu TASK-047 (T3-05d) selesai & PR merged -- keduanya menyentuh file yang sama (`strangler_runner.rs`), diserialkan agar tidak bertabrakan.
