---
title: Spec Migrasi board/ ke Plane (Self-Hosted, Community Edition) — Standar Kerja, Bukan Eksekusi
status: research
date: 2026-10-18
author: kirocrew (lead-squad), diskusi dengan Achmad
depends_on: board-devci-refactor-go-symphony-inspired-2026-10-18.md
informs: galleon-fleet (TIDAK TERKAIT produk — ini riset operasional board/ KiroCrew+agy sendiri)
---

# Spec Migrasi `board/` ke Plane — Deploy Sungguhan, Model Disesuaikan

> **Status: SPEC/STANDAR KERJA, BUKAN EKSEKUSI.** Sesuai instruksi Owner 2026-10-18 — dokumen ini
> definisi arsitektur + kontrak kerja, belum ada kode/deploy yang dijalankan. Ini riset INTERNAL
> operasional (board/+agy+dev-ci), BUKAN dokumen produk galleon-fleet.
>
> **Keputusan Owner**: Plane **dideploy sungguhan** (self-hosted, bukan sekadar referensi pola)
> menggantikan file-based board (`product-backlog/`, `sprints/`, markdown+JSON+front-matter),
> dengan model data dan workflow disesuaikan ke sistem kita (Story→Backlog→PRD→Spec→Task→Report,
> gate antar-tahap, assignee kirocrew/agy).

---

## 1. Fakta Plane yang Diverifikasi (2026-10-18, dibaca langsung dari docs resmi + repo)

### 1.1 Edisi dan Lisensi — Pilihan Wajib Sebelum Deploy

| Edisi | Lisensi | Biaya | Kode | Catatan |
|---|---|---|---|---|
| **Community** | **AGPL-3.0** | Gratis, tanpa license key | Open-source penuh, boleh dimodifikasi | **Codebase BERBEDA** dari Commercial — bukan "Commercial dikunci fitur," tapi repo terpisah |
| **Commercial** | Proprietary (closed-source) | Free tier 12 seat/workspace, lalu berbayar (Pro/Business/Enterprise Grid) | Closed-source | Instalasi via `prime.plane.so` (installer berbeda dari Community) |
| **Airgapped** | Proprietary | Enterprise, perlu kontrak | Closed-source, isolated | Tidak relevan — butuh internet-less environment, bukan kebutuhan kita |

**Keputusan default untuk kebutuhan Anda (privat, 1 Owner + 2 "developer" KiroCrew/agy)**:
**Community Edition** — gratis, AGPL-3.0, instalasi lewat `setup.sh` dari repo GitHub (bukan
`prime.plane.so` yang itu jalur Commercial).

**Implikasi hukum AGPL-3.0 yang WAJIB dicatat** [bukan nasihat hukum, baca sendiri teks lisensi
sebelum keputusan final]: AGPL adalah copyleft kuat — modifikasi kode yang **diakses lewat
jaringan oleh pihak lain** (network use) mewajibkan source modifikasi dibuka. Untuk pemakaian
**privat internal** (hanya Anda + 2 agent, tidak diakses publik/pelanggan), ini pada umumnya tidak
memicu kewajiban publish source — TAPI ini bukan nasihat hukum definitif, perlu konfirmasi kalau
rencana ke depan melibatkan akses pihak ketiga.

### 1.2 Model Data Plane (Fakta dari API Reference resmi, dibaca langsung)

Plane API punya struktur jauh lebih kaya dari dugaan awal riset sebelumnya. Entitas inti yang
relevan dipetakan ke model board kita:

| Entitas Plane | Field/kapabilitas kunci | Padanan board kita |
|---|---|---|
| **Project** | 1 workspace bisa banyak project | Bisa 1 project = galleon-fleet |
| **Work Item** (dulu "Issue") | title, description, state, priority, labels, custom properties, links, attachments, comments, activity log | Gabungan Story+Backlog+Task (perlu pemetaan status, lihat §2) |
| **Work Item States** | custom state per project (bukan fixed) | **Cocok 1:1** dengan status kita (`todo/in-progress/blocked/review/done`) — custom state Plane bisa dibuat PERSIS nama status kita |
| **Work Item Types** | custom type + custom schema per type | **Cocok 1:1** dengan jenis artefak kita (Story/Backlog/PRD/Spec/Task/Report) — tiap jenis jadi satu Work Item Type dengan Custom Properties sendiri |
| **Custom Properties** | field tambahan per Work Item Type (text/dropdown/dst) | Pemetaan `source_story`/`source_backlog`/`source_spec`/`acceptance`/`author` dst sebagai Custom Property per Type |
| **Cycles** | time-boxed iteration (= sprint) | **Cocok 1:1** dengan `sprints/sprint-NN/` kita |
| **Modules** | grouping lintas-cycle (fitur/epic) | Cocok dengan konsep `epic` di Story kita |
| **Intake** | issue masuk sebelum di-triage | Bisa dipakai untuk tahap sebelum `Backlog` (mirip "draft idea") |
| **Milestones**, **Estimates**, **Time Tracking** | fitur tambahan | **Di luar kebutuhan kita** — jangan dipakai, hindari over-engineering |
| **Pages** | dokumen wiki per project/workspace | Bisa menampung `RULES.md`/`TEMPLATES.md` sebagai referensi, OPSIONAL |

### 1.3 API dan Integrasi — Fakta Penting untuk Desain Bridge

- **180+ endpoint REST**, terorganisir resource (`/work-items/`, `/cycles/`, `/modules/`, dst),
  format JSON standar.
- **MCP server resmi** (`plane-mcp-server`, MIT license) — artinya KiroCrew (saya) BISA
  berinteraksi dengan Plane lewat MCP tool standar, TIDAK perlu bikin wrapper API custom dari nol
  untuk kebutuhan dasar (create/update/list work item).
- **GAP TERVERIFIKASI** (GitHub issue #9452, dibaca langsung): endpoint archive/unarchive Work
  Item **TIDAK ADA** di REST API publik Community Edition walau SDK resmi (`plane-python-sdk`)
  dan MCP server mempublikasikan kapabilitas itu — artinya **integrasi via SDK/MCP bisa gagal
  404 untuk operasi tertentu** pada instance self-hosted. Ini risiko nyata, bukan hipotetis.
- **Webhook mewajibkan URL publicly accessible** (dilaporkan di forum resmi Plane, konteks
  pertanyaan user soal webhook ke private IP gagal) — **board kita privat/lokal**, jadi webhook
  Plane TIDAK BISA langsung dipakai tanpa reverse-tunnel atau exposure tambahan (risiko keamanan
  baru yang tidak ada di sistem file-based sekarang).
- **Bug dilaporkan**: webhook kadang trigger ganda untuk satu event (GitHub issue #6848) — bridge
  baru WAJIB idempotent (konsisten dengan prinsip Symphony: orchestrator sebagai satu otoritas
  state, bukan percaya event mentah tanpa verifikasi).

### 1.4 Resource & Deploy — REVISI 2026-10-18, Fakta Diverifikasi Langsung dari `docker-compose.yml`

**Koreksi atas tulisan awal §1.4 (yang keliru, berdasar docs Commercial Edition)**: angka
"4GB RAM, Postgres+Redis+MinIO" di versi awal dokumen ini TIDAK AKURAT untuk Community Edition.
Diverifikasi langsung dari `docker-compose.yml` branch `preview` (sumber primer, bukan docs
marketing), 2026-10-18:

**11 container, bukan 4:**

| Service | Peran | Jenis beban |
|---|---|---|
| `web`, `admin`, `space` | 3 app Next.js TERPISAH, **di-build dari source** (`Dockerfile.web`/`.admin`/`.space`) saat deploy pertama | Build time berat x3 |
| `api` | Django REST API | Runtime |
| `worker` (bgworker) | Background job processor | Runtime |
| `beat-worker` | Scheduler/cron internal | Runtime |
| `migrator` | DB migration (one-shot saat startup) | Startup only |
| `live` | Realtime WebSocket service | Runtime |
| `plane-db` | **Postgres 15.7**, `max_connections=1000` | Database |
| `plane-redis` | Valkey (fork Redis) | Cache/queue |
| **`plane-mq`** | **RabbitMQ 3.13 (message broker PENUH)** — bukan cuma Redis seperti diasumsikan awal | Message queue, moving part tambahan |
| `plane-minio` | S3-compatible object storage | File upload |
| `proxy` | Nginx-based reverse proxy, **bind port HTTP+HTTPS langsung ke host** | Networking — risiko exposure, lihat di bawah |

**Host nyata diverifikasi (`resource_status`, 2026-10-18)**: 4 core, **14.3GB RAM tersedia**,
load 0.07/core (hampir idle). RAM **BUKAN bottleneck** — jauh lebih longgar dari asumsi riset
lama ("4-core sudah jenuh"). **CPU tetap jadi titik rawan**: `dev-ci/README.md` eksplisit
`CPUS=3` ("leaving a core for agy/system on this 4-core host") — build awal 3 app Next.js Plane
akan BERSAING LANGSUNG untuk 1 core sisa yang sama dengan compile Rust `dev-ci` dan agy. Ini
**kontensi CPU nyata saat deploy pertama** (build image), bukan risiko runtime steady-state
(setelah image terbuild, 11 container Postgres/Redis/RabbitMQ/MinIO/app yang IDLE jauh lebih
ringan dari saat build).

**Risiko exposure baru**: `proxy` container bind `${LISTEN_HTTP_PORT}:80` dan
`${LISTEN_HTTPS_PORT}:443` — WAJIB dikonfigurasi bind ke `127.0.0.1` saja (konsisten pola
`board-server` yang sengaja private via tailscale, dan `dev-ci` yang containernya tidak publish
port sama sekali). JANGAN biarkan default compose membuka port ke semua interface.

**Dampak ke keputusan deploy**: resource bukan penghalang (RAM longgar), TAPI kompleksitas
operasional NAIK signifikan dibanding asumsi awal — RabbitMQ + MinIO + Postgres adalah 3
stateful service tambahan yang perlu backup/monitoring, di atas yang sudah ada (`dev-ci` Docker
volumes, `board-server` systemd). Ini bahan pertimbangan nyata untuk keputusan terbuka §5 poin 5,
bukan sekadar "cukup RAM-nya atau tidak."

---

## 2. Pemetaan Model Data: board/ (sekarang) → Plane (diusulkan)

| Board sekarang | Plane | Keputusan Pemetaan |
|---|---|---|
| `US-xxx.md` (Story) | Work Item Type "Story" | Custom Property: `epic`, `priority` (Plane native), `author` |
| `BL-xxx.md` (Backlog) | Work Item Type "Backlog" | Custom Property: `source_story` (relasi/link ke Work Item lain), `estimate`, `assignee` (Plane native: assignee user) |
| `PRD-xxx.md` | Work Item Type "PRD" ATAU Plane **Pages** | PRD berisi narasi panjang (Objective/Metrics/Assumptions) — lebih cocok sebagai **Page** daripada Work Item (Work Item untuk item kerja terlacak, Page untuk dokumen) — **keputusan terbuka, lihat §5** |
| `SPEC-xxx.md` | Work Item Type "Spec" ATAU Page | Sama pertimbangan dengan PRD — SPEC-001 yang baru dibuat (addendum, tabel desain) lebih natural sebagai Page |
| `TASK-xxx.json` | Work Item Type "Task" (default Plane) | Custom Property: `source_spec`, `source_backlog`, `acceptance` (list — cek apakah Custom Property Plane support list/array type, **perlu verifikasi teknis**) |
| `RPT-xxx.md` (Report) | **Comment pada Work Item** ATAU Work Item terpisah dengan link | Report = bukti penyelesaian — Plane punya **Work Item Comments** dan **Activity log** native, mungkin LEBIH NATURAL dipetakan ke situ daripada Work Item baru — **keputusan terbuka, lihat §5** |
| `status` (todo/in-progress/blocked/review/done) | **Work Item States** (custom per project) | Buat 5 state ini PERSIS di Plane project settings — Plane States punya kategori (`backlog`/`unstarted`/`started`/`completed`/`cancelled`), map `blocked`→kategori custom atau `started` dengan label berbeda — **perlu verifikasi kategori yang didukung** |
| `sprints/sprint-NN/` | **Cycle** | 1:1, Plane Cycle sudah punya start/end date native (lebih baik dari `SPRINT.md` front-matter manual) |
| `assignee: kirocrew/agy` | Plane **User/Member** (akun asli) atau label | Plane assignee adalah user account — perlu buat 2 "user" (kirocrew-bot, agy-bot) di instance Plane, ATAU pakai label kalau tidak mau provisioning user formal — **keputusan terbuka** |
| `validate.py` (validator front-matter) | **Custom Property required + Work Item Type schema** (native Plane) + webhook/API check tambahan untuk aturan lintas-field (misal "report done wajib ada Acceptance Check") | Sebagian validasi natural ter-cover Plane (required field per Type), TAPI aturan lintas-artefak (`source_story` harus exist) **tidak otomatis** — bridge/automation kita masih perlu logic ini |
| `RULES.md`/`TEMPLATES.md` | Plane **Pages** (dokumentasi) + enforcement lewat Custom Property schema | Isi aturan proses tetap perlu didokumentasikan di Page, enforcement SEBAGIAN pindah ke Plane schema, SEBAGIAN tetap di bridge |

---

## 3. Arsitektur Bridge (Go, Konsisten Keputusan Refactor Sebelumnya)

Plane **menggantikan storage** (file markdown/JSON → Plane DB via API), TAPI **tidak
menggantikan** kebutuhan orchestrator yang sudah didesain di
`board-devci-refactor-go-symphony-inspired-2026-10-18.md`. Plane adalah **Issue Tracker Adapter**
(persis istilah Symphony Section 11) — satu lapisan dalam arsitektur yang sudah dirancang, bukan
pengganti seluruh orchestrator.

```
Orchestrator (Go, SATU otoritas state — sudah didesain)
        │
        ▼
Board Adapter (interface sama seperti sebelumnya, implementasi BARU: PlaneAdapter)
        │
        ▼
Plane REST API (atau MCP server resmi untuk operasi dasar)
        │
        ▼
Plane instance (Docker self-hosted, Community Edition)
```

**Perubahan dari desain sebelumnya**: `Board Adapter` yang tadinya baca/tulis file langsung
(`tasks/*.json`) sekarang **HTTP client ke Plane API** — interface Go-nya (`FetchCandidates`,
`UpdateStatus`, dst) **tidak berubah bentuknya**, hanya implementasinya diganti. Ini mengikuti
prinsip Symphony "Issue Tracker Adapter" yang SENGAJA dibuat kecil dan dapat diganti (Linear ↔
Plane ↔ file-based, semua implementasi dari interface yang sama) — jadi migrasi ini **tidak**
membongkar desain orchestrator yang sudah disetujui, hanya mengganti SATU komponen.

### 3.1 Mengatasi Gap Webhook (publicly-accessible requirement)

Karena board privat/lokal dan webhook Plane butuh URL publik, **jangan pakai webhook sebagai
jalur utama**. Pola yang konsisten dengan desain orchestrator (Symphony-style poll tick, bukan
reaktif murni): **Orchestrator POLL Plane API tiap tick** (seperti sekarang poll file), webhook
jadi OPSIONAL/sekunder kalau nanti ada kebutuhan near-real-time dan risiko exposure sudah
dievaluasi terpisah. Ini **mengurangi risiko baru** (tidak perlu expose port) dengan mengorbankan
latency (polling vs push) — trade-off yang konsisten dengan prinsip "jangan tambah permukaan
risiko tanpa kebutuhan konkret."

### 3.2 Mengatasi Gap API archive/unarchive

Bridge **tidak boleh bergantung** pada endpoint archive/unarchive Work Item (dikonfirmasi tidak
ada di REST API publik Community Edition). Mekanisme "archive sprint" (`sprint-manager.py close`
sekarang) dipetakan ke: pindahkan Work Item ke Cycle "archive" ATAU tandai lewat Custom Property/
label `archived: true` yang DIBUAT SENDIRI — bukan pakai state bawaan `cancelled`/arsip Plane yang
API publiknya belum lengkap.

---

## 4. Standar Kerja (Workflow) — Disesuaikan dari RULES.md

Prinsip dari `RULES.md` yang **DIPERTAHANKAN** (tidak berubah oleh migrasi tool):
1. Gate antar-tahap (Story→Backlog→PRD→Spec→Task→Report) — diimplementasi sebagai **Work Item
   State transition rules**, dicek bridge sebelum mengizinkan API call pindah state (Plane sendiri
   tidak native punya "gate" lintas-type seperti ini — perlu enforcement di bridge).
2. ID stabil (`US-/BL-/SPEC-/TASK-/RPT-` prefix) — Plane Work Item punya ID internal sendiri
   (sequential number per project) + **custom field untuk ID lama kita** selama masa transisi,
   ATAU adopsi penomoran native Plane (`PROJ-123`) sebagai pengganti — **keputusan terbuka §5**.
3. Front-matter wajib → **Custom Property required** per Work Item Type (native Plane, LEBIH KUAT
   dari validator Python kita karena di-enforce di level create API, bukan post-hoc check).
4. Jejak balik (`source_*`) → **Work Item Links** (Plane native, relasi antar Work Item) — ini
   PERBAIKAN NYATA dibanding sekarang: `validate.py` sekarang cuma cek file ada/tidak (dan punya
   bug glob prefix yang sudah diaudit), Plane Links adalah relasi struktural asli di database.
5. "Jangan klaim done tanpa bukti" → Report jadi **Comment + Attachment** pada Work Item Task,
   bridge WAJIB verifikasi comment/attachment ada sebelum izinkan transisi ke state `done` (logic
   port dari `_verify_agy_delivered` yang sudah ada di `board_agy_bridge.py`, bukan dibuang).

---

## 5. Keputusan Terbuka (Perlu Jawaban Owner Sebelum Spec Final)

1. **PRD/SPEC sebagai Work Item atau Page?** Mempengaruhi apakah "approve" PRD/SPEC jadi state
   transition (Work Item) atau sekadar edit dokumen (Page, tidak ada state machine).
2. **Report sebagai Work Item baru atau Comment pada Task?** Mempengaruhi apakah report punya ID
   sendiri yang bisa dirujuk (seperti `RPT-xxx` sekarang) atau melebur ke activity log Task.
3. **Assignee: user account asli (`kirocrew`, `agy` sebagai login Plane) atau label?** User
   account lebih "benar" secara model Plane tapi perlu provisioning; label lebih sederhana tapi
   kurang native (tidak dapat notifikasi/filter assignee bawaan).
4. **ID: pertahankan prefix lama (`US-001`) sebagai custom field, atau pindah penuh ke penomoran
   Plane native (`PROJ-123`)?** Pertahankan = kompatibel mundur dengan referensi lama di dokumen
   lain (banyak dokumen `standard-docs/` merujuk `US-xxx`/`BL-xxx`); pindah penuh = lebih bersih
   tapi semua rujukan lama jadi usang.
5. **Resource**: perlu BENAR-BENAR mengukur beban Plane (Postgres+Redis+storage+app, estimasi 4
   service minimum) berjalan BERSAMAAN dengan `dev-ci` (compile Rust, container CI) di host
   4-core yang sama — SPEC ini TIDAK mengasumsikan itu aman, perlu uji resource terpisah sebelum
   keputusan final deploy produksi.
6. **Migrasi data existing**: US-001/BL-001-003/SPEC-001/TASK-016-018 yang SUDAH dibuat di
   file-based board — dipindah manual ke Plane via API/UI sekali, atau ditulis script migrasi
   satu-kali (one-shot, bukan bagian orchestrator permanen)?
7. **BARU (dari verifikasi §1.4/§6)**: `blocked` dipetakan ke state group `started` dengan nama
   custom "Blocked" — SETUJU, atau ada alternatif lain (misal pakai `triage` group yang belum
   dipetakan sama sekali)?
8. **BARU**: field `acceptance` (list) jadi multi-line text (parse manual di bridge) — SETUJU,
   atau field ini sebaiknya TETAP di luar Plane (tersimpan di deskripsi Work Item sebagai bagian
   narasi, tidak sebagai Custom Property terstruktur)?

---

## 6. Yang Sudah Terjawab vs Yang Masih Terbuka (REVISI 2026-10-18, verifikasi lanjutan)

**Terjawab, dengan sumber primer**:
- **Kategori Work Item State**: Plane punya **6 group FIXED**: `backlog`, `unstarted`, `started`,
  `completed`, `cancelled`, `triage` — nama state DI DALAM tiap group bisa diganti bebas tanpa
  merusak reporting (Boards/charts baca GROUP, bukan nama). **Dampak ke pemetaan kita**: 4 dari 5
  status kita punya pasangan jelas (`todo`→`unstarted`, `in-progress`→`started`,
  `review`→kemungkinan `started` juga dengan nama "Review", `done`→`completed`). **`blocked`
  TIDAK punya group sendiri** — harus dipetakan ke `started` dengan nama custom "Blocked" (secara
  makna: task diblokir masih "sedang berjalan", bukan selesai/batal) — ini KEPUTUSAN DESAIN baru,
  ditambahkan ke §5 sebagai keputusan terbuka #7.
- **Tipe Custom Property**: text, number, dropdown (single/multi-select), boolean, date, member
  picker. **TIDAK ADA tipe array/list bebas**. Field `acceptance` (list kriteria penerimaan Task)
  **tidak bisa** jadi multi-select (itu butuh opsi pre-defined, bukan teks bebas per-task) —
  solusi realistis: **multi-line text field** (satu string, baris dipisah newline, parse manual
  di bridge saat baca/tulis) — BUKAN native list, perlu logic tambahan di `PlaneAdapter`.

**Masih terbuka/belum terverifikasi** (sama seperti sebelumnya, ditambah 1 baru):
- Perilaku pasti MCP server resmi (`plane-mcp-server`) terhadap Community Edition self-hosted —
  ada laporan GitHub issue soal mismatch endpoint (`/work-items/` vs `/issues/`) antara versi SDK
  dan instance self-hosted yang perlu dicek versi mana yang kompatibel sebelum dipakai.
- Prosedur backup/restore Plane self-hosted — SEKARANG LEBIH PENTING setelah temuan §1.4: ada 3
  stateful service (Postgres+RabbitMQ+MinIO), bukan cuma 1 database, jadi strategi backup harus
  mencakup ketiganya secara konsisten (snapshot bersamaan, bukan terpisah-pisah).
- **BARU**: apakah `beat-worker` (scheduler internal Plane) berpotensi tabrakan konsep dengan
  orchestrator Go yang sedang kita desain (keduanya "scheduler") — perlu dipastikan `beat-worker`
  Plane HANYA untuk kebutuhan internal Plane sendiri (reminder email, dst), BUKAN dipakai sebagai
  pengganti tick loop orchestrator kita — kalau tercampur, melanggar prinsip "satu otoritas state"
  yang sudah disepakati.

## 8. Perbandingan Eksternal — Jira, OpenProject, Redmine (2026-10-18, Diminta Owner Sebelum Komit ke Plane)

> **Alasan bagian ini ada**: sebelum komit penuh ke Plane, Owner minta perbandingan nyata ke
> alternatif self-hosted/open-source sejenis, supaya pilihan akhir cocok dengan spek fisik server
> (4-core, 14.3GB RAM, SUDAH ada beban `dev-ci` + agy berjalan), bukan karena Plane kebetulan
> yang pertama diriset.

### 8.1 Jira — TIDAK LAYAK, Dieliminasi di Awal

**Fakta tegas** (dibaca langsung dari sumber, 2026-10-18): *"New Data Center subscriptions for
new customers ended March 30, 2026, for anyone not already committed, the window to stay on
self-hosted Jira has closed."* — **Jira self-hosted (Data Center) SUDAH DITUTUP untuk pelanggan
baru**, bukan sekadar mahal. Bahkan sebelum penutupan ini, rekomendasi resmi Atlassian sendiri
untuk Data Center: minimal **2 VM terpisah, masing-masing 4-thread CPU + 8GB RAM + NVMe +
database terpisah + load balancer** — total kebutuhan jauh melampaui 1 server 4-core yang Anda
punya, bahkan kalau lisensinya masih bisa dibeli. **Jira dieliminasi — bukan opsi, titik.**

### 8.2 OpenProject — Resource Setara atau Lebih Berat dari Plane

| Aspek | Fakta Terverifikasi |
|---|---|
| **Arsitektur** | Puma web process + background worker + Sidekiq-style cron container + PostgreSQL + memcached + Caddy proxy + collaborative editing server — **7 komponen**, mirip kelas dengan Plane (11 container) tapi tanpa RabbitMQ/MinIO terpisah |
| **RAM** | **8GB RAM minimum** dikonfirmasi 2 sumber independen (dev.to deploy guide + openproject.org docs resmi: "roughly 300-400MB RAM PER WORKER", dan jumlah worker bertambah sesuai concurrent user) |
| **Peringatan nyata** | Sumber independen (ramnode.com, bukan vendor): *"Undersize the VPS and the first symptom is the worker container getting OOM-killed during seeding"* — ini bukan hipotetis, ini kegagalan yang dilaporkan terjadi |
| **Kesimpulan** | **Setara atau LEBIH BERAT dari Plane** untuk resource, TIDAK memberi keuntungan dibanding Plane untuk skala kita — tidak ada alasan pindah ke OpenProject kalau sudah mempertimbangkan Plane |

### 8.3 Redmine — JAUH Lebih Ringan, Trade-off di Fitur Modern

| Aspek | Fakta Terverifikasi |
|---|---|
| **Arsitektur** | **Monolitik** — HANYA app server (Ruby on Rails, Puma/Passenger) + 1 database (PostgreSQL/MySQL). **TIDAK ADA** message queue, object storage terpisah, atau multi-service seperti Plane/OpenProject |
| **RAM** | Sumber independen (StackOverflow, laporan nyata): **~80MB RAM** dengan sedikit issue. Rekomendasi VPS minimum untuk deploy produksi: **2GB RAM total** (vs Plane 4GB+ dan OpenProject 8GB) |
| **API** | REST API **native, built-in** (bukan plugin tambahan) — `POST /issues.json`, custom fields, Issue Statuses, Trackers, format JSON standar. **Matang untuk kebutuhan bridge Go** — tidak kalah dari Plane untuk operasi dasar (create/update/list) |
| **Usia & kematangan** | 20+ tahun (rilis pertama 2006) — SANGAT stabil, TAPI konsepnya "Tracker/Issue/Version" generik, **TIDAK punya** Cycles/Modules/Work Item Types modern setara Plane. Pemetaan Story/Backlog/Task/Report HARUS pakai "Tracker" (setara kategori) + Custom Field manual untuk semua yang Plane native (state group, dsb) |
| **Kesimpulan** | **Resource JAUH lebih ringan** (cocok untuk host yang sudah dibagi dengan `dev-ci`+agy), API cukup untuk bridge, TAPI model data lebih primitif — pemetaan Story→Backlog→Spec→Task→Report butuh LEBIH BANYAK kerja manual di sisi bridge (karena Plane sudah native punya Work Item Types+Custom Properties+Cycles yang cocok 1:1, Redmine tidak) |

### 8.4 Tabel Perbandingan Akhir

| Kriteria | Jira | Plane (Community) | OpenProject | Redmine |
|---|---|---|---|---|
| **Bisa dipakai sama sekali?** | ❌ Ditutup untuk baru | ✅ | ✅ | ✅ |
| **RAM minimum realistis** | 2x8GB (tidak relevan, sudah tereliminasi) | ~4GB+ (11 container) | ~8GB (7 komponen) | **~2GB** (monolitik) |
| **Cocok di host 4-core/14.3GB yang SUDAH ada dev-ci+agy?** | — | Ketat tapi mungkin, kontensi CPU saat build awal | **Berat**, risiko OOM saat seeding terkonfirmasi | **Paling longgar** |
| **Model data cocok Story/Backlog/Spec/Task/Report?** | — | **Native cocok** (Work Item Types+Custom Properties+Cycles) | Mirip Plane tapi kurang terverifikasi detailnya | **Primitif**, butuh banyak Custom Field manual |
| **API utk bridge Go** | — | 180+ endpoint, MCP resmi, TAPI ada gap (archive/unarchive 404) | Ada API, belum diverifikasi detail | **Native, matang, 20 tahun stabil** |
| **Kompleksitas operasional (backup, monitoring)** | — | **Tinggi** (Postgres+RabbitMQ+MinIO = 3 stateful service) | Tinggi (Postgres+worker+cron) | **Rendah** (1 app + 1 DB) |

### 8.5 Rekomendasi Revisi (Bukan Keputusan Final — Tetap Milik Owner)

**Sebelum temuan §8 ini**, dokumen ini condong ke Plane karena model data paling cocok. **Setelah
perbandingan nyata**, trade-off-nya jadi eksplisit:

- **Pilih Plane** kalau kecocokan model data (Work Item Types/Cycles/Custom Properties native)
  LEBIH PENTING daripada kesederhanaan operasional — siap kelola 3 stateful service tambahan
  (Postgres+RabbitMQ+MinIO) berdampingan dengan `dev-ci`+agy di host yang sama.
- **Pilih Redmine** kalau **kesederhanaan dan resource rendah** lebih penting daripada kecocokan
  model data sempurna — siap menulis LEBIH BANYAK logic pemetaan manual di bridge Go (Tracker→
  jenis artefak, Custom Field manual untuk tiap field front-matter kita), tapi dapat footprint
  resource yang jauh lebih kecil dan jauh LEBIH SEDIKIT moving part untuk di-maintain.
- **OpenProject dieliminasi** — tidak ada skenario di mana ia lebih baik dari Plane UNTUK
  KEBUTUHAN KITA (resource setara/lebih berat, tidak ada keunggulan model data yang terverifikasi
  mengungguli Plane).

**Pertanyaan keputusan baru untuk Owner (menggantikan sebagian keputusan terbuka §5 lama)**:
model data yang pas (Plane) atau operasional yang ringan (Redmine)? Ini trade-off INTI yang
sebelumnya tidak eksplisit karena spec awal hanya meriset Plane sendirian.

## 9. Sumber Tambahan (§8)

- Plane API Reference (resmi): https://developers.plane.so/api-reference/introduction
- Plane Self-hosting — Editions: https://developers.plane.so/self-hosting/editions-and-versions
- Plane Self-hosting — Docker Compose: https://developers.plane.so/self-hosting/methods/docker-compose
- Plane repo (branch preview): https://github.com/makeplane/plane/tree/preview
- GitHub issue #9452 (gap archive/unarchive API): https://github.com/makeplane/plane/issues/9452
- GitHub issue #6848 (webhook duplicate trigger bug): https://github.com/makeplane/plane/issues/6848
- Forum Plane (webhook ke private IP gagal): https://forum.plane.so/t/webooks-to-private-ips/91
- Riset board sebelumnya: `board-devci-refactor-go-symphony-inspired-2026-10-18.md`
- Jira Data Center penutupan subscription baru: https://plane.so/blog/11-jira-alternatives-you-can-self-host-in-2026
- Atlassian technical prerequisites (2x VM, 8GB RAM masing-masing): https://community.atlassian.com/t5/Jira-Work-Management-Questions/Technical-prerequisites/qaq-p/2857036
- OpenProject deploy guide independen (OOM saat seeding): https://ramnode.com/guides/openproject
- OpenProject scaling docs resmi (300-400MB/worker): https://openproject.org/docs/installation-and-operations/operation/scaling
- Redmine RAM usage nyata (StackOverflow): https://stackoverflow.com/questions/4964533/reducing-redmines-memory-usage-low-hanging-fruit
- Redmine REST API (native, built-in): https://qiita.com/automationse/items/dfcd403d1b2d37b0d8b8, https://github.com/Lerrrtaste/redmine-openapi-specification
