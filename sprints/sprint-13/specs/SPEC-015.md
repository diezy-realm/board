---
id: SPEC-015
type: spec
spec_kind: tech
title: Dekomisioning Go, proto, strangler, gRPC SystemGateway
status: draft
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Prasyarat: smoke E2E TASK-087 hijau tanpa proses Go. Fakta pada `testing@3f3a729`.

## Pernyataan Masalah (Problem Statement)
Setelah Sprint 12 tidak ada konsumen produksi untuk Go, tetapi repo masih memuat:
- `engine/` (Go module), `go.work`, `web/data/` (seed camelCase yang tidak dirujuk kode, F-16), `scripts/migrations/extract-seed.mjs` (bila belum dihapus di TASK-070).
- `proto/agent_service.proto` — satu-satunya konsumen Rust: `crates/galleon-gateway/build.rs:23–38` (tonic-build, butuh `protoc`).
- `crates/galleon-gateway`: `strangler_runner.rs` (`/api/turn` → Go `127.0.0.1:50051`, `:461–475`), `grpc_system_gateway.rs` (server gRPC `:50052`, F-03), `start_grpc_server` (`gateway.rs:17`, tidak pernah dipanggil), `handlers/mod.rs:285–319` (`TurnApiHandler`, test-only, tanpa auth), re-export `lib.rs:58,133–134`, test `tests/system_gateway_integration_test.rs`, dependensi `tonic = "0.12"`, `prost = "0.13"`, `tonic-build = "0.12"` (`Cargo.toml:33–39,101`). `install_strangler_agent_runner` tidak dipanggil di produksi (runner produksi = `RuntimeAgentRunner`, `galleon-runtime/src/agent/agent/mod.rs:4290`).
- `apps/galleoncode`: section `[engine]` (`src/config/mod.rs:276–310`, nonaktif default) + `tests/contract_test.rs`.
- `crates/galleon-eval/src/runner.rs`: nama `GoTurnRequest` walau runner memakai Agent Rust.
- CI: `.github/workflows/engine-ci.yml`; deteksi Go di `pr-testing-gate.yml:45,129,157`.
- Test arsitektur 4-tier: `tests/architecture/tier_boundaries.rs` (`test_go_engine_tier_boundaries` `:158`), `no_duplicate_risk_tier.rs` (memindai `web-2/src` yang tidak ada, F-17).
- `prost = "0.14"` di `galleon-channel-lark` dan `galleon-channels` **bukan** bagian Go boundary (protobuf Lark) — tidak disentuh.

## Solusi yang Diusulkan (Proposed Solution)
1. **TASK-088 — Rust gRPC/strangler:** hapus `strangler_runner.rs`, `grpc_system_gateway.rs`, `start_grpc_server`, `TurnApiHandler` + registrasinya, re-export terkait, `tests/system_gateway_integration_test.rs`, `build.rs`, dependensi `tonic`/`prost`/`tonic-build` di gateway. Rute `/api/turn` dihapus dari `build_gateway_router` bila masih ada (tidak berkonsumen, RES §3). Perbarui komentar `crates/galleon-api/src/sop.rs:4`, `crates/galleon-gateway/Cargo.toml:32`.
2. **TASK-089 — proto & klien Go di Rust:** hapus `proto/` setelah `rg -n 'agent_service|proto/' --glob '!standard-docs/**'` kosong; hapus `[engine]` galleoncode + `contract_test.rs`. Struct config galleoncode tidak memakai `deny_unknown_fields` (`rg deny_unknown_fields apps/galleoncode/src/config/mod.rs` kosong), sehingga file config pengguna yang masih memuat `[engine]` tetap terbaca — TASK-089 menambahkan satu test untuk itu; rename `GoTurnRequest` → `EvalTurnRequest` di galleon-eval.
3. **TASK-090 — Hapus Go:** `git rm -r engine go.work web/data` (+ `scripts/migrations/extract-seed.mjs` bila masih ada). Perbarui `.gitignore`, `.dockerignore`, `Makefile`/script yang merujuk `engine/` (`rg -n 'engine/' --glob '!standard-docs/**' --glob '!CHANGELOG*'`).
4. **TASK-091 — CI & test arsitektur:** hapus `engine-ci.yml`; hapus deteksi Go di `pr-testing-gate.yml`; `check_no_go.sh` dipanggil mode `full`; tulis ulang `tier_boundaries.rs` ke 3 tier (Desktop shell / Rust core / Web UI): hapus `test_go_engine_tier_boundaries`, tambah `test_no_go_sources` (gagal bila ada `*.go`); `no_duplicate_risk_tier.rs` memindai `web/src` dan dokumentasinya menyebut Rust (`galleon-fleet-core`) sebagai SSOT. Owner memperbarui `gates.sh` lokal (langkah Owner di SPRINT.md).
5. **TASK-092 — Dokumen:** beri banner Superseded dan/atau pindahkan ke `standard-docs/archive/go-engine/` dokumen di `SUPERSESSION-INDEX-2026-10-29.md` §3; `http-engine-api.md` → banner + rujukan ke `consumer-inventory.md`.

## Model Data (Data Model)
Tidak ada. Data pengguna tidak tersentuh (`<data_dir>/fleet` sudah dipakai sejak Sprint 11).

## Desain API (API Design)
Endpoint dihapus: `POST /api/turn` (Rust, tidak berkonsumen), server gRPC `:50052` (tidak pernah start). Tidak ada endpoint baru.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- Memindahkan `engine/` ke repo arsip dulu → opsional; riwayat git sudah menyimpan semuanya (`git log -- engine`). Bila Owner ingin repo arsip, itu langkah Owner, bukan task agent.
- Mempertahankan `proto/` untuk add-on Go masa depan → ditolak: kontrak add-on (ODR-30) adalah HTTP/WS publik gateway, bukan proto internal yang tidak terjaga.

## Pertimbangan Keamanan (Security Considerations)
- Mengurangi permukaan serangan: listener `:9090`, `:50051`, `:50052` hilang (OWASP A02).
- Supply chain (OWASP A03): menghapus toolchain Go + `protoc` + `tonic-build` dari build; `cargo deny check` (bila dikonfigurasi) dijalankan dan outputnya di RPT TASK-088.

## Rencana Pengujian (Testing Plan)
- `cargo check --workspace --all-targets --locked`, `cargo nextest run --workspace --locked`, `cargo clippy --workspace --all-targets --locked -- -D warnings`.
- `cargo test --test architecture` (root package, `Cargo.toml:523–524`).
- `rg --files -g '*.go' -g 'go.mod' -g 'go.work'` kosong; `rg -n ':9090|:50051|:50052|GALLEON_ENGINE_URL' --glob '!standard-docs/archive/**' --glob '!CHANGELOG*'` kosong atau tiap sisa dijustifikasi di RPT.
- Ulangi `scripts/e2e/smoke_dashboard.sh` (TASK-087) setelah TASK-090.

## Rollout / Migrasi
080 → 081 → 082 → 083 → 084. Rollback per PR. Setelah TASK-090 Go tidak bisa dijalankan lagi dari `testing`; versi terakhir yang memuat Go dicatat (SHA) di RPT TASK-090.
