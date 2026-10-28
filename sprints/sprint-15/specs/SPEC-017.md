---
id: SPEC-017
type: spec
spec_kind: tech
title: Pemulihan wiring serve gateway (TLS, public-bind, path_prefix, tunnel) + ekstraksi crate galleon-tunnel
status: draft
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta: RES baseline §F-18 pada `testing@3f3a729`. **OLD** = `git show db18a3745^:crates/clawcrew-gateway/src/lib.rs`.

## Pernyataan Masalah (Problem Statement)
Commit `db18a3745` ("feat: refactoring rust") menulis ulang `run_gateway_with_plugin_webhooks` (`crates/galleon-gateway/src/gateway.rs:58–108`) menjadi `TcpListener::bind` + `axum::serve(listener, app)`. Yang ikut hilang, padahal config-nya masih ada dan masih bisa diubah lewat `/api/sections` (`api_sections/handlers.rs:454,1005`):

1. **TLS/mTLS** (`[gateway.tls]`): OLD membangun `tls::build_tls_acceptor` dan loop accept manual (OLD:2360–2440). Sekarang `tls.rs:16` masih ada tetapi tidak dipanggil → **gateway melayani HTTP polos walau `tls.enabled = true`** (OWASP A04:2025 Cryptographic Failures; ASVS V12). Dependensi `hyper`, `hyper-util`, `tokio-rustls`, `rustls` masih di `crates/galleon-gateway/Cargo.toml:43–51`.
2. **Peringatan public bind** (OLD:891–905, memakai `galleon_config::pairing::is_public_bind` yang masih ada di `pairing.rs:767`).
3. **`[gateway] path_prefix`** (`schema.rs:7662`): OLD `Router::new().nest(prefix, inner)` + redirect trailing slash (OLD:2336–2347). Sekarang diabaikan → deployment reverse-proxy dengan prefix rusak. Klien sudah membangun URL ber-prefix (`crates/galleon-runtime/src/daemon/mod.rs:413,1078`, `gateway_admin_url` di `src/main.rs`), jadi tanpa nest klien dan server tidak cocok; tambahkan test yang memanggil rute dengan dan tanpa prefix.
4. **Tunnel** (`[tunnel]`): OLD memanggil `galleon_runtime::tunnel::create_tunnel` lalu `start(host, port)` (OLD:1574–1605). Sekarang `create_tunnel` hanya dipanggil test (`src/tunnel/mod.rs`) → modul 1.828 LOC tidak pernah dijalankan.
5. Modularitas: `tunnel` hanya bergantung pada `galleon_config`, `galleon_log`, `galleon_spawn`, `anyhow`, `tokio` dan tidak punya pemakai `crate::tunnel` lain di runtime → kandidat ekstraksi paling aman (MOD-03).

Catatan prioritas: masalah 1–3 ada **hari ini** dan tidak bergantung pada penghapusan Go. Sprint ini hanya bergantung pada BL-087 (layer + ConnectInfo, TASK-059), sehingga Owner boleh mengaktifkannya tepat setelah Sprint 10 (pengecualian urutan, RULES amendment §A4).

## Solusi yang Diusulkan (Proposed Solution)
Prinsip sama dengan SPEC-012: **pulihkan dari OLD, jangan rancang ulang**; ganti `clawcrew_*`→`galleon_*`, `println!` → `::galleon_log::record!` (`clippy.toml` melarang `println!`).

- **TASK-102 — TLS/mTLS + peringatan public bind:** pulihkan `ACCEPT_ERROR_BACKOFF_MS` (OLD:122), `is_recoverable_accept_error` (OLD:131), cabang `tls_acceptor` (OLD:2360–2380) dan loop accept TLS (OLD:2386–2440) di `gateway.rs`, dengan `into_make_service_with_connect_info::<SocketAddr>()` (sudah dipasang TASK-059). `security_headers::apply_with_hsts` dipakai bila TLS aktif (sudah diatur TASK-059). `.expect("infallible make_service")` di OLD diganti `match` pada `Result<_, Infallible>` (`Ok(svc) => svc, Err(never) => match never {}`) agar lolos `clippy::expect_used` tanpa allow. Pulihkan peringatan public bind (OLD:891–905).
- **TASK-103 — `path_prefix`:** pulihkan nest + redirect (OLD:2336–2347) setelah layer dipasang; validasi prefix di config sudah ada (cek `rg -n path_prefix crates/galleon-config/src` di RPT, jangan menambah validasi baru bila sudah ada).
- **TASK-104 — Tunnel:** pulihkan start tunnel (OLD:1574–1605) setelah `listener.local_addr()`; kegagalan konstruksi/start = `WARN` dan tetap jalan lokal (perilaku OLD). Proses child memakai `kill_on_drop(true)` (`tunnel/*.rs`), sehingga tunnel berhenti saat gateway selesai; tambahkan `tun.stop().await` setelah serve selesai (tanpa mengubah trait).
- **TASK-105 — Ekstraksi `crates/galleon-tunnel`:** `git mv crates/galleon-runtime/src/tunnel crates/galleon-tunnel/src` (riwayat terjaga), `Cargo.toml` crate baru (`[lints] workspace = true`, `#![forbid(unsafe_code)]`, deps hanya yang dipakai), `galleon-runtime/src/lib.rs:55` menjadi `pub use galleon_tunnel as tunnel;` (kompatibilitas, tanpa deprecation noise), gateway memanggil `galleon_tunnel::create_tunnel` langsung. Perluas `tests/architecture/dependency_direction.rs` (bukan test baru): `galleon-tunnel` tidak boleh bergantung pada `galleon-runtime`/`galleon-gateway`/`galleon-channels`; `galleon-fleet-core` (SPEC-013) tidak boleh bergantung pada `galleon-gateway`/`galleon-channels`/`galleon-providers`.
- **Tidak dilakukan:** ekstraksi `approval` (bergantung `i18n`/`security` runtime; butuh pemindahan modul lain → backlog lanjutan bila ada kebutuhan nyata, YAGNI); mDNS advertisement (`nodes/mdns.rs` ada tapi tidak dipasang) → Q9 PRD, default tidak dipulihkan sampai ada konsumen.

## Model Data (Data Model)
Tidak ada.

## Desain API (API Design)
Tidak ada rute baru. Perubahan perilaku yang disengaja: (a) bila `tls.enabled`, port gateway berbicara TLS; (b) bila `path_prefix` diisi, semua rute berada di bawah prefix; (c) bila `[tunnel]` bukan `none`, proses tunnel dijalankan.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- `axum-server` dengan rustls → ditolak: dependensi baru (N-01), padahal kode OLD + deps sudah ada.
- Menghapus config TLS/tunnel/path_prefix karena tidak dipakai → ditolak: config terekspos di UI dan dokumen; menghapusnya memutus pengguna yang sudah mengatur (Q8 PRD, default pulihkan).
- Ekstraksi `approval` lebih dulu → ditolak (lihat di atas).

## Pertimbangan Keamanan (Security Considerations)
- A04:2025 Cryptographic Failures: TLS yang dikonfigurasi wajib benar-benar aktif; mTLS mengikuti `client_auth`.
- A02:2025 Security Misconfiguration: peringatan public bind; tunnel mengekspos gateway ke publik → `require_pairing` (default `true`, `schema.rs`) tetap berlaku; RPT TASK-104 mencatat bahwa rute publik hanya `/health`, `/ready`, `/pair`, `/pair/code` (dari test tabel rute TASK-064).
- Handshake TLS gagal dicatat `DEBUG` (tidak membocorkan detail ke klien), sama dengan OLD.

## Rencana Pengujian (Testing Plan)
- TASK-102: test integrasi di `crates/galleon-gateway/tests/` memakai sertifikat self-signed dari `rcgen` 0.13 (sudah dev-dependency gateway, `crates/galleon-gateway/Cargo.toml:105`) → `GET /health` via TLS = 200, via HTTP polos = gagal handshake.
- TASK-103: `path_prefix = "/galleon"` → `GET /galleon/health` 200, `GET /health` 404, `GET /galleon/` 308.
- TASK-104: `[tunnel] tunnel_provider = "custom"` dengan `start_command` = `echo https://example.test` → URL tercatat di log; provider tidak valid → gateway tetap jalan.
- TASK-105: `cargo nextest run -p galleon-tunnel` (test pindah dari `src/tunnel/mod.rs`), `cargo test --test architecture`, `cargo tree -p galleon-tunnel --edges normal --depth 1`.

## Rollout / Migrasi
094 → 095 → 096 → 097. Tiap task satu PR. Rollback: revert PR (konfigurasi pengguna tidak berubah).
