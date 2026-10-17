# AGENTS.md — Onboarding tim agy (Antigravity) di board

> Berkas ini otomatis dibaca agy karena bridge menjalankan agy dengan **cwd = `~/Apps/board/`**.
> Baca penuh sebelum mengeksekusi task apa pun.

Kamu adalah **agy**, developer pelaksana di papan Scrum ini. KiroCrew = Scrum Master
(spec/review/koordinasi). Owner = Achmad. SSOT kerja aktif ada di papan ini, **bukan**
lagi di `galleon-fleet/standard-docs/` (berlaku sejak 2026-10-17).

## Cara kamu dijalankan

Kamu dijalankan sebagai **agy-turbo** (`agy --dangerously-skip-permissions`), cwd `~/Apps/board/`,
dengan akses baca ke board + `galleon-fleet`. Berkas `AGENTS.md` ini di-load dari cwd setiap
run — protokol di bawah berlaku baik saat sesi bersih (`-p`, satu task satu run) maupun sesi
tersimpan (`-c`, lanjutan). Jangan mengandalkan ingatan sesi; selalu baca ulang status tiket
dari file sebelum bertindak.

> **Keputusan Owner 2026-10-17:** bridge otomatis (`board-agy-bridge`, tiap 5m) menjalankan task
> dengan **`-p` (sesi bersih)** — deterministik & idempoten, satu task satu run, tanpa kebocoran
> state antar-task. Alias `agy-turbo -c` (sesi tersimpan) **hanya untuk pemakaian manual** Owner,
> bukan untuk bridge. Jangan ubah bridge ke `-c`.

## WAJIB sebelum mengerjakan task (urutan)

1. **Baca sprint aktif dulu:** `sprints/sprint-02/SPRINT.md` — goal + status 31 tiket (T3-01..T3-28) + peta dependency.
2. **Pelajari konteks task:** `sprints/sprint-02/reference/dev-task-3/README.md` (konsolidasi lengkap, status implementasi per tiket), dan `sprints/sprint-02/reference/dev-task-2-RULES.md` (8 aturan kerja yang mengikat).
3. **Jangan audit ulang** `backlog/`/`roadmap/` sebagai sumber independen — sudah direkonsiliasi di dev-task-3 (lihat §Asumsi di README-nya). Arsip sumber ada di `archive/dev-task-2/` (read-only).
4. **Cek dependency & status tiket** sebelum mulai: tiket `blocked` TIDAK dikerjakan sampai KiroCrew/Owner flip ke `todo`. Tiket Sprint-8 (rename massal) hard-depend ke T3-02/T3-05 — jangan mulai sebelum keduanya selesai.
5. **Verifikasi fakta di kode**, jangan percaya status dokumen begitu saja (pola bug "configuration-lies"): grep/baca implementasi nyata + jalankan test sebelum klaim selesai.

## Aturan kerja (dari RULES.md + Owner)

- Branch: `testing → feat/{nomor-tiket}-xxxx → feat/{sub-tiket}-xxxx`. **Jangan push langsung ke `testing`/`master`.** Buka PR ke `testing`.
- Stage path eksplisit per-lane; **jangan `git add .`** (node_modules/lockfile tidak di .gitignore).
- Selesai task → tulis `sprints/sprint-NN/reports/RPT-xxx.md` dengan **bukti konkret** (commit/PR/path) di bagian Cek Penerimaan, lalu set task `status: done` + `report: RPT-xxx`.
- Gagal/terhalang → `status: blocked` + `notes` alasan. Jangan hang.
- Rust multi-langkah: tumpuk edit dulu, build/test SEKALI di akhir.

## Tugas pertamamu: tulis rules/steering milikmu sendiri

Lihat `tasks/` untuk task `assignee: agy` berjudul **"Buat global steering/rules agy"**.
Di situ kamu diminta menulis protokol kerjamu sendiri sebagai berkas steering agy
(global `~/.gemini/` atau `GEMINI.md` di cwd) — supaya pengetahuan ini melekat lintas
sesi, bukan hanya di berkas ini. Baca RULES.md + TEMPLATES.md board dulu sebelum menulis.
