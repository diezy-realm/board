# ATURAN BERSAMA — Board Koordinasi KiroCrew ⇄ agy (Antigravity)

> **WAJIB DIBACA agent mana pun (KiroCrew atau agy) SEBELUM menulis ke board ini.**
> Board ini adalah *single source of truth* bersama. Jangan menulis sesuka hati —
> ikuti format di `TEMPLATES.md` dan alur di dokumen ini. Penulisan yang tidak
> sesuai front-matter akan **ditolak validator**.
>
> **Landasan teknis & arah produk** (arsitektur, standar kode, ODR) ada di repo
> `galleon-fleet` → baca `standard-docs/ONBOARDING.md` sebelum mengambil task
> yang menyentuh kode. Board = pekerjaan berjalan; standard-docs = aturan baku.

---

## 1. Alur Kerja (urutan kerja dunia nyata — gaya tim produk + Scrum)

```
💡 User Story  →  📋 Backlog  →  📄 PRD/Riset  │  🔧 Spec  →  ✅ Task  →  📊 Report
└──────────── PRODUCT BACKLOG ────────────────┘  └──────── SPRINT BACKLOG ────────┘
   product-backlog/stories|backlog|prd            sprints/sprint-NN/specs|tasks|reports
```

**Struktur folder (model Scrum):**
```
~/Apps/board/
  product-backlog/   stories/ backlog/ prd/      ← semua kerja belum masuk sprint
  sprints/
    sprint-01/       SPRINT.md  specs/ tasks/ reports/   ← sprint AKTIF (sekuensial dari 01)
    sprint-02/ ...
  archive/           sprint-NN/ ...               ← sprint yang sudah ditutup (all-done)
  RULES.md  TEMPLATES.md  validate.py  sprint-manager.py
```

Pemisahan Scrum: **Product Backlog** (semua kebutuhan, dinamis) vs **Sprint Backlog**
(subset terpilih untuk sprint berjalan, tetap selama sprint) vs **Increment** (hasil Done).

Setiap tahap **hanya boleh maju** jika tahap sebelumnya sudah mencapai status gate-nya.
Ini meniru alur nyata: ide tidak langsung jadi kode — ia disaring, diriset,
dispesifikasikan, baru dieksekusi, lalu dilaporkan.

### Gate antar-tahap (syarat naik tahap)
| Dari → Ke | Syarat (gate) |
|-----------|---------------|
| Story → Backlog | Story `status: ready` + punya Acceptance Criteria + lolos INVEST |
| Backlog → PRD | Backlog `status: refined` + butuh riset/keputusan produk |
| PRD → Spec | PRD `status: approved` (disetujui owner/Achmad) |
| Spec → Task | Spec `status: approved` + punya API/Data model (jika teknis) |
| Task → Report | Task `status: done` + Acceptance Check terpenuhi dengan bukti |

> Catatan: tidak semua item wajib lewat PRD. Item kecil/teknis boleh
> Story → Backlog → Spec → Task. PRD dipakai untuk fitur yang butuh riset/keputusan.

---

## 2. RACI + Peran Scrum (Siapa Mengerjakan Apa)

**Pemetaan peran Scrum → aktor kita:**
| Peran Scrum | Aktor | Tanggung jawab |
|-------------|-------|----------------|
| **Product Owner** | Achmad (dibantu KiroCrew-PO) | Prioritas Product Backlog, approve PRD, definisi "value" |
| **Scrum Master** | KiroCrew-Lead | Jaga proses: gate antar-stage, tutup sprint, carry-over, archive |
| **Developers** | KiroCrew crew + **agy** | Eksekusi task jadi Increment yang Done |

| Tahap | Penanggung jawab | Boleh menulis | Keputusan akhir |
|-------|------------------|---------------|-----------------|
| Story | Product Owner / Achmad | kirocrew, achmad | Achmad |
| Backlog | KiroCrew (Lead/PO) | kirocrew | Lead |
| PRD / Riset | KiroCrew (PO + R&D) | kirocrew | Achmad (approve) |
| Spec | KiroCrew (Lead) | kirocrew | Lead (approve) |
| Task | KiroCrew mem-*assign* | kirocrew | — |
| Report | **Pelaksana task** (kirocrew ATAU agy) | kirocrew, agy | reviewer |

**Pembagian mesin:**
- **KiroCrew** = perencanaan, spec, review, koordinasi, + peran Scrum Master (kelola sprint).
- **agy (Antigravity)** = Developer pelaksana task `assignee: agy` → kerjakan → tulis Report.
- Keduanya **membaca** seluruh board; keduanya **menulis** sesuai RACI di atas.

---

## 3. Aturan Penulisan (hard rules)

1. **ID stabil & unik** per jenis: `US-`, `BL-`, `PRD-`, `SPEC-`, `TASK-`, `RPT-` + nomor urut 3 digit (`US-001`).
   ID tidak pernah dipakai ulang walau item dihapus.
2. **Front-matter YAML wajib** di tiap file (kecuali task = JSON). Field wajib ada di `TEMPLATES.md`. Kurang field → **ditolak validator**.
3. **Jejak balik wajib**: tiap artefak menyimpan link ke sumbernya
   (`source_story`, `source_backlog`, `source_prd`, `source_spec`, `source_task`).
   Dilarang merujuk ID yang **tidak ada** — validator cek keberadaan file sumber.
4. **Jangan klaim tanpa bukti**: Report wajib punya `Acceptance Check` dengan bukti
   nyata (path file / commit / PR). Status `done` tanpa bukti = `invalid`.
5. **Bahasa**: isi dokumen **Bahasa Indonesia**. Heading boleh istilah baku
   (Objective, Acceptance Criteria) karena standar lintas-tim.
6. **Satu file = satu artefak.** Jangan gabung dua story dalam satu file.
7. **Status hanya dari daftar sah** (lihat tiap template). Status di luar daftar = `invalid`.
8. **Jangan edit milik mesin lain yang sedang `in-progress`** tanpa alasan tercatat
   di field `notes`. Hindari dua penulis pada file yang sama bersamaan.

---

## 4. Status yang sah (per jenis)

- **Story**: `draft → ready → in-backlog → done`
- **Backlog**: `todo → refined → in-progress → review → done`
- **PRD**: `draft → in-review → approved`
- **Spec**: `draft → approved → implemented`
- **Task**: `todo → in-progress → blocked → review → done`
- **Report**: `done | partial | failed`

---

## 5. Koordinasi antar-mesin (bagaimana task mengalir ke agy)

1. KiroCrew membuat `tasks/TASK-xxx.json` dengan `assignee: agy`, `status: todo`,
   `description` (instruksi lengkap, berdiri sendiri), dan `source_spec`.
2. Tiga systemd user timer (interval diubah dari halaman board, view Status):
   - `agy-bridge` (eksekutor): task `assignee=agy & status=todo` -> `in-progress`, agy dipanggil headless
     (`--print-timeout 0`, tanpa batas waktu; task multi-wake memakai ulang `conversation_id`).
   - `board-unblock`: `blocked` -> `todo` saat task PRASYARAT sudah done + PR-nya merged (atau auto-retry terbatas).
   - `board-review`: task `review` -> `done` (PR merged), `todo` (CI lokal merah, maks 3x), atau `blocked`.
   - CI lokal (`~/Apps/dev-ci`) BUKAN timer: `board-review` memulainya (unit `ci-pr<N>-<sha8>`) untuk task `review`
     yang head PR-nya belum punya verdict `local/Required Gate`; satu build pada satu waktu (antre), hasil = commit status `local/*`.
3. agy mengerjakan, membuka PR, menulis `reports/RPT-xxx.md` (dengan `source_task`) + `report: RPT-xxx`.
   Bridge men-set `review` selama PR masih open, `done` bila tak ada PR (task non-kode) atau PR sudah merged.
4. Kembali ke `todo`: otomatis oleh `board-review` (CI merah) atau manual (drag di UI). Task yang branch-nya sudah punya
   PR open dilanjutkan di branch itu (prompt memuat nomor PR + log CI yang gagal), bukan dimulai ulang.
   Komentar GitHub tidak dipakai: semua umpan balik lewat board.

> agy dipanggil headless oleh bridge; `agy-turbo -c` adalah untuk pemakaian manualmu.

---

## 6. Yang DILARANG

- ❌ Menulis ke subfolder tanpa front-matter lengkap.
- ❌ Merujuk ID sumber yang tidak ada (`source_spec: SPEC-999` padahal tak ada filenya).
- ❌ Menandai `done` tanpa bukti di Acceptance Check.
- ❌ Melewati gate (mis. bikin Task dari Spec yang masih `draft`).
- ❌ Membuat jenis ID di subfolder yang salah (US- di dalam `tasks/`).
- ❌ Mengubah ID atau menghapus jejak balik artefak lain.

---

## 7. Sprint (Agile Scrum) — siklus & aturan

**Artefak Scrum:**
- **Product Backlog** (`product-backlog/`) — semua story/backlog/PRD, dinamis, diprioritaskan PO.
- **Sprint Backlog** (`sprints/sprint-NN/`) — subset terpilih untuk sprint berjalan; **tetap** selama sprint.
- **Increment** — hasil task yang Done (punya Report + bukti).

**Event Scrum (dipetakan ke mesin kita):**
1. **Sprint Planning** — KiroCrew pilih item dari Product Backlog → buat Spec+Task di `sprint-NN/`, set Sprint Goal di `SPRINT.md`.
2. **Daily** — poller cron KiroCrew men-scan task, jalankan yang `assignee: agy`.
3. **Sprint Review** — KiroCrew verifikasi Report tiap task vs Acceptance + DoD.
4. **Retrospective** — catatan perbaikan proses (opsional, di `SPRINT.md`).

**Aturan sprint:**
- Sprint **sekuensial mulai 01**, tidak melompat. Sprint baru = `sprint-manager.py new NN`.
- Hanya **satu sprint aktif** pada satu waktu (yang `status: active`). Sisanya archived.
- Tiap sprint punya **Sprint Goal + kategori** (Foundation → Core → Integration → Hardening → Release, default; PO boleh ubah).
- **Definition of Done sprint** mengikat semua task-nya (lihat `SPRINT.md`).

## 8. Tutup Sprint, Carry-Over & Archive

**Kapan sprint ditutup:** saat **semua** task sprint `status: done` (Increment lengkap),
ATAU PO memutuskan sprint berakhir (time-box habis).

**Urutan tutup (dijalankan `sprint-manager.py close NN`):**
1. **Carry-over dulu** — setiap task yang **belum** `done` disalin ke sprint berikutnya
   (`sprint-(NN+1)/tasks/`), status di-reset ke `todo`, diberi `carried_from: sprint-NN`.
   Salinan asli tetap tinggal di sprint yang diarsip (untuk histori). Jadi tidak ada
   pekerjaan yang hilang — yang belum selesai otomatis ikut sprint berikutnya.
2. **Tandai `status: closed`** di `SPRINT.md` + isi tanggal `end`.
3. **Pindahkan seluruh folder** `sprints/sprint-NN/` → `archive/sprint-NN/`.

**Tujuan:** sprint berjalan (aktif) selalu **bersih** — hanya berisi pekerjaan sprint
itu. Yang sudah selesai masuk arsip; yang belum selesai pindah ke sprint depan. Tidak
ada task menggantung yang membingungkan sprint aktif.

> Carry-over = inti Scrum: sprint time-boxed, pekerjaan yang tak selesai **tidak**
> memperpanjang sprint — ia kembali ke backlog/sprint berikutnya untuk diprioritaskan ulang.

---

_Versi 2 — 2026-10-12. Diturunkan dari konvensi Jira (user story, INVEST, acceptance
criteria, DoD) + Confluence (PRD, tech/API spec, report) + Scrum (sprint, Product/Sprint
Backlog, Increment, DoD, carry-over). Lihat `TEMPLATES.md` untuk format tiap jenis,
`sprint-manager.py` untuk kelola sprint._

## 9. Amandemen 2026-10-29 — Rust bahasa tunggal (A1–A7)

> Dasar: `galleon-fleet/standard-docs/decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md`, ADR-0018. Diterapkan oleh TASK-057. Aturan lain di dokumen ini tetap berlaku; bila bertentangan, bagian ini yang berlaku. Sumber asli: `RULES-amendment-2026-10-29.md`.

### A1. Bahasa produk inti (sisipkan sebagai aturan baru di §7)
- `galleon-fleet` adalah produk inti dan **hanya** berisi Rust (crates workspace + `apps/tauri`) dan UI Web (TypeScript di `web/`). Tidak ada file `*.go`, `go.mod`, `go.sum`, `go.work` baru sejak TASK-056 (`scripts/ci/check_no_go.sh diff`) dan tidak ada sama sekali sejak TASK-091 (`full`).
- Add-on / kebutuhan lain boleh ditulis dalam Go **di repository terpisah**, dan hanya berintegrasi lewat kontrak publik (ODR-30): HTTP/WS gateway Rust dengan token pairing (rute di `standard-docs/tech-standart/api-contracts/consumer-inventory.md`), MCP, atau plugin WASM `galleon:plugin@1.0.0` (`wit/v1/`). Tidak boleh ada gRPC internal, FFI, SDK/proto Go di repo core, atau berbagi file data dengan `galleon-fleet`.
- Kontrak dimiliki gateway Rust. Perubahan bentuk respons rute berkonsumen wajib disertai pembaruan test kontrak/snapshot (TASK-064, TASK-081) di PR yang sama.

### A2. Ukuran task (perketat §3 dan §7)
- Satu task = satu PR = **≤ 1 jam** kerja agent. Deskripsi task memuat `BRANCH: testing -> feat/<unik>`, `Alokasi pengerjaan: <= 1 jam`, dan (bila ada) `PRASYARAT (DEPENDENCY): TASK-xxx`.
- Branch **wajib** diawali `feat/` — `tools/agy-bridge/board_agy_bridge.py::_expected_branch` hanya mengenali `feat/...`; tanpa itu auto-unblock (`board_switch.py`) tidak pernah terpicu.
- Bila pelaksana menilai task > 1 jam, ia **tidak berhenti tanpa PR**: bridge hanya menerima hasil bila branch ter-push dan PR terbuka (`board_agy_bridge.py::_verify_agy_delivered`); tanpa itu task jatuh ke `blocked` dan hanya di-retry `MAX_AUTO_RETRY=3` kali (`board_switch.py::unblock`), lalu menunggu tombol retry manual. Pelaksana mem-push bagian yang sudah hijau, membuka PR, menulis bagian 'Sisa pekerjaan' di deskripsi PR, dan menandai test yang belum beres `#[ignore = "<TASK-id> sisa"]`. Lead membuat task lanjutan dari deskripsi PR itu (bukan memperpanjang task).
- `PRASYARAT` hanya efektif bila task prasyarat berada di **sprint aktif yang sama** (`board_switch.py::unblock` hanya membaca sprint aktif). Task pertama sebuah sprint dibuat `todo`; prasyarat lintas-sprint ditegakkan oleh aktivasi sprint (A3).

### A3. Status sprint `planning` dan aktivasi (tambahan §5 dan §7)
- `SPRINT.md` boleh berstatus `planning`: sprint disiapkan lebih awal dan **tidak dijalankan** bridge (`_sprint_is_active` hanya menerima `active`).
- Selama `planning`, PRD boleh `in-review` dan SPEC boleh `draft` walaupun task sudah ditulis. Ini pengecualian terbatas dari gate §1 ("Spec approved → Task") **hanya** untuk sprint `planning`.
- Checklist aktivasi (Scrum Master, sebelum mengganti `planning` → `active`):
  1. Sprint sebelumnya `closed`, dan semua task-nya `done` (ingat: `sprint-manager.py close NN` meng-carry-over task belum selesai ke sprint berikutnya).
  2. PRD sumber `approved` (Achmad); SPEC sprint ini `approved` (Lead).
  3. Pertanyaan terbuka PRD yang relevan dengan sprint dijawab atau default-nya diterima tertulis.
  4. `python3 validate.py --all` tidak menambah error dibanding sebelum aktivasi.
  5. Isi `start:` dan `end:` di front-matter.

### A4. Pengecualian urutan sprint (tambahan §7)
- Aturan "sekuensial, tidak melompat" tetap berlaku untuk **nomor** sprint, dan itu juga perilaku otomatis: `sprint-manager.py auto` (timer `board-sprint`) menutup sprint yang semua task-nya `done` lalu mengaktifkan sprint-NN+1 yang berstatus `planning`, **tanpa** memeriksa §A3 (PRD/SPEC `approved`). Karena itu SPEC sprint berikutnya sudah harus `approved` sebelum sprint berjalan selesai.
- Mendahulukan sprint bernomor lebih besar (mis. Sprint 15 setelah Sprint 10) **tidak otomatis**. Prosedur: sebelum Sprint 10 ditutup, ubah `status: planning` pada `sprints/sprint-11/SPRINT.md` menjadi `status: hold` (hanya `planning` yang diaktifkan otomatis, `hold` dilewati); setelah Sprint 10 tertutup, Owner mengubah Sprint 15 menjadi `active` dan mengisi `start`/`end`, dengan satu baris alasan di "Langkah Owner"; setelah Sprint 15 tertutup, Owner mengembalikan sprint-11 menjadi `active` secara manual. Default program ini tetap berurutan 09 → 15.
- Tetap hanya satu sprint `active` pada satu waktu.

### A5. Bukti di Report (perketat §4)
- RPT task kode wajib menyalin output **asli** dari perintah verifikasi yang tertulis di task (mis. `cargo nextest run …`, `cargo clippy … -D warnings`, `npm test`), termasuk ringkasan jumlah test. Klaim tanpa output = `partial`.
- Bila toolchain tidak tersedia di mesin pelaksana, tulis itu di RPT dan status `partial`; jangan menulis "lulus".

### A6. CI lokal Owner
- GitHub Actions dinonaktifkan; gate nyata adalah `~/Apps/dev-ci` (`.github/workflows/ci.yml:3–5`). Script gate baru yang ditambahkan task (`check_no_go.sh`, `check_production_unwrap.py`, `brand_gate.sh`) harus juga didaftarkan Owner di `gates.sh`; task mencatat langkah ini di RPT.
- **Gate `Test` berstatus advisory** (`~/Apps/dev-ci/repos/galleon-fleet/gates.sh`, daftar `LIST`: `Test|heavy|none|25|1`; keputusan Owner 2026-10-17). Akibatnya test yang gagal **tidak** memblokir auto-merge ke `testing`, sehingga janji ODR-29 ("kontrak berubah tanpa snapshot = CI merah") belum ditegakkan. Disarankan sebelum TASK-059 merged: tambahkan gate non-advisory `Contract` yang menjalankan `cargo nextest run --locked -p galleon-gateway -p galleon-fleet-core` (cakupan sempit, bukan seluruh workspace).
- **Tidak ada lane Go di `gates.sh`** (tidak ada `go test`/`go vet`), dan `has_rust_changes` hanya melihat `*.rs`/`Cargo.toml`/`Cargo.lock`. PR yang hanya mengubah `engine/*.go` (TASK-055) lolos Required Gate tanpa satu pun test Go. Karena itu RPT TASK-055 wajib memuat output `go test` asli (A5).
- PR yang hanya mengubah Dockerfile/workflow (TASK-049, TASK-050) juga tidak menjalankan gate Rust; bukti berasal dari RPT (`cargo check -p galleoncode -p galleonrelay`).
- `agy-bridge.service` memakai `PATH` sendiri. `rg`, `node`, `npm` hanya ada di linuxbrew, jadi `/home/linuxbrew/.linuxbrew/bin` **ditambahkan di akhir** `PATH` unit tersebut (2026-10-29); perintah verifikasi di task boleh memakai `rg`. `cargo-nextest` ditemukan lewat `$CARGO_HOME/bin`.

### A7. Penutupan sprint
- `sprint-manager.py auto` menutup sebuah sprint hanya bila **semua** task-nya `done`, termasuk task berassignee `kirocrew`. Task milik KiroCrew tidak diambil bridge; Lead wajib menandainya `done` (dengan RPT) agar sprint tidak berhenti diam-diam.
- Setelah sprint ditutup, sprint-NN+1 `planning` otomatis menjadi `active` (lihat A4); pastikan PRD/SPEC-nya `approved` dan Owner sudah menjawab pertanyaan terbuka yang relevan sebelum itu.
