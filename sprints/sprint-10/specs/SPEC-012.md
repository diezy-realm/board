---
id: SPEC-012
type: spec
spec_kind: api
title: Pemulihan router gateway Rust, inventaris konsumen, fixture kontrak Go
status: draft
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta: RES baseline F-01, F-04, F-14, F-15 pada `testing@3f3a729`. Sumber kode lama: `git show db18a3745^:crates/clawcrew-gateway/src/lib.rs` (disebut **OLD**).

## Pernyataan Masalah (Problem Statement)
1. `build_gateway_router` (`crates/galleon-gateway/src/gateway.rs:134`) hanya memasang ±23 rute. Commit `db18a3745` (2026-10-03) menghapus router 152 path. Konsumen yang kini 404: CLI `src/main.rs:8271` (`/admin/shutdown`), `:8328` (`/admin/sop/pending`), `:8513` (`/admin/paircode`); ACP bridge `src/bin/clawcrew-acp-bridge.rs:287,291` (`/pair/code`, `/pair`); webhook channel (`optional_channel_routes`, `lib.rs:514`, tidak pernah dipanggil).
2. Layer yang hilang: `RequestBodyLimitLayer(MAX_BODY_SIZE=65_536)`, `TimeoutLayer(REQUEST_TIMEOUT_SECS=30)` dengan rute long-running 600 s, `security_headers::apply[_with_hsts]` (OLD:2288–2357), dan `into_make_service_with_connect_info::<SocketAddr>()` (OLD:2387, 2447) yang dibutuhkan `require_localhost` rute admin. Saat ini `gateway.rs:98` memanggil `axum::serve(listener, app)` tanpa ConnectInfo. Konstanta dan modul masih ada (`lib.rs:54,72–75`).
3. Handler admin & pairing-lama **sudah terhapus** dari kode (F-14): `handle_admin_shutdown` (OLD:4619), `handle_admin_reload` (OLD:4675), `handle_admin_paircode` (OLD:4758), `handle_admin_paircode_new` (OLD:4805), `handle_pair` (OLD:2621), `handle_pair_code` (OLD:4954), `require_localhost`.
4. `src/tests.rs` gateway (7.596 baris, 188 test) yatim; OLD punya `#[cfg(test)] mod tests;` yang hilang saat refactor. `plugin_webhook/tests.rs:13` mengimpor `crate::tests::admin_paircode_state` yang tidak ada → kemungkinan besar test build crate ini gagal kompilasi (belum diverifikasi; cargo tidak ada di lingkungan audit).
5. Belum ada daftar resmi "siapa memakai rute apa", dan belum ada rekaman respons Go untuk dijadikan kontrak sebelum Go dihapus.

## Solusi yang Diusulkan (Proposed Solution)
Prinsip: **pulihkan, jangan rancang ulang**. Setiap handler yang dipulihkan diambil dari OLD, nama `clawcrew_*` diganti `galleon_*`, logging memakai `::galleon_log::record!`. Tidak ada rute tanpa konsumen.

1. **TASK-058 — Inventaris konsumen** `standard-docs/tech-standart/api-contracts/consumer-inventory.md`: tabel `method | path | konsumen (file:line) | implementasi sekarang (Go/Rust/none) | keputusan (port/restore/drop) | auth`. Sumber: `rg` di `web/src`, `apps/tauri/src`, `apps/galleoncode`, `src/main.rs`, `src/bin/*`, `nginx/`, `scripts/`. Termasuk konfirmasi bahwa rute di PRD-002 §5 "tanpa konsumen" memang tanpa konsumen di Tauri/CLI.
2. **TASK-059 — Layer & ConnectInfo** di `build_gateway_router`/`run_gateway_with_plugin_webhooks`: urutan sama dengan OLD:2290–2357 (`TimeoutLayer` 30 s → `RequestBodyLimitLayer` 64 KB → `security_headers::apply`, HSTS hanya bila TLS aktif); long-running router 600 s hanya untuk rute yang di OLD memakainya **dan** dipasang sekarang (`a2a::a2a_task_route` dsb.). Serve dengan `into_make_service_with_connect_info::<SocketAddr>()`. Batas body 64 KB dipasang pada **router inti** (sebelum `merge` router lain), bukan sebagai lapisan terluar, agar router fleet (SPEC-013 TASK-081) dapat memakai batas 1 MiB sendiri; timeout dan security headers tetap global.
3. **TASK-060 — Pairing**: pulihkan `handle_pair` (`POST /pair`, header `X-Pairing-Code`), `handle_pair_code` (`GET /pair/code`, hanya mengembalikan kode sebelum pairing pertama, perilaku OLD), dan pasang handler yang masih ada di `api_pairing.rs`: `POST /api/pairing/initiate`, `POST /api/pair`, `GET /api/devices`, `PATCH /api/devices/me/capabilities`, `DELETE /api/devices/{id}`, `POST /api/devices/{id}/token/rotate` (OLD:2200–2210).
4. **TASK-061 — Admin**: pulihkan `require_localhost`, `/admin/shutdown`, `/admin/reload`, `/admin/paircode`, `/admin/paircode/new`; pasang `/admin/sop/pending`, `/admin/sop/approve`, `/admin/sop/deny` dari `api_sop.rs` (path persis mengikuti konsumen CLI `src/main.rs:8328,8390,8394`).
5. **TASK-062 — Channel**: `.merge(optional_channel_routes())` + `/sop/{*rest}` webhook (`api_sop_webhook.rs`) bila tercantum di inventaris.
6. **TASK-063 — Test yatim**: tambahkan `#[cfg(test)] mod tests;` di `lib.rs`, lalu perbaiki kompilasi. Test yang menguji rute **yang sengaja tidak dipulihkan** dihapus (dicatat daftar nama test di RPT); test yang menguji rute yang dipulihkan harus hijau. Bila perbaikan > 1 jam, berhenti, laporkan `partial` dengan daftar sisa, dan KiroCrew memecah task.
7. **TASK-064 — Test tabel rute**: fungsi `pub fn route_inventory() -> &'static [(Method, &'static str, Access)]` **tidak** dibuat (YAGNI). Sebagai gantinya test integrasi `crates/galleon-gateway/tests/route_table.rs` yang menjalankan router di `127.0.0.1:0` dan, untuk setiap baris inventaris berstatus Rust: (a) tanpa token → 401 kecuali `Access::Public`, (b) `insta::assert_yaml_snapshot!` daftar `(method,path,status)`.
8. **TASK-065 — Fixture Go**: `scripts/contract/record_go_fixtures.sh` (bash + `curl` + `jq`, **tanpa file Go baru**) menjalankan `go run ./cmd/agent-engine` (dari `engine/`) terhadap direktori data sementara berisi salinan `engine/data`, memanggil setiap endpoint Go di inventaris berstatus `port`, dan menyimpan respons ke `tests/fixtures/go-fleet/<method>_<path_slug>.json` (dinormalisasi `jq -S`). Nilai volatil (timestamp, uptime, pid) dicatat sebagai daftar kunci volatil di `tests/fixtures/go-fleet/VOLATILE.md`.

## Model Data (Data Model)
Tidak ada entitas baru. `AppState` sudah memuat `shutdown_tx`, `reload_tx`, `device_registry`, `pending_pairings`, `pairing` (`state.rs:28–63`).

## Desain API (API Design)
| Method | Path | Akses | Sumber handler | Konsumen |
|---|---|---|---|---|
| POST | `/pair` | publik + rate-limit pair | OLD:2621 | ACP bridge `:291`, web (SPEC-014) |
| GET | `/pair/code` | publik, kode hanya sebelum pairing pertama | OLD:4954 | ACP bridge `:287`, web (SPEC-014) |
| POST | `/api/pairing/initiate` | Bearer | `api_pairing.rs:362` | web `ConnectedDevicesView.tsx:53` |
| POST | `/api/pair` | publik (kode sekali pakai) | `api_pairing.rs:388` | test `api_pairing.rs:1141`, perangkat kedua |
| GET | `/api/devices` | Bearer | `api_pairing.rs:533` | web (path diubah di TASK-084) |
| PATCH | `/api/devices/me/capabilities` | Bearer | `api_pairing.rs:623` | node/perangkat |
| DELETE | `/api/devices/{id}` | Bearer | `api_pairing.rs:568` | web (TASK-084) |
| POST | `/api/devices/{id}/token/rotate` | Bearer | `api_pairing.rs:674` | perangkat |
| POST | `/admin/shutdown` | localhost | OLD:4619 | CLI `main.rs:8271` |
| POST | `/admin/reload` | localhost | OLD:4675 | CLI (dicek TASK-058) |
| GET | `/admin/paircode` | localhost | OLD:4758 | CLI `main.rs:8513` |
| POST | `/admin/paircode/new` | localhost | OLD:4805 | CLI `main.rs:8502` |
| GET | `/admin/sop/pending` | localhost | `api_sop.rs:131` | CLI `main.rs:8328` |
| POST | `/admin/sop/approve`, `/admin/sop/deny` | localhost | `api_sop.rs:160`, `:171` | CLI `main.rs:8390,8394` |
| * | `optional_channel_routes()` | signature per channel | `lib.rs:514` | penyedia webhook eksternal |

Kode error: 401 `{"error":"Unauthorized — pair first via POST /pair, then send Authorization: Bearer <token>"}` (`api/mod.rs:51`); 403 untuk non-localhost di `/admin/*`; 413 body > 64 KB; 408 timeout (`TimeoutLayer::with_status_code`); 429 rate-limit pairing.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- Memulihkan seluruh 152 path OLD → ditolak (YAGNI; banyak tanpa konsumen, menambah attack surface).
- Membuat registry rute deklaratif (`DynamicRouter` di `handlers/mod.rs:332`) → ditolak: saat ini test-only dan `TurnApiHandler` tanpa auth; menambah lapisan baru tanpa kebutuhan.
- Menulis ulang handler admin dari nol → ditolak: OLD sudah teruji (test di `tests.rs`), cukup diadaptasi.
- Fixture via program Go kecil → ditolak (melanggar ODR "tidak ada Go baru"); `curl` cukup.

## Pertimbangan Keamanan (Security Considerations)
- OWASP Top 10:2025 A01/A07, API Top 10 2023 API2/API4 (Unrestricted Resource Consumption → body limit + timeout), API8, API9 (Improper Inventory Management → `consumer-inventory.md` + test tabel rute).
- `/admin/*` wajib `require_localhost` dengan `ConnectInfo` — tanpa ConnectInfo extractor gagal saat runtime, jadi TASK-059 adalah prasyarat TASK-061.
- `/pair/code` mengekspos kode sebelum pairing pertama (perilaku OLD). Mitigasi yang sudah ada: bind default `127.0.0.1` (`schema.rs:7759`) dan rate-limit pairing (`GatewayRateLimiter`). Tidak dilonggarkan lebih jauh.
- Token dibandingkan oleh `PairingGuard::is_authenticated` (`galleon-config/src/pairing.rs:347`); TASK-060 memverifikasi perbandingan constant-time (crate `subtle` sudah di `Cargo.lock`) dan melaporkannya; bila tidak constant-time, dicatat sebagai temuan, bukan diperbaiki diam-diam di task yang sama.

## Rencana Pengujian (Testing Plan)
- Per task: `cargo nextest run -p galleon-gateway --locked` + `cargo clippy -p galleon-gateway --all-targets --locked -- -D warnings`; output ringkas di RPT.
- TASK-059: test body 64 KB + 1 → 413; handler lambat → 408; header `X-Content-Type-Options: nosniff` ada.
- TASK-060/061: test OLD di `tests.rs` yang relevan dihidupkan; test baru non-loopback → 403 memakai `ConnectInfo` buatan (`axum::extract::connect_info::MockConnectInfo`).
- TASK-064: snapshot `insta` + matriks 401.
- TASK-065: script dijalankan dua kali menghasilkan fixture identik setelah normalisasi (kecuali kunci di `VOLATILE.md`).

## Rollout / Migrasi
Urutan 050 → 051 → 052 → 053 → 054 → 055 → 056 → 057. Tidak mengubah perilaku web (web masih ke Go sampai Sprint 12). Rollback = revert PR per task.
