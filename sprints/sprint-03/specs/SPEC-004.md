---
id: SPEC-004
type: spec
spec_kind: tech
title: Arsitektur Dekomposisi File Raksasa Gateway (SAFE RF-A File-Split)
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Pasca-penyelesaian pemutusan ketergantungan `clawcrew-gateway` terhadap `clawcrew-runtime` (T3-02), codebase gateway masih memiliki 3 file produksi besar dengan ukuran melebihi ambang batas arsitektur 2.000 baris:
1. `crates/clawcrew-gateway/src/api_config.rs` (4.940 LOC)
2. `crates/clawcrew-gateway/src/ws.rs` (4.259 LOC)
3. `crates/clawcrew-gateway/src/api_sections.rs` (2.413 LOC)

File monolitik ini mempersulit pemeliharaan, memperlambat proses diff code-review, dan menggabungkan logika routing, validasi patch, session lifecycle, serta ribuan baris unit test ke dalam satu file tunggal.

## Solusi yang Diusulkan (Proposed Solution)
Mengadopsi pola refactoring **SAFE RF-A (Module Decomposition with Facade Re-export)** tanpa mengubah dependensi crate eksternal, tanpa memodifikasi kontrak rute HTTP/WS Axum, dan tanpa merusak path import caller yang sudah ada:

### 1. Dekomposisi `api_config` (4.940 LOC → `api_config/`)
- `crates/clawcrew-gateway/src/api_config/mod.rs`: Definisi router Axum, DTO publik (`PropQuery`, `ListQuery`, `PropPutBody`, `PatchOp`), re-export seluruh handler publik.
- `crates/clawcrew-gateway/src/api_config/handlers.rs`: Handler per-property CRUD (GET, PUT, DELETE, OPTIONS).
- `crates/clawcrew-gateway/src/api_config/patch.rs`: Logika eksekusi JSON Patch dan atomisitas `persist_and_swap`.
- `crates/clawcrew-gateway/src/api_config/drift.rs`: Logika komputasi pergeseran konfigurasi (`try_compute_drift`, `ConfigDriftSummary`).
- `crates/clawcrew-gateway/src/api_config/tests.rs`: Seluruh unit test suite `mod tests` (dipindahkan bersih dari baris 2626-4940).

### 2. Dekomposisi `ws` (4.259 LOC → `ws/`)
- `crates/clawcrew-gateway/src/ws/mod.rs`: Entry point WebSocket handshake, route handler `ws_handler`, re-export publik.
- `crates/clawcrew-gateway/src/ws/session.rs`: State machine koneksi WS, framing message protocol, heartbeat ping/pong.
- `crates/clawcrew-gateway/src/ws/dispatch.rs`: Dispatcher pesan inbound client request ke internal runner/runtime-adapter.
- `crates/clawcrew-gateway/src/ws/tests.rs`: Seluruh unit test suite `mod tests` (dipindahkan bersih dari baris 2106-4259).

### 3. Dekomposisi `api_sections` (2.413 LOC → `api_sections/`)
- `crates/clawcrew-gateway/src/api_sections/mod.rs`: Route handler per-section konfigurasi, re-export publik.
- `crates/clawcrew-gateway/src/api_sections/handlers.rs`: Handler spesifik section (readiness, update, schema parsing).
- `crates/clawcrew-gateway/src/api_sections/tests.rs`: Seluruh unit test suite `mod tests` (dipindahkan bersih dari baris 1135-2413).

## Model Data & API Design
- **Zero Contract Change**: Seluruh endpoint REST (`/api/config/*`, `/api/sections/*`) dan WebSocket (`/ws`) tetap memiliki signature, request/response JSON, dan status error yang identik.
- **Facade Stabilitas**: `pub use api_config::*` dan re-export di `crates/clawcrew-gateway/src/lib.rs` dipertahankan sehingga caller di `src/main.rs` dan unit test eksternal tidak mengalami broken reference.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Biarkan file monolitik sampai Sprint 8 rename massal*: Ditolak, karena rename massal crate `clawcrew-gateway` → `galleon-gateway` di atas file monolitik 5.000 baris akan meningkatkan risiko konflik merge secara eksponensial.
- *Pecah ke crate terpisah*: Ditolak (pelanggaran YAGNI/Ponytail), concern ini murni modularisasi internal gateway.

## Rencana Pengujian (Testing Plan)
1. `cargo fmt --all -- --check` untuk menjamin kerapihan kode.
2. `cargo check -p clawcrew-gateway` untuk validasi tipe data dan visibility module (`pub(crate)` vs `pub`).
3. `cargo nextest run -p clawcrew-gateway --locked` untuk memverifikasi 100% test lulus.

## Rollout / Migrasi
Dikerjakan bertahap dalam 3 sub-task berantai (TASK-027, TASK-028, TASK-029). Setiap sub-task memiliki alokasi waktu maksimum pengerjaan <1 jam.
