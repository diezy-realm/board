---
id: SPEC-011
type: spec
spec_kind: tech
title: Governance Rust-only, steering agent, kontainmen Go, guard no-new-Go
status: draft
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta merujuk `board/research/RES-2026-10-29-rust-single-language-baseline.md` (disingkat RES) pada `testing@3f3a729`.

## Pernyataan Masalah (Problem Statement)
1. Keputusan Rust-only belum ada di repo; ODR/ADR lama (ODR-22, ODR-25, ADR-004/005, boundary policy v1) masih menyatakan Go sebagai Tier 3 → agent mengikuti dokumen lama.
2. File steering agent masih menyuruh menulis Go (RES F-09): `.github/copilot-instructions.md`, `.github/instructions/*`, `.gemini/`, `.kiro/steering/`, `apps/tauri/AGENTS.md`. `AGENTS.md`/`CLAUDE.md` root sudah bersih (0 referensi Go).
3. Selama Go masih berjalan (sampai Sprint 13), `:9090` bind ke semua interface (`engine/core/metrics/metrics.go:108` memakai `":%d"`; listener gRPC `engine/app/app.go:110` juga `":%d"`) dan eksekusi terminal tanpa auth (`engine/src/fleet/delivery.go:72,75` → handler `:442`) = RCE jaringan lokal (RES F-04 S-01/S-02).
4. Tidak ada mekanisme yang mencegah PR baru menambah Go.

## Solusi yang Diusulkan (Proposed Solution)
- **Dokumen (TASK-052):** salin paket ini ke `galleon-fleet/standard-docs/` apa adanya: ODR-2026-10-29, ADR-0018, `01-boundary-policy.md` v2 (ganti v1), `SUPERSESSION-INDEX-2026-10-29.md`, `rust-conventions-amendment-2026-10-29.md`, serta `templates/template-odr.md` dan `templates/template-adr.md` (Tier Go dihapus → 3 tier). Tambah banner `> Superseded by ODR-2026-10-29 / ADR-0018` di baris pertama setiap dokumen yang tercantum di index (tanpa mengubah isi lain).
- **Steering (TASK-053, TASK-054):** hapus instruksi Go; ganti dengan satu kalimat rujukan ke ADR-0018 + boundary policy v2. Tidak menulis ulang aturan Rust yang sudah ada.
- **Kontainmen Go (TASK-055), minimal:**
  - `engine/core/metrics/metrics.go:108` dan `engine/app/app.go:110` → `fmt.Sprintf("127.0.0.1:%d", …)`; env `GALLEON_ENGINE_BIND` **tidak** ditambahkan (YAGNI; Go akan dihapus).
  - Bungkus handler terminal (`/api/terminal/exec`, `/api/engine/execute`) dengan pemeriksaan header `Authorization: Bearer` yang dibandingkan constant-time (`crypto/subtle`) dengan env `GALLEON_ENGINE_TOKEN`; bila env kosong → selalu 401 (fail-closed). Web saat ini tidak bisa memakai terminal via Go setelah ini — **disengaja**; terminal kembali di Sprint 11 lewat Rust.
- **Guard (TASK-056):** `scripts/ci/check_no_go.sh` mode `diff` (Sprint 09–12): gagal bila `git diff --name-only --diff-filter=A origin/testing...HEAD` berisi `*.go`, `go.mod`, `go.sum`, `go.work`. Mode `full` (Sprint 13): gagal bila `git ls-files '*.go' 'go.mod' 'go.work'` tidak kosong. Dipasang sebagai step di job `repo-structure` pada `.github/workflows/ci.yml`. **Catatan fakta:** `ci.yml:3–5` menyatakan GitHub Actions dimatikan dan CI berjalan lokal lewat `~/Apps/dev-ci` (`repos/galleon-fleet/gates.sh`, di luar repo, tidak bisa diaudit dari sini). Karena itu Owner wajib menambahkan pemanggilan `scripts/ci/check_no_go.sh diff` ke `gates.sh` (langkah Owner di SPRINT.md sprint-09); `ci.yml` diupdate agar daftar lane tetap selaras seperti diminta komentar `ci.yml:4–5`. Perubahan file Go yang **sudah ada** tetap boleh (diperlukan TASK-055).
- **Board (TASK-057):** terapkan `board/RULES-amendment-2026-10-29.md` dan `board/TEMPLATES-amendment-2026-10-29.md` ke `RULES.md`/`TEMPLATES.md`.

## Model Data (Data Model)
Tidak ada perubahan model data.

## Desain API (API Design)
Tidak ada endpoint baru. Perubahan perilaku Go sementara:

| Endpoint Go | Sebelum | Sesudah TASK-055 |
|---|---|---|
| `POST /api/terminal/exec`, `POST /api/engine/execute` | tanpa auth | 401 `{"error":"unauthorized"}` kecuali Bearer = `GALLEON_ENGINE_TOKEN` |
| Listener HTTP `:9090` dan gRPC `GRPCPort` | semua interface | `127.0.0.1` |

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- Tidak menyentuh Go sama sekali karena akan dihapus → ditolak: 4 sprint dengan RCE LAN terbuka.
- Menghapus rute terminal Go sekarang → setara dengan auth fail-closed, tetapi lebih banyak diff dan merusak test Go yang ada. Auth fail-closed lebih kecil.
- Guard berbasis pre-commit hook → ditolak: tidak mengikat agent di CI.

## Pertimbangan Keamanan (Security Considerations)
- OWASP Top 10:2025 A01 (Broken Access Control), A02 (Security Misconfiguration); OWASP API Top 10 2023 API2 (Broken Authentication), API8 (Security Misconfiguration).
- Perbandingan token constant-time; token tidak pernah di-log.
- Guard CI = kontrol integritas (A08) untuk keputusan arsitektur.

## Rencana Pengujian (Testing Plan)
- TASK-055: `go test ./src/fleet/... ./src/server/...` + test baru: tanpa header → 401; header salah → 401; env kosong + header apa pun → 401; benar → handler jalan. `ss -ltnp | grep -E '9090|50051'` menunjukkan alamat `127.0.0.1`.
- TASK-056: jalankan script pada branch berisi file `x.go` baru (harus gagal) dan branch tanpa (harus lolos); salin output ke RPT.
- TASK-052–054, 049: `rg` sebelum/sesudah disalin ke RPT; `python3 validate.py --all` untuk board.

## H. Hotfix: selektor build setelah rename (TASK-049, TASK-050)
**Fakta (testing@3f3a729):** package kini `galleoncode` dan `galleonrelay`; tidak ada package `zerocode`/`zerorelay`. Referensi lama masih ada di Dockerfile (150-207), Dockerfile.debian (86-171), Containerfile (204, 291), dist/aur/PKGBUILD:38, release-stable-manual.yml:343-344, cross-platform-build-manual.yml:278,289, setup.bat:245,282,283, scripts/dev/mtls-relay-testbed.sh:123, dan assert test di xtask/src/generate/spec.rs:1696,1699. Dockerfile.alpine:141-148 sudah benar dan menjadi pola acuan.

**Keputusan default D-HF1:** nama artefak publik (binary terpasang `zerocode`, tag image `-zerorelay`, nama asset rilis) tidak diubah. Hanya selektor build, glob artefak build, dan path sumber yang diganti. Mengubah nama artefak publik memerlukan keputusan Owner terpisah (rebrand ODR-19).

**Pembagian:** TASK-049 (Docker family, Containerfile, PKGBUILD) lalu TASK-050 (workflow, xtask test, setup.bat, script dev). Berurutan karena keduanya dapat menyentuh `xtask/src/generate/*` bila baris berada di zona `generated:`.

**Di luar scope:** selektor `clawcrew-*` dan `--bin clawcrew` (lihat SPEC-016 'Temuan tambahan').

## Rollout / Migrasi
Urutan task 044 → 045 → 046 → 047 → 048 → 049, masing-masing satu PR ke `testing`. Tidak ada flag. Rollback = revert PR.
