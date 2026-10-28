# Amandemen TEMPLATES.md — 2026-10-29

> Diterapkan ke `TEMPLATES.md` oleh TASK-057. Dasar: `RULES-amendment-2026-10-29.md`.

## T1. Template baru `SPRINT.md`
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

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-xxx (todo, agy):** <judul>
2. **TASK-yyy (blocked, agy):** <judul> — menunggu PR TASK-xxx merged

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task `done` dengan Report berisi output verifikasi
- [ ] Seluruh PR ke `testing` dengan CI `dev-ci` hijau

## Langkah Owner
- <langkah di luar repo, mis. gates.sh>

## Referensi & Pedoman
- Spec / Backlog / PRD / Keputusan
```

## T2. Task JSON — isi wajib `description`
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

## T3. Report — Bukti
Di bagian `## Bukti (Evidence)` tambahkan baris:
```markdown
- Output perintah verifikasi (salin apa adanya, bukan ringkasan): <blok kode>
```

## T4. Template keputusan di `galleon-fleet`
- `standard-docs/templates/template-odr.md`: bagian Tier menjadi 3 tier (Desktop shell / Rust Core / UI Web) + baris "Add-on Go/bahasa lain (repo terpisah)". Versi siap pakai ada di paket: `galleon-fleet/standard-docs/templates/template-odr.md`.
- `standard-docs/templates/template-adr.md`: Konteks "3-tier architecture … Rust bahasa tunggal (ADR-0018)". Versi siap pakai: `galleon-fleet/standard-docs/templates/template-adr.md`.

## T5. Task yang tidak muat 1 jam
```text
Jangan berhenti tanpa PR. Push bagian yang sudah hijau, buka PR, tulis 'Sisa pekerjaan' di deskripsi PR;
test yang belum beres: #[ignore = "TASK-xxx sisa"]. Lead membuat task lanjutan.   # lihat RULES amandemen A2
```
