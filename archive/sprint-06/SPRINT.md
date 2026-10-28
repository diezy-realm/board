---
id: sprint-06
type: sprint
goal: Retargeting test harness eval & cross-runtime replay ke Go surface (T3-06 / BR-D2) dan finalisasi pembuangan legacy RPC (T3-08)
category: Testing
status: closed
start: 2026-10-27
end: 2026-10-27
author: kirocrew
---
# Sprint 06 — Retargeting Test Harness & Deprecate Legacy RPC (T3-06, T3-08)

> **Sprint Goal:** Mengarahkan ulang (*retarget*) evaluasi test suite `clawcrew-eval` agar dapat mereplay fixture LLM trace langsung ke interface engine Go (`StartTurn` / `ExecuteTurn`) pasca-strangler T3-05 tanpa mengubah trace data fixtures, serta membersihkan sisa callers legacy RPC subsistem (T3-08).

## Cakupan Utama & Rencana Tiket (Dev Task 3)
1. **T3-06 (BR-D2):** Retargeting harness `clawcrew-eval` untuk replay fixture LLM trace ke jalur Go engine.
2. **T3-08 (BR-D4):** Audit dan pembersihan final seluruh caller yang merujuk pada legacy RPC runtime yang telah usang.

## Dependensi & Prasyarat
- **Prasyarat:** Sprint 05 (Ramping Runtime T3-05) harus berstatus `done` dan terverifikasi hijau 100%.
- **Memblokir:** Sprint 07 dan Sprint 08.
