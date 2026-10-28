# RES-2026-10-29 — Standar Rekayasa Rust untuk Galleon Fleet (Riset Eksternal → Aturan Konkret)

> Peran: Senior Lead Engineer. Tujuan: menerjemahkan praktik eksternal yang terverifikasi menjadi aturan yang **bisa dicek mesin** di repo ini. Setiap aturan diberi status: `ADA` (sudah di repo), `DRIFT` (ada tapi salah/tidak efektif), `BARU` (belum ada, diusulkan). Aturan yang tidak punya masalah nyata di codebase **sengaja tidak ditambahkan** (YAGNI).

## 1. Sumber Eksternal

| Topik | Sumber | Poin yang dipakai |
|---|---|---|
| OWASP Top 10 | [OWASP Top 10:2025](https://top10.owasp.org/2025/) | A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging & Alerting Failures, A10 Mishandling of Exceptional Conditions |
| OWASP API | [OWASP API Security Top 10 2023](https://api-security.owasp.org/editions/2023/en/0x00-toc/) | API1 BOLA, API2 Broken Authentication, API3 BOPLA, API4 Unrestricted Resource Consumption, API5 BFLA, API9 Improper Inventory Management |
| OWASP ASVS | [ASVS 5.0.0 (stabil, 30 Mei 2025)](https://owasp.org/www-project-application-security-verification-standard/) | Dipakai sebagai checklist verifikasi per endpoint (auth, validasi input, error handling, logging) |
| Sonar untuk Rust | [SonarQube Cloud — Rust](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/languages/rust) | Analyzer Rust terintegrasi dengan Clippy (otomatis menjalankan Clippy; bisa dimatikan via `sonar.rust.clippy.enabled=false`), import coverage LCOV/Cobertura, `sonar.rust.cargo.manifestPaths` |
| Clippy | [Clippy docs](https://doc.rust-lang.org/clippy/) | Lint group & konfigurasi `clippy.toml` |
| Lints workspace | [Cargo — `[lints]`](https://doc.rust-lang.org/cargo/reference/lints.html), [Cargo — Workspaces](https://doc.rust-lang.org/stable/cargo/reference/workspaces.html) | `[workspace.lints]` hanya berlaku bila member menulis `[lints] workspace = true` |
| API idiom | [Rust API Guidelines — Checklist](https://rust-lang.github.io/api-guidelines/checklist.html) | Naming (C-CASE), error type yang bermakna (C-GOOD-ERR), type-safety (newtype, C-NEWTYPE), future-proofing (private fields, sealed traits) |
| nextest | [nextest — running](https://nexte.st/docs/running/), [nextest config reference](https://www.nexte.st/docs/configuration/reference/) | Doctest tidak didukung nextest → jalankan `cargo test --doc` sebagai langkah terpisah; retries & slow-timeout per profil |
| sccache | [sccache — Rust](https://github.com/mozilla/sccache/blob/main/docs/Rust.md) | Incremental compilation harus dimatikan; crate `bin`, `dylib`, `cdylib`, `proc-macro` tidak bisa di-cache |
| Supply chain | [cargo-deny](https://embarkstudios.github.io/cargo-deny/) | `advisories`, `bans`, `licenses`, `sources` |

## 2. Aturan Modularitas Crate

| ID | Aturan | Status | Alasan berbasis fakta |
|---|---|---|---|
| MOD-01 | Domain baru (fleet dashboard) masuk crate `galleon-fleet-core` **tanpa** dependensi `axum`, `galleon-runtime`, atau `galleon-gateway`. Adapter HTTP tinggal di `galleon-gateway/src/api_fleet/`. | BARU | `galleon-runtime` sudah ±272k LOC (RES baseline F-08); menambah fitur ke sana memperburuk compile time dan coupling. |
| MOD-02 | Arah dependensi satu arah: `gateway → runtime → (config, memory, tools, …)`; `gateway → fleet-core → (config, infra)`. Crate leaf tidak boleh bergantung pada `runtime`/`gateway`. Dicek dengan `cargo tree -e normal -i <crate>`. | BARU (formalisasi) | Graf saat ini sudah mengikuti pola ini; aturan menjaga agar tidak rusak. |
| MOD-03 | Ekstraksi dari `galleon-runtime` hanya untuk modul dengan coupling rendah dan konsumen jelas. Kandidat: `tunnel` (1,8k LOC, deps hanya `galleon_config`/`galleon_log`/`galleon_spawn`; dikerjakan TASK-105), `approval` (1,2k LOC, deps keluar runtime `i18n`/`security`; ditunda). `agent`/`sop` **tidak** diekstrak di program ini. | BARU | Tabel coupling RES baseline F-08. |
| MOD-04 | Tidak membuat crate untuk stub Go (`audit`, `briefing`, `charter`, `integration`, `navigator`, `treasury`) atau paket Go yang tidak terhubung (`squad`, `ship`, `mission`, `schedule`, `protocol`, `policy`). | BARU | RES baseline F-05. Bila produk membutuhkan Squad/Ship/Mission, buat story baru, bukan port. |
| MOD-05 | Batas ukuran file mengikuti `standard-docs/tech-standart/code-quality/rust-module-size-and-decomposition-standard.md` (sudah ada). | ADA | — |
| MOD-06 | Nama crate baru: prefix `galleon-`, kebab-case, tidak boleh `galleon-fleet` (bentrok dengan package root). | BARU | Package root bernama `galleon-fleet`. |

## 3. Aturan Idiom & Kualitas Rust

| ID | Aturan | Status | Cek mesin |
|---|---|---|---|
| RS-01 | Setiap crate member menulis `[lints] workspace = true`. Crate dengan hutang `unwrap/expect` memakai `#![allow(clippy::unwrap_used, clippy::expect_used)]` di `lib.rs` **dengan komentar ratchet** (`// RATCHET: BL-091, baseline N`), lalu dikurangi bertahap. | DRIFT → perbaiki | `scripts/ci/check_lints_inherit.sh` (baru, TASK di Sprint 14). Saat ini 1/60 crate yang mewarisi. |
| RS-02 | Crate baru wajib `#![forbid(unsafe_code)]` kecuali ada justifikasi tertulis di ADR. | BARU (untuk crate baru) | `rg -L 'forbid\(unsafe_code\)' crates/galleon-fleet-core/src/lib.rs` |
| RS-03 | Error library memakai `thiserror` enum per crate; `anyhow` hanya di binary/edge. Error HTTP dipetakan eksplisit ke status code; **tidak pernah** mengembalikan sukses palsu. | BARU (aturan), repo sudah memakai keduanya | Review + test negatif (lihat SPEC-013). Mengoreksi F-04 S-06. |
| RS-04 | Newtype untuk identifier yang menyeberang boundary (mis. `CollectionName` enum tertutup, bukan `String`). | BARU | Mengoreksi path traversal / nama koleksi bebas. |
| RS-05 | Tulis file data secara atomik: `tempfile::NamedTempFile::new_in(dir)` → tulis → `sync_all` → `persist(path)`. Permission 0600 di Unix. Pola ini **sudah ada** di `galleon-infra/src/session_store.rs:223` — reuse, jangan tulis ulang. | BARU (untuk fleet) | Mengoreksi F-04 S-05. `tempfile 3.26` sudah dependensi `galleon-infra`. |
| RS-06 | Logging hanya lewat `::galleon_log::record!` (sudah dipaksa `clippy.toml` `disallowed-macros`). Dokumen `rust-conventions.md` diperbarui agar tidak mengajarkan `tracing::info!` langsung. | DRIFT | `clippy -D warnings` |
| RS-07 | Async: tidak ada `std::fs`/`std::process` blocking di handler async; gunakan `tokio::fs`/`spawn_blocking`. | BARU | Review; `clippy::disallowed_methods` hanya bila ditemukan pelanggaran nyata. |
| RS-08 | Tidak menambah dependensi baru untuk port fleet API; reuse `sysinfo`, `qrcode`, `rusqlite`, `insta`, `schemars` yang sudah ada di `Cargo.lock`. | BARU | `git diff Cargo.lock` di PR port harus kosong kecuali entri crate internal baru. |

## 4. Aturan Keamanan (OWASP → kontrol Rust konkret)

| ID | Kontrol | OWASP | Implementasi di repo |
|---|---|---|---|
| SEC-01 | Semua rute non-publik melewati `require_auth` (`galleon-gateway/src/api/mod.rs:36`). Publik hanya: `/health`, `/ready`, `/api/health`, `/pair` (dengan rate limit), webhook channel bertanda tangan. | A01, API2, API5 | Test tabel rute: setiap rute non-publik → 401 tanpa bearer. |
| SEC-02 | Bind default `127.0.0.1` (sudah: `galleon-config/src/schema.rs:7759 default_gateway_host`); bind publik hanya via konfigurasi eksplisit. | A02 | Test konfigurasi default sudah cukup; tidak ada perubahan Rust. |
| SEC-03 | `RequestBodyLimitLayer` 64 KB global, override per-rute (upload), `TimeoutLayer` 30 s, security headers. | API4, A02 | Dipulihkan dari router lama (`db18a3745^`). |
| SEC-04 | Eksekusi perintah: allowlist `SecurityPolicy::validate_command_execution` (`galleon-config/src/policy.rs:3250`), tier tinggi lewat `ApprovalManager`, audit tiap eksekusi. **Tidak ada** eksekusi tanpa auth. | A01, A05, A06 | Test: tanpa token → 401; perintah di luar allowlist → 403; audit tertulis. |
| SEC-05 | Validasi input dengan tipe (serde `deny_unknown_fields` untuk request body yang mengubah state). | A05, API3 | Test body dengan field asing → 400. |
| SEC-06 | Error tidak membocorkan detail internal ke klien; detail ke log. | A10, A09 | Test respons error tidak memuat path/stack. |
| SEC-07 | Supply chain: `cargo deny check` + `cargo audit` (sudah di CI). CodeQL `rust` (sudah). Go dihapus dari matrix setelah Go dihapus. | A03 | CI. |
| SEC-08 | Sonar: aktifkan analyzer Rust (Clippy + coverage LCOV) **hanya** bila Owner menyediakan instance SonarQube Cloud/Server. Tanpa instance, Clippy `-D warnings` + CodeQL adalah gate. | A03, kualitas | `sonar-project.properties` + job CI kondisional `if: secrets.SONAR_TOKEN != ''`. |

## 5. Aturan Build & Test Tooling

| ID | Aturan | Status | Alasan |
|---|---|---|---|
| BT-01 | `rustc-wrapper = "sccache"` dipindah dari `.cargo/config.toml` ke env `RUSTC_WRAPPER` di CI/`Justfile`/devcontainer. Di job yang memakai sccache set `CARGO_INCREMENTAL=0`. | DRIFT | Cargo gagal di mesin tanpa sccache; sccache tidak bisa cache build incremental ([sccache Rust docs](https://github.com/mozilla/sccache/blob/main/docs/Rust.md)). |
| BT-02 | Tambah lane CI `cargo test --doc --workspace --locked`. | BARU | nextest tidak menjalankan doctest ([nextest](https://nexte.st/docs/running/)). |
| BT-03 | Komentar `.config/nextest.toml` disamakan dengan nilai (`default.retries = 0`). Retry hanya di profil `ci`; test flaky wajib dicatat, bukan disembunyikan retry. | DRIFT | Komentar "Retry sekali" vs `retries = 0`. |
| BT-04 | Hapus `--exclude clawcrew-desktop` (11 ref) karena `apps/tauri` sudah di luar workspace. | DRIFT | RES baseline F-09. |
| BT-05 | Test kontrak HTTP memakai `insta` snapshot JSON untuk setiap rute dashboard yang di-port; fixture diambil dari perilaku Go sebelum Go dihapus. | BARU | Menutup concern "gap kontrak" Owner: kontrak dikunci oleh test, bukan oleh dokumen. |

## 6. Yang Sengaja Tidak Diusulkan (YAGNI)

- Tidak ada gRPC internal Rust↔Rust; proto dihapus bersama Go.
- Tidak mengganti penyimpanan JSON fleet ke SQLite di program ini; format file dipertahankan agar data pengguna tidak perlu dimigrasi. Pergantian storage = story terpisah bila ada kebutuhan (mis. multi-writer).
- Tidak menambah fuzzing/proptest framework baru; `insta` + test negatif cukup untuk permukaan yang di-port.
- Tidak memecah `galleon-runtime` secara besar-besaran; hanya ekstraksi kandidat berisiko rendah dengan ukuran PR kecil.
