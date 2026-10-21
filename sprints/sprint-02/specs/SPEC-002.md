---
id: SPEC-002
type: spec
spec_kind: tech
title: Pemecahan File Monolitik Gateway api.rs (T3-04 / BR-C7)
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
File `crates/clawcrew-gateway/src/api.rs` memiliki ukuran 6.153 baris kode, melanggar batas arsitektur T3-04 (>2000 baris). Audit kode 2026-10-22 membuktikan:
- Baris 1 s/d 2.249 (2.249 baris) adalah endpoint handlers produksi Axum.
- Baris 2.250 s/d 6.153 (3.904 baris / ~63% file) adalah unit test internal (`pub(crate) mod tests`).

Ukuran monolitik ini mempersulit review, memperlambat navigasi compiler, dan rawan memicu merge conflict.

## Solusi yang Diusulkan (Proposed Solution)
Penerapan pola SAFE RF-A (file-split dalam satu crate, mempertahankan path dan visibilitas fungsi, zero external API change):
1. **Fase 1 (TASK-022):** Ekstraksi unit test internal `pub(crate) mod tests` (3.904 baris) ke `crates/clawcrew-gateway/src/api/tests.rs` (atau `crates/clawcrew-gateway/src/api_tests.rs`). File produksi `api.rs` langsung berkurang menjadi ~2.249 baris.
2. **Fase 2 (TASK-023):** Ekstraksi handler cron (`handle_api_cron_*`) dan session (`handle_api_session_*`) ke modul terpisah `crates/clawcrew-gateway/src/api/cron.rs` dan `crates/clawcrew-gateway/src/api/sessions.rs`.
3. **Fase 3 (TASK-024):** Ekstraksi handler channel, memory, dan integrations ke submodul terkait. `crates/clawcrew-gateway/src/api.rs` (atau `api/mod.rs`) menjadi router/re-exporter ramping (<300 baris).

## Model Data (Data Model)
Tidak ada perubahan pada schema data, DTO, atau state gateway. Semua signature fungsi `pub async fn handle_api_*` tetap identik dan di-re-export secara transparan ke router di `crates/clawcrew-gateway/src/lib.rs`.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- **Ekstraksi sekaligus dalam 1 PR besar:** Ditolak karena menyentuh ribuan baris kode sekaligus dan melanggar aturan 1 PR = 1 Concern (Rule 7).
- **Membiarkan test di dalam file produksi:** Ditolak karena melanggar DoD T3-04 (file produksi >2000 baris).

## Pertimbangan Keamanan (Security Considerations)
- Tidak ada perubahan otorisasi, sanitasi input, atau trust boundary.
- Seluruh verifikasi session key dan header token tetap dipertahankan.

## Rencana Pengujian (Testing Plan)
- `cargo check -p clawcrew-gateway` (wajib 0 error).
- `cargo test -p clawcrew-gateway` (seluruh 444 tests wajib pass).
- CI gate dev-ci (`local/Required Gate`) wajib hijau di PR.

## Rollout / Migrasi
Dijalankan secara sekuensial (chaining): TASK-022 (`todo`) -> TASK-023 (`blocked` until 022 merged) -> TASK-024 (`blocked` until 023 merged).
