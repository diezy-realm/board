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
- Bila pelaksana menilai task > 1 jam, ia **tidak berhenti tanpa PR**: bridge hanya menerima hasil bila branch ter-push dan PR terbuka (`board_agy_bridge.py::_verify_agy_delivered`); tanpa itu task jatuh ke `blocked` dan hanya di-retry `MAX_AUTO_RETRY=3` kali (`board_switch.py::unblock`), lalu menunggu tombol retry manual. Pelaksana mem-push bagian yang sudah hijau, membuka PR, menulis bagian 'Sisa pekerjaan' di deskripsi PR, dan menandai test yang belum beres `#[ignore = "<TASK-id> sisa"]`. Lead membuat task lanjutan dari deskripsi PR itu (bukan memperpanjang task).
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
- Aturan "sekuensial, tidak melompat" tetap berlaku untuk **nomor** sprint, dan itu juga perilaku otomatis: `sprint-manager.py auto` (timer `board-sprint`) menutup sprint yang semua task-nya `done` lalu mengaktifkan sprint-NN+1 yang berstatus `planning`, **tanpa** memeriksa §A3 (PRD/SPEC `approved`). Karena itu SPEC sprint berikutnya sudah harus `approved` sebelum sprint berjalan selesai.
- Mendahulukan sprint bernomor lebih besar (mis. Sprint 15 setelah Sprint 10) **tidak otomatis**. Prosedur: sebelum Sprint 10 ditutup, ubah `status: planning` pada `sprints/sprint-11/SPRINT.md` menjadi `status: hold` (hanya `planning` yang diaktifkan otomatis, `hold` dilewati); setelah Sprint 10 tertutup, Owner mengubah Sprint 15 menjadi `active` dan mengisi `start`/`end`, dengan satu baris alasan di "Langkah Owner"; setelah Sprint 15 tertutup, Owner mengembalikan sprint-11 menjadi `active` secara manual. Default program ini tetap berurutan 09 → 15.
- Tetap hanya satu sprint `active` pada satu waktu.

## A5. Bukti di Report (perketat §4)
- RPT task kode wajib menyalin output **asli** dari perintah verifikasi yang tertulis di task (mis. `cargo nextest run …`, `cargo clippy … -D warnings`, `npm test`), termasuk ringkasan jumlah test. Klaim tanpa output = `partial`.
- Bila toolchain tidak tersedia di mesin pelaksana, tulis itu di RPT dan status `partial`; jangan menulis "lulus".

## A6. CI lokal Owner
- GitHub Actions dinonaktifkan; gate nyata adalah `~/Apps/dev-ci` (`.github/workflows/ci.yml:3–5`). Script gate baru yang ditambahkan task (`check_no_go.sh`, `check_production_unwrap.py`, `brand_gate.sh`) harus juga didaftarkan Owner di `gates.sh`; task mencatat langkah ini di RPT.
- **Gate `Test` berstatus advisory** (`~/Apps/dev-ci/repos/galleon-fleet/gates.sh`, daftar `LIST`: `Test|heavy|none|25|1`; keputusan Owner 2026-10-17). Akibatnya test yang gagal **tidak** memblokir auto-merge ke `testing`, sehingga janji ODR-29 ("kontrak berubah tanpa snapshot = CI merah") belum ditegakkan. Disarankan sebelum TASK-059 merged: tambahkan gate non-advisory `Contract` yang menjalankan `cargo nextest run --locked -p galleon-gateway -p galleon-fleet-core` (cakupan sempit, bukan seluruh workspace).
- **Tidak ada lane Go di `gates.sh`** (tidak ada `go test`/`go vet`), dan `has_rust_changes` hanya melihat `*.rs`/`Cargo.toml`/`Cargo.lock`. PR yang hanya mengubah `engine/*.go` (TASK-055) lolos Required Gate tanpa satu pun test Go. Karena itu RPT TASK-055 wajib memuat output `go test` asli (A5).
- PR yang hanya mengubah Dockerfile/workflow (TASK-049, TASK-050) juga tidak menjalankan gate Rust; bukti berasal dari RPT (`cargo check -p galleoncode -p galleonrelay`).
- `agy-bridge.service` memakai `PATH` sendiri. `rg`, `node`, `npm` hanya ada di linuxbrew, jadi `/home/linuxbrew/.linuxbrew/bin` **ditambahkan di akhir** `PATH` unit tersebut (2026-10-29); perintah verifikasi di task boleh memakai `rg`. `cargo-nextest` ditemukan lewat `$CARGO_HOME/bin`.

## A7. Penutupan sprint
- `sprint-manager.py auto` menutup sebuah sprint hanya bila **semua** task-nya `done`, termasuk task berassignee `kirocrew`. Task milik KiroCrew tidak diambil bridge; Lead wajib menandainya `done` (dengan RPT) agar sprint tidak berhenti diam-diam.
- Setelah sprint ditutup, sprint-NN+1 `planning` otomatis menjadi `active` (lihat A4); pastikan PRD/SPEC-nya `approved` dan Owner sudah menjawab pertanyaan terbuka yang relevan sebelum itu.
