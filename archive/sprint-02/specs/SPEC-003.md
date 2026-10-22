---
id: SPEC-003
type: spec
spec_kind: tech
title: Penghapusan Modul Legacy RPC runtime/src/rpc dengan Git Archive Tag (T3-08 / BR-D4)
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Modul `crates/clawcrew-runtime/src/rpc/` (34.616 baris kode) merupakan transport socket & WSS daemon lama yang telah digantikan oleh arsitektur gateway baru dan Client Protocol Go (BG-E2). Audit kode 2026-10-22 membuktikan:
- Di luar crate runtime, **satu-satunya pemanggil aktif** adalah `src/main.rs:5371, 5473` (`run_local_listener` dan `run_wss_listener`).
- `apps/zerocode/src/client.rs` hanya menyebut nama tipe di komentar docstring.
- Modul ini membebani durasi kompilasi dan menduplikasi transport layer.

## Solusi yang Diusulkan (Proposed Solution)
Mengikuti pola sukses penghapusan `verifiable_intent` (T3-07):
1. **Fase 1 (TASK-025):** Pembuatan dan push Git Tag anotasi permanen `archive/pre-galleon-rpc` dari commit branch `testing` untuk mengabadikan state 34.6k LOC modul RPC sebelum dihapus.
2. **Fase 2 (TASK-026):** Pelepasan registrasi socket/wss listener di `src/main.rs`, penghapusan folder `crates/clawcrew-runtime/src/rpc/`, pembersihan deklarasi `pub mod rpc;` di `runtime/src/lib.rs`, dan penghapusan integration test lama di `crates/clawcrew-runtime/tests/`.

## Model Data (Data Model)
Tidak ada model data baru. Tipe RPC lama dihilangkan tanpa fallback alias.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- **Menghapus tanpa git tag archive:** Ditolak keras karena melanggar aturan dev-task-3 (harus ada tag archive untuk preservasi historis).
- **Membiarkan kode sebagai dead code:** Ditolak karena menambah 34.6k baris sampah dan memicu peringatan audit.

## Pertimbangan Keamanan (Security Considerations)
- Menghilangkan attack surface listener socket/WSS lokal yang tidak lagi diaudit.
- Seluruh komunikasi klien eksternal kini melalui port gateway yang terotentikasi dan terisolasi.

## Rencana Pengujian (Testing Plan)
- `cargo check --workspace` (0 error).
- `cargo nextest run --workspace --locked` (seluruh test suite lolos).
- Smoke test startup daemon binary.

## Rollout / Migrasi
Dijalankan bertahap: TASK-025 (`todo`, pembuatan tag archive) -> TASK-026 (`blocked`, penghapusan kode pasca-tag).
