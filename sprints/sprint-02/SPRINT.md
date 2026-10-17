---
id: sprint-02
type: sprint
goal: Tuntaskan dekoplasi crate Rust yang tersisa (T3-02 gateway lepas runtime, T3-03 channel split) lalu buka jalan Sprint-8 rename massal
category: refactoring
status: active
start: 2026-10-17
end:
author: kirocrew
---
# Sprint 02 — Dev Task 3 (konsolidasi task aktif, lanjutan)

> **Sprint Goal:** Tuntaskan dua tiket in-progress jantung Sprint-4 — **T3-02** (`clawcrew-gateway` lepas penuh dari `clawcrew-runtime`) dan **T3-03** (pecah `clawcrew-channels` monolith jadi crate `galleon-channel-*` per channel) — karena ~11 tiket Sprint-8 (rename massal `clawcrew-*`→`galleon-*`) **hard-depend** ke keduanya dan tidak boleh mulai sebelum selesai.

## SSOT & sumber

Sprint ini adalah kelanjutan **Dev Task 3** yang sebelumnya hidup di
`standard-docs/decisions/finalize/dev-task-3/`. Dokumen sumber lengkap dibawa ke
`reference/` di sprint ini:

- `reference/dev-task-3/README.md` — konsolidasi 31 tiket (T3-01..T3-28) + status implementasi per tiket + peta dependency.
- `reference/dev-task-2-RULES.md` — 8 aturan kerja (lahir dari insiden dev-task-2) yang **masih mengikat** kerja sprint ini.
- `../../archive/dev-task-2/` — lapisan rekonsiliasi (9 sprint, DoD, finding, ci-infra-fix) yang **sudah diserap** dev-task-3 dan sprint-nya **sudah selesai**. Diarsipkan sebagai jejak sumber; **jangan audit ulang** sebagai sumber independen (lihat `reference/dev-task-3/README.md §Asumsi`).

Mulai 2026-10-17, **board/ adalah SSOT kerja aktif** untuk task-task ini. Lihat
`reference/ONBOARDING-agy.md` untuk cara agy mengerjakannya.

## Status tiket (ringkas — detail di `reference/dev-task-3/README.md`)

**Aktif / in-progress (ada TASK di `tasks/`):**
- **T3-02** (BR-C5) — `gateway` lepas `runtime`. Masih ada ratusan ref `clawcrew_runtime::` di gateway. `tasks/TASK-001.json`.
- **T3-03** (BR-C6) — pecah `channels` per-channel. Sebagian channel sudah diekstrak; sisa channel masih di monolith. `tasks/TASK-002.json`.

**Blocked (menunggu T3-02/T3-05 selesai — belum dibuat TASK supaya tidak dijalankan prematur):**
- T3-04 (BR-C7) depend T3-02 · T3-05 (BR-D1) · T3-06 (BR-D2) · T3-08 (BR-D4) depend T3-02
- T3-11 (BL-17) depend T3-10 + butuh keputusan desain
- Sprint-8 rename: T3-14..T3-24 (11 tiket) — **tidak boleh mulai sebelum T3-02/05 tuntas**

**Sudah selesai (Terpenuhi — tidak dijadwalkan ulang):** T3-01, T3-02b, T3-07, T3-09, T3-10, T3-12, T3-13, T3-25, T3-26, T3-27, T3-28.

> Aturan tutup & carry-over: lihat `../../RULES.md`.
