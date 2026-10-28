# Amandemen RULES.md — 2026-10-29 (Rust bahasa tunggal galleon-fleet)

> Dasar: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md` dan ADR-0018.
> Diterapkan ke `RULES.md` oleh TASK-057 (KiroCrew). Aturan lain di `RULES.md` tetap berlaku; bila bertentangan, amandemen ini yang berlaku.

## A1. Bahasa produk inti (sisipkan sebagai aturan baru di §7)
- `galleon-fleet` adalah produk inti dan **hanya** berisi Rust (crates workspace + `apps/tauri`) dan UI Web (TypeScript di `web/`). Tidak ada file `*.go`, `go.mod`, `go.sum`, `go.work` baru sejak TASK-056 (`scripts/ci/check_no_go.sh diff`) dan tidak ada sama sekali sejak TASK-091 (`full`).
- Add-on / kebutuhan lain boleh ditulis dalam Go **di repository terpisah**, dan hanya berintegrasi lewat kontrak publik (ODR-30): HTTP/WS gateway Rust dengan token pairing (rute di `standard-docs/tech-standart/api-contracts/consumer-inventory.md`), MCP, atau plugin WASM `galleon:plugin@1.0.0` (`wit/v1/`). Tidak boleh ada gRPC internal, FFI, SDK/proto Go di repo core, atau berbagi file data dengan `galleon-fleet`.
- Kontrak dimiliki gateway Rust. Perubahan bentuk respons rute berkonsumen wajib disertai pembaruan test kontrak/snapshot (TASK-064, TASK-081) di PR yang sama.

## A2. Ukuran task (perketat §3 dan §7)
- Satu task = satu PR = **≤ 1 jam** kerja agent. Deskripsi task memuat `BRANCH: testing -> feat/<unik>`, `Alokasi pengerjaan: <= 1 jam`, dan (bila ada) `PRASYARAT (DEPENDENCY): TASK-xxx`.
- Branch **wajib** diawali `feat/` — `tools/agy-bridge/board_agy_bridge.py::_expected_branch` hanya mengenali `feat/...`; tanpa itu auto-unblock (`board_switch.py`) tidak pernah terpicu.
- Bila pelaksana menilai task > 1 jam, ia berhenti, menulis RPT `partial` berisi sisa pekerjaan, dan KiroCrew memecah task (bukan memperpanjang).
- `PRASYARAT` hanya efektif bila task prasyarat berada di **sprint aktif yang sama** (`board_switch.py::unblock` hanya membaca sprint aktif). Task pertama sebuah sprint dibuat `todo`; prasyarat lintas-sprint ditegakkan oleh aktivasi sprint (A3).

## A3. Status sprint `planning` dan aktivasi (tambahan §5 dan §7)
- `SPRINT.md` boleh berstatus `planning`: sprint disiapkan lebih awal dan **tidak dijalankan** bridge (`_sprint_is_active` hanya menerima `active`).
- Selama `planning`, PRD boleh `in-review` dan SPEC boleh `draft` walaupun task sudah ditulis. Ini pengecualian terbatas dari gate §1 ("Spec approved → Task") **hanya** untuk sprint `planning`.
- Checklist aktivasi (Scrum Master, sebelum mengganti `planning` → `active`):
  1. Sprint sebelumnya `closed`, dan semua task-nya `done` (ingat: `sprint-manager.py close NN` meng-carry-over task belum selesai ke sprint berikutnya).
  2. PRD sumber `approved` (Achmad); SPEC sprint ini `approved` (Lead).
  3. Pertanyaan terbuka PRD yang relevan dengan sprint dijawab atau default-nya diterima tertulis.
  4. `python3 validate.py --all` tidak menambah error dibanding sebelum aktivasi.
  5. Isi `start:` dan `end:` di front-matter.

## A4. Pengecualian urutan sprint (tambahan §7)
- Aturan "sekuensial, tidak melompat" tetap berlaku untuk **nomor** sprint. Owner boleh mengaktifkan sprint `planning` bernomor lebih besar lebih dulu bila semua prasyaratnya sudah `done`; keputusan dicatat satu baris di bagian "Langkah Owner" `SPRINT.md` (tanggal + alasan). Contoh yang diizinkan: Sprint 15 (TLS) setelah Sprint 10.
- Tetap hanya satu sprint `active` pada satu waktu.

## A5. Bukti di Report (perketat §4)
- RPT task kode wajib menyalin output **asli** dari perintah verifikasi yang tertulis di task (mis. `cargo nextest run …`, `cargo clippy … -D warnings`, `npm test`), termasuk ringkasan jumlah test. Klaim tanpa output = `partial`.
- Bila toolchain tidak tersedia di mesin pelaksana, tulis itu di RPT dan status `partial`; jangan menulis "lulus".

## A6. CI lokal Owner
- GitHub Actions dinonaktifkan; gate nyata adalah `~/Apps/dev-ci` (`.github/workflows/ci.yml:3–5`). Script gate baru yang ditambahkan task (`check_no_go.sh`, `check_production_unwrap.py`, `brand_gate.sh`) harus juga didaftarkan Owner di `gates.sh`; task mencatat langkah ini di RPT.
