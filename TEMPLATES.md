# TEMPLATES — Format Persis Tiap Artefak Board

> Salin template yang sesuai, isi dalam **Bahasa Indonesia**. Field front-matter
> bertanda **(wajib)** diperiksa validator — kurang satu saja, file ditolak.
> ID = prefix + 3 digit urut (contoh `US-001`). Lihat `RULES.md` untuk alur & gate.

---

## 📁 stories/ — User Story  (`US-xxx.md`)

```markdown
---
id: US-001            # (wajib)
type: story           # (wajib, harus "story")
title: Judul singkat  # (wajib)
status: draft         # (wajib) draft | ready | in-backlog | done
epic:                 # nama epic, boleh kosong
priority: medium      # high | medium | low
author: kirocrew      # (wajib) kirocrew | agy | achmad
created: 2026-10-12   # (wajib) YYYY-MM-DD
---
## Story
Sebagai **<peran>**, saya ingin **<aksi>**, agar **<manfaat>**.

## Kriteria Penerimaan (Acceptance Criteria)
- [ ] Diberikan <konteks>, ketika <aksi>, maka <hasil>
- [ ] ...

## Cek INVEST
Independent / Negotiable / Valuable / Estimable / Small / Testable — catatan singkat.

## Tautan
- Backlog turunan: BL-xxx (jika ada)
- Catatan:
```

---

## 📁 backlog/ — Backlog Item  (`BL-xxx.md`)

```markdown
---
id: BL-001                 # (wajib)
type: backlog              # (wajib)
title: Judul               # (wajib)
status: todo               # (wajib) todo | refined | in-progress | review | done
source_story: US-001       # (wajib) ID story asal — file-nya harus ada
estimate:                  # story point, boleh kosong
assignee: unassigned       # kirocrew | agy | unassigned
sprint:                    # nama sprint, boleh kosong
author: kirocrew           # (wajib)
created: 2026-10-12         # (wajib)
---
## Deskripsi
<apa yang dikerjakan, ringkas dan konkret>

## Definition of Done (DoD)
- [ ] <syarat selesai dari sisi PROSES: kode ditulis, test lulus, review, merged>

## Dependencies
- Memblokir / diblokir oleh: BL-xxx (jika ada)
```

---

## 📁 prd/ — Product Requirements Document  (`PRD-xxx.md`)

```markdown
---
id: PRD-001                # (wajib)
type: prd                  # (wajib)
title: Nama fitur/produk   # (wajib)
status: draft              # (wajib) draft | in-review | approved
target_release:            # tanggal target, boleh kosong
owner: achmad              # (wajib) penanggung jawab keputusan
author: kirocrew           # (wajib)
created: 2026-10-12         # (wajib)
---
## 1. Tujuan (Objective)
<kenapa fitur ini ada — kaitannya dengan goal besar organisasi/produk>

## 2. Metrik Keberhasilan (Success Metrics)
| Tujuan | Metrik | Target |
|--------|--------|--------|
|        |        |        |

## 3. Asumsi (Assumptions)
- <asumsi tentang user / batasan teknis / tujuan bisnis>

## 4. Kebutuhan & User Story (Requirements)
| Kebutuhan | User story | Prioritas | Tautan |
|-----------|-----------|-----------|--------|
|           |           |           |        |

## 5. Di Luar Lingkup & Pertanyaan Terbuka (Out of Scope / Open Questions)
- Di luar lingkup: <...>
- Pertanyaan terbuka: <...> → (jawaban + tanggal saat terjawab)
```

---

## 📁 specs/ — Tech Spec / API Spec  (`SPEC-xxx.md`)

```markdown
---
id: SPEC-001               # (wajib)
type: spec                 # (wajib)
spec_kind: tech            # (wajib) tech | api
title: Judul               # (wajib)
status: draft              # (wajib) draft | approved | implemented
source_prd: PRD-001        # ID PRD asal (boleh kosong untuk item teknis kecil, tapi disarankan)
author: kirocrew           # (wajib)
created: 2026-10-12         # (wajib)
---
## Pernyataan Masalah (Problem Statement)
## Solusi yang Diusulkan (Proposed Solution)   # arsitektur, komponen, alur data
## Model Data (Data Model)                      # schema / entity
## Desain API (API Design)                      # WAJIB jika spec_kind: api
#   - Endpoint, method, request/response contoh, kode error
## Alternatif yang Dipertimbangkan (Alternatives Considered)
## Pertimbangan Keamanan (Security Considerations)
## Rencana Pengujian (Testing Plan)
## Rollout / Migrasi
```

---

## 📁 tasks/ — Task  (`TASK-xxx.json`)  ← JSON, bukan markdown

```json
{
  "id": "TASK-001",
  "type": "task",
  "title": "Judul task",
  "status": "todo",
  "assignee": "agy",
  "source_spec": "SPEC-001",
  "source_backlog": "BL-001",
  "description": "Instruksi konkret & berdiri sendiri untuk agent pelaksana. Sertakan path spec/berkas yang relevan.",
  "acceptance": ["Syarat task dianggap selesai (akan dicek di Report)"],
  "report": null,
  "author": "kirocrew",
  "created": "2026-10-12T20:00:00Z",
  "updated": "2026-10-12T20:00:00Z"
}
```

Field **(wajib)**: `id, type, title, status, assignee, description, created`.
`status`: `todo | in-progress | blocked | review | done`. `assignee`: `kirocrew | agy`.

---

## 📁 reports/ — Report  (`RPT-xxx.md`)

```markdown
---
id: RPT-001                # (wajib)
type: report               # (wajib)
title: Judul               # (wajib)
status: done               # (wajib) done | partial | failed
source_task: TASK-001      # (wajib) ID task asal — file-nya harus ada
author: agy                # (wajib) agy | kirocrew
created: 2026-10-12         # (wajib)
---
## Ringkasan (Summary)
<1 paragraf: apa yang dikerjakan + hasilnya>

## Yang Dikerjakan (What Was Done)
- <langkah / perubahan konkret>

## Bukti (Evidence)
- Berkas / commit / PR / path: <...>

## Cek Penerimaan (Acceptance Check)
- [x] <kriteria task terpenuhi? sertakan bukti>

## Masalah Terbuka / Lanjutan (Open Issues / Next)
- <sisa pekerjaan / rekomendasi>
```

---

_Versi 1 — 2026-10-12. Perubahan template harus dibarengi update validator._

## Amandemen 2026-10-29 (T1–T5)

> Diterapkan oleh TASK-057. Sumber asli: `TEMPLATES-amendment-2026-10-29.md`.

> Diterapkan ke `TEMPLATES.md` oleh TASK-057. Dasar: `RULES-amendment-2026-10-29.md`.

### T1. Template baru `SPRINT.md`
`TEMPLATES.md` belum punya template sprint (format selama ini mengikuti `sprints/sprint-04/SPRINT.md`). Tambahkan:
```markdown
---
id: sprint-NN              # (wajib)
type: sprint               # (wajib)
goal: <satu kalimat>       # (wajib)
category: <Governance|Migration|Hardening|...>
status: planning           # planning | active | closed  (planning = disiapkan, tidak dijalankan bridge)
start:                     # diisi saat aktivasi
end:
author: kirocrew
---
# Sprint NN — <judul>

> **Sprint Goal:** <...>

### Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-xxx (todo, agy):** <judul>
2. **TASK-yyy (blocked, agy):** <judul> — menunggu PR TASK-xxx merged

### Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task `done` dengan Report berisi output verifikasi
- [ ] Seluruh PR ke `testing` dengan CI `dev-ci` hijau

### Langkah Owner
- <langkah di luar repo, mis. gates.sh>

### Referensi & Pedoman
- Spec / Backlog / PRD / Keputusan
```

### T2. Task JSON — isi wajib `description`
Tambahkan catatan di bawah template task:
```text
description wajib memuat (urutan bebas):
  Gunakan skill <squad-...>.
  Spec: SPEC-xxx · Backlog: BL-xxx.
  <langkah bernomor, berisi file:line dan perintah verifikasi>
  BRANCH: testing -> feat/<unik>.            # wajib feat/ (bridge _expected_branch)
  Target PR ke branch testing. Alokasi pengerjaan: <= 1 jam.
  PRASYARAT (DEPENDENCY): TASK-xxx (PR merged ke testing).   # hanya bila ada, sprint yang sama
status awal: task pertama sprint = todo; berikutnya = blocked (auto-unblock saat PR prasyarat merged).
```
Field tambahan yang sudah dipakai board dan kini resmi: `role`, `tags`, `source_spec`, `source_backlog`, `notes`, `updated`.

### T3. Report — Bukti
Di bagian `## Bukti (Evidence)` tambahkan baris:
```markdown
- Output perintah verifikasi (salin apa adanya, bukan ringkasan): <blok kode>
```

### T4. Template keputusan di `galleon-fleet`
- `standard-docs/templates/template-odr.md`: bagian Tier menjadi 3 tier (Desktop shell / Rust Core / UI Web) + baris "Add-on Go/bahasa lain (repo terpisah)". Versi siap pakai ada di paket: `galleon-fleet/standard-docs/templates/template-odr.md`.
- `standard-docs/templates/template-adr.md`: Konteks "3-tier architecture … Rust bahasa tunggal (ADR-0018)". Versi siap pakai: `galleon-fleet/standard-docs/templates/template-adr.md`.

### T5. Task yang tidak muat 1 jam
```text
Jangan berhenti tanpa PR. Push bagian yang sudah hijau, buka PR, tulis 'Sisa pekerjaan' di deskripsi PR;
test yang belum beres: #[ignore = "TASK-xxx sisa"]. Lead membuat task lanjutan.   # lihat RULES amandemen A2
```
