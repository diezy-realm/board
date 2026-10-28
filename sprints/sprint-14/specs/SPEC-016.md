---
id: SPEC-016
type: spec
spec_kind: tech
title: Higiene Rust — pewarisan lint workspace, doctest, sccache, drift tooling, Sonar kondisional
status: draft
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta: RES baseline §F-08/F-09/F-17; standar: RES rust-engineering-standards (RS-*, SEC-*, BT-*), rust-conventions amendment §3.

## Pernyataan Masalah (Problem Statement)
1. `[workspace.lints]` (root `Cargo.toml`: `rust.unsafe_code = "warn"`, `clippy.unwrap_used = "warn"`, `clippy.expect_used = "warn"`, `:81–83`) hanya diwarisi 1 dari 60 crate (`galleon-channel-wecom-ws`). Lint workspace praktis tidak berlaku.
2. `clippy.toml` tidak punya `allow-unwrap-in-tests`/`allow-expect-in-tests`; bila lint diwarisi, `cargo clippy --all-targets -- -D warnings` (`scripts/ci/run_clippy.sh:79`) akan gagal di ribuan `unwrap` di test, padahal kebijakan repo mengizinkan unwrap di test (`scripts/ci/check_production_unwrap.py`, T-CI-01).
3. `clippy.toml` reason `disallowed-macros` masih menyebut `::clawcrew_log::record!` (`:16–30`) padahal macro sebenarnya `::galleon_log::record!`; header "ClawCrew".
4. `.cargo/config.toml` memasang `rustc-wrapper = "sccache"` tanpa syarat dan menyebutnya "harmless" — cargo gagal di mesin tanpa sccache; sccache juga mensyaratkan incremental dimatikan dan tidak meng-cache crate `bin`/`proc-macro` ([sccache Rust docs](https://github.com/mozilla/sccache/blob/main/docs/Rust.md)).
5. Doctest tidak pernah dijalankan: nextest tidak mendukung doctest ([nextest](https://nexte.st/docs/running/)); tidak ada lane `cargo test --doc`.
6. `.config/nextest.toml` profil default `retries = 0` (`:7`) dengan komentar yang menyebut retry.
7. `homepage = "https://www.clawcrew.com"` (`Cargo.toml:11`). `--exclude clawcrew-desktop`: 11 referensi di `.github/` + 14 di `Containerfile`, `dev/ci.sh`, `scripts/ci/*` (package sebenarnya `galleon-desktop`, dan `apps/tauri` sudah di luar workspace).
8. `brand_gate.py` dan `check_production_unwrap.py` ada tetapi tidak dirujuk `ci.yml`.
9. Tidak ada `sonar-project.properties`; ketersediaan instance Sonar belum diketahui (Q4 PRD).

## Solusi yang Diusulkan (Proposed Solution)
- **TASK-093 — Fondasi lint:** `clippy.toml` tambah `allow-unwrap-in-tests = true`, `allow-expect-in-tests = true` (opsi resmi Clippy, [Clippy config](https://doc.rust-lang.org/clippy/lint_configuration.html)); perbaiki reason menjadi `::galleon_log::record!`. Pasang `scripts/ci/check_production_unwrap.py` di job `lint` `ci.yml` (dan catat untuk `gates.sh` Owner).
- **TASK-094 / TASK-095 / TASK-096 — Pewarisan bertahap** `[lints] workspace = true`:
  - Batch A (TASK-094), hitungan grep `unwrap|expect` ≤ 60, 31 crate: galleon-channel-twitch, galleon-channel-clawdtalk, galleon-channel-notion, galleon-commands, galleon-channel-twitter, galleon-dist, galleon-routing, galleon-channel-signal, galleon-macros, galleon-sop-graph, galleon-channel-linq, galleon-channel-wecom, galleon-channel-bluesky, galleon-channel-mochat, galleon-channel-dingtalk, galleon-relay-proto, galleon-spawn, galleon-channel-reddit, galleon-channel-nostr, galleon-i18n, galleon-channel-core, galleon-channel-irc, galleon-channel-amqp, galleon-channel-qq, galleon-channel-nextcloud, galleon-channel-voice-call, galleon-channel-email, galleon-channel-webhook, galleon-channel-filesystem, galleon-security-scrub, galleon-eval. (`galleon-channel-wecom-ws` sudah mewarisi; `galleon-desktop` di luar workspace.)
  - Batch B (TASK-095), hitungan 61–700, 18 crate: galleon-channel-mattermost, galleon-tool-call-parser, galleon-channel-imessage, galleon-channel-line, galleon-channel-git, galleon-channel-lark, galleon-api, galleon-tls, galleon-channel-discord, galleon-channel-wechat, galleonrelay, galleon-channel-whatsapp, galleon-channel-slack, galleon-hardware, galleon-channel-matrix, galleon-log, galleon-channel-telegram, galleon-plugins.
  - Batch C (TASK-096): `galleon-infra`, `galleon-channels`, `galleon-gateway`, `galleoncode`, `galleon-memory`, `galleon-providers`, `galleon-config`, `galleon-tools`, `galleon-runtime`, root package.
  - Aturan per crate: tambahkan `[lints] workspace = true`; jalankan satu kali `cargo clippy -p <a> -p <b> … --all-targets --locked -- -D warnings` untuk seluruh batch. Bila gagal karena `unwrap_used`/`expect_used`/`unsafe_code` di jalur produksi, tambahkan di `lib.rs`/`main.rs`: `#![allow(clippy::unwrap_used, clippy::expect_used)] // RATCHET(BL-091): <N> pemakaian produksi per <tanggal>; jangan menambah` (atau `unsafe_code` dengan alasan). **Tidak memperbaiki unwrap** di task ini (perubahan perilaku). Angka N dicatat di tabel RPT.
  - Bila satu batch melebihi 1 jam, KiroCrew memecahnya (aturan RULES amendment), bukan menunda.
- **TASK-097 — Doctest & nextest:** job `doctest` di `ci.yml`: `cargo test --doc --workspace --locked`; samakan komentar `.config/nextest.toml` dengan nilai. Bila doctest gagal pada saat pertama dijalankan, perbaiki contoh yang rusak **atau** tandai `ignore` dengan komentar alasan; daftar di RPT.
- **TASK-098 — sccache:** hapus `rustc-wrapper` dari `.cargo/config.toml`; set `RUSTC_WRAPPER=sccache` + `CARGO_INCREMENTAL=0` hanya di lingkungan yang memasang sccache (`ci.yml` env job Rust, `dev/ci.sh`, devcontainer bila ada).
- **TASK-099 — Drift nama:** ganti `--exclude clawcrew-desktop` → hapus (bukan diganti, karena `apps/tauri` tidak di workspace) di 25 lokasi; `homepage = "https://www.clawcrew.com"` (`Cargo.toml:11`) → URL produk yang dikonfirmasi Owner; default sama dengan `repository` (`https://github.com/diezy-realm/galleon-fleet`, `Cargo.toml:10`); pasang `scripts/ci/brand_gate.sh` di job `repo-structure`. Nama kompatibilitas runtime (mis. deteksi binary lama di `src/main.rs`) **tidak** disentuh di task ini.
- **TASK-100 — Sonar kondisional (default Q4):** `sonar-project.properties` dengan `sonar.rust.cargo.manifestPaths=Cargo.toml`, `sonar.rust.clippy.enabled=true`, `sonar.rust.lcov.reportPaths=lcov.info` ([Sonar Rust](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/languages/rust)); job `sonar` hanya jalan bila secret `SONAR_TOKEN` ada. Coverage LCOV dari `cargo llvm-cov nextest --lcov` hanya di job ini.
- **TASK-101 — Dokumen:** terapkan `rust-conventions-amendment-2026-10-29.md` ke `rust-conventions.md` (hapus bagian gRPC/tonic, perbarui logging, tambahkan aturan crate baru).

## Model Data (Data Model)
Tidak ada.

## Desain API (API Design)
Tidak ada.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- Memperbaiki semua `unwrap` sekarang → ditolak: ribuan perubahan perilaku, risiko bug baru (melanggar "jangan fix X menimbulkan Y").
- Script ratchet hitungan baru → ditolak: `check_production_unwrap.py` sudah mencegah penambahan di diff (YAGNI).
- Menambah banyak lint pedantic sekaligus → ditolak; set lint workspace tidak diubah di sprint ini, hanya diwariskan.
- Sonar wajib → ditolak sampai Owner mengonfirmasi instance.

## Pertimbangan Keamanan (Security Considerations)
- OWASP A10:2025 (Mishandling Exceptional Conditions): `unwrap/expect` di jalur produksi = panic; ratchet mencegah bertambah.
- OWASP A03 (Supply Chain): tidak ada dependensi baru; `cargo llvm-cov` hanya di job Sonar.
- `unsafe_code` diwariskan → setiap blok unsafe baru terlihat di review; crate baru `forbid`.

## Rencana Pengujian (Testing Plan)
- Per batch: satu invokasi `cargo clippy -p … -p … --all-targets --locked -- -D warnings` dan `cargo nextest run -p … -p … --locked` (tidak boleh ada perubahan perilaku).
- Cek global setelah TASK-096: `cargo metadata --no-deps --format-version 1 | jq -r '.packages[].manifest_path' | xargs grep -L '^\[lints\]'` kosong (kecuali fixture test yang dijustifikasi).
- TASK-098: `env -u RUSTC_WRAPPER cargo check -p galleon-api` di mesin tanpa sccache berhasil.
- TASK-099: `rg -n 'clawcrew-desktop' . --hidden --glob '!standard-docs/**' --glob '!CHANGELOG*'` kosong.

## Rollout / Migrasi
085 → 086 → 087 → 088 → 089 → 090 → 091 → 092 → 093. Tiap task PR terpisah. Rollback: revert.

## Temuan tambahan (diverifikasi 2026-10-29 pada testing@3f3a729, statis)
Selektor cargo yang masih memakai nama sebelum rename #93, di luar hotfix TASK-049/050: `-p clawcrew-plugins|clawcrew-runtime|clawcrew-gateway|clawcrew-eval` dan `--bin clawcrew` di `.github/workflows/windows-tests.yml` (212-249) dan `sop-eval-advisory.yml:46`; `--bin clawcrew` di `scripts/desktop/prepare-kernel.sh:81-85`, `dev/test-quickstart.sh:18-19`, `demo/run-agent-host.sh:49`, `demo/Dockerfile:44`, `scripts/ci/windows_test_scope.test.sh:397-443`; `-p clawcrew-desktop` di `dev/run-tauri-dev.sh:28`; `install ... target/dist/clawcrew` di `dist/aur/PKGBUILD`. Binary root kini `galleon` (Cargo.toml:117). Bila TASK-099 melebihi 1 jam, tulis RPT `partial` dan KiroCrew memecahnya.
