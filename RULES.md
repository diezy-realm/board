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
