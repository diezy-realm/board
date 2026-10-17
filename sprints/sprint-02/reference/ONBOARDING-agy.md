# Onboarding agy — kerja dari board/, bukan standard-docs/ lagi

**Berlaku mulai 2026-10-17.** SSOT kerja aktif (task yang kamu, agy, eksekusi)
berpindah dari `galleon-fleet/standard-docs/decisions/finalize/dev-task-*/`
ke papan ini: **`~/Apps/board/`**.

## Apa yang berubah

| Dulu | Sekarang |
|---|---|
| Baca task dari `standard-docs/decisions/finalize/dev-task-3/README.md` | Baca task dari `sprints/sprint-NN/tasks/TASK-*.json` di board |
| Status tiket di checkbox markdown `[ ]`/`[x]` | Status di front-matter / field JSON (`todo/in-progress/blocked/review/done`) |
| Lapor di dokumen dev-task | Tulis `sprints/sprint-NN/reports/RPT-*.md` dengan bukti (commit/PR/path) |

Dokumen dev-task-2/3 **tetap dibawa** ke `sprints/sprint-02/reference/` sebagai
**bahan baca** (konteks, status historis, dependency), tapi **sumber perintah
kerja** sekarang adalah `tasks/TASK-*.json`.

## Cara kerja (poller `board-agy-bridge`)

1. KiroCrew membuat `tasks/TASK-xxx.json` dengan `assignee: agy`, `status: todo`.
2. Poller cron KiroCrew (`~/.kiro/crew/crons/board_agy_bridge.py`, tiap 5m) men-scan
   `tasks/`. Task `assignee=agy & status=todo` → agy headless (`-p`) dieksekusi.
3. agy menulis `reports/RPT-xxx.md`, lalu task di-set `status: done` + `report: RPT-xxx`.

**PENTING — status `blocked`:** task dengan `status: blocked` (mis. TASK-001/002
di sprint-02) **TIDAK dijalankan** poller. Ini sengaja: T3-02/T3-03 adalah refactor
Rust besar yang tim manusia masih kerjakan di branch `testing`. Jangan jalankan
paralel — tunggu KiroCrew/Owner flip `blocked` → `todo` saat tim selesai, supaya
tidak bentrok merge.

## Aturan branch (dari Owner, 2026-10-17)

```
testing → feat/{nomor-tiket}-xxxx → feat/{sub-nomor-tiket}-xxxx
```
Semua kerja cabang dari `testing`. **Jangan push langsung ke `testing`/`master`.**
Buka PR ke `testing`.

## Baca dulu sebelum menulis ke board

- `~/Apps/board/RULES.md` — alur stage, gate, front-matter wajib (ditolak `validate.py` kalau kurang).
- `~/Apps/board/TEMPLATES.md` — format persis tiap artefak.
- `sprints/sprint-02/SPRINT.md` — goal + status tiket sprint ini.
