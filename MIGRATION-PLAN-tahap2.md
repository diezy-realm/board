# Rencana Migrasi standard-docs → board (Tahap 2) — siap-eksekusi

> Dokumen rencana. Status tiap blok: **SIAP** (tinggal jalankan) / **MENUNGGU** (ada
> gate). Disusun 2026-10-12 berbasis verifikasi isi nyata (bukan asumsi).
> Sudah selesai sebelumnya: research/backlog/product-research/governance (tahap 1),
> refactoring-rust plan + ADR (tahap 1b). Yang tersisa di bawah.

## Prinsip
- `standard-docs/` = **landasan baku** (ADR/ODR, tech-standart, product, foundation, templates, files).
- `~/Apps/board/` = **pekerjaan berjalan** (active) + **arsip** (sprint-done / superseded).
- Pindah pakai `git mv`/copy+`git rm`, selalu tinggalkan **stub README "DIPINDAH →"**.
- JANGAN pindah sepotong dari satu rantai SSOT (membelah lane = ambigu).

---

## BLOK A — `roadmap/` → board (REFERENSI saja) · status: SIAP

**Keputusan Owner (2026-10-11):** roadmap dipindah **apa adanya sebagai dokumen
referensi**, BUKAN dikonversi jadi task JSON Kanban. Alasan: 150 tiket lane masih
mentah, dan dev-task-2/3 (yang menyerapnya) belum ikut pindah — konversi sekarang
akan membelah SSOT.

**Target:**
```
board/product-backlog/roadmap-lanes/
  R-rust.md  G-go-engine.md  U-ui-desktop.md  P-platform-release.md
  D-docs-hygiene.md  N-rename-and-legacy-cleanup.md  PR-plan.md  README.md
```

**Langkah eksekusi (saat diberi aba-aba):**
1. `copytree standard-docs/roadmap → board/product-backlog/roadmap-lanes`; `git add` di board.
2. `git rm -r standard-docs/roadmap` di galleon; stub README "DIPINDAH →" di lokasi lama.
3. **Update 3 rujukan config** (roadmap/PR-plan.md kini di board):
   - `AGENTS.md` baris 35 & 77 — ganti `standard-docs/roadmap/PR-plan.md` → catatan "PR-plan ada di `~/Apps/board/product-backlog/roadmap-lanes/PR-plan.md`".
   - `.gemini/steering.md` baris 17 & 194 — idem.
   - `docs/README.md` baris 16 — idem.
4. Cek link relatif intra-roadmap (lane saling taut) tetap nyambung (pindah sebagai 1 folder → aman).

**Risiko:** rendah. roadmap tidak dirujuk CI gate (terverifikasi). Hanya 3 file config + referensi dev-task-3 yang menyebut roadmap (dev-task-3 tetap, jadi rujukannya jadi lintas-lokasi — catat di stub).

---

## BLOK B — `dev-task-2` + `dev-task-3` → board · status: MENUNGGU (gate tim lain)

**Gate wajib (tidak bisa dilewati):** dev-task-2/3 dikerjakan **tim lain di mesin
terpisah**; PR #18 masih OPEN, checkbox berubah harian. Eksekusi HANYA setelah:
- (a) Owner konfirmasi tim selesai/setuju pindah, ATAU
- (b) PR #18/#19 merged & 5 sprint aktif ditutup.

**Rantai SSOT (jangan dibelah):**
```
roadmap/ (mentah) → dev-task-2/ (9 sprint, rekonsiliasi) → dev-task-3/ (5 sprint aktif, konsolidasi = SSOT kerja kini)
```

**Target (saat gate hijau):**
```
board/sprints/sprint-02-dev-task3/        ← dev-task-3 jadi sprint board AKTIF nyata
  SPRINT.md (goal dari dev-task-3)
  tasks/ specs/ reports/   (konversi 5 sprint aktif → task JSON, atau simpan md referensi dulu)
board/archive/sprint-done/
  dev-task-2-raw-9-sprints/               ← dev-task-2 UTUH sebagai jejak rekonsiliasi
  (4 sprint done sudah di board/archive/sprint-done/ via tahap arsip)
```

**Langkah eksekusi (saat gate hijau):**
1. Konfirmasi `git status` dev-task-2/3 bersih di mesin tim (tak ada WIP uncommitted).
2. dev-task-3 → `board/sprints/sprint-02-dev-task3/`; tulis `SPRINT.md` (goal = konsolidasi).
   - Opsi konversi task: (a) tiap tiket → `TASK-NNN.json` validator-compliant, atau
     (b) simpan sprint md sebagai referensi + buat task JSON hanya untuk item yang
     benar-benar dieksekusi via board. **Rekomendasi: (b)** — hindari konversi 32 tiket sekaligus.
3. dev-task-2 9 sprint → `board/archive/sprint-done/dev-task-2-raw-9-sprints/` (jejak).
4. Hapus duplikasi: setelah dev-task-3 jadi SSOT board, dev-task-2 cukup arsip.
5. Update `AGENTS.md` baris 35 & 77 + `.gemini` rujukan `dev-task-*/README.md`.
6. **JANGAN** jalankan sampai gate (a)/(b) terpenuhi.

**Risiko:** TINGGI tanpa gate (tabrakan kerja tim). Dengan gate: sedang (butuh update rujukan config + konversi task).

---

## BLOK C — Arsip & sprint-done · status: SIAP (plan terpisah, lihat sesi arsip)
`execute-done/` (3 fase) + `archive/` (7 subfolder) → `board/archive/{sprint-done,superseded}`.
Aman kapan saja (murni historis). Detail di diskusi arsip sebelumnya.

---

## Plan update tampilan board (mengikut struktur di atas)
1. **View ke-3 "🗄 Arsip"** — grup collapse: Sprint Done · Superseded · (nanti) raw-reconciliation dev-task-2.
2. **Filter "sembunyikan archived"** default di view Status/Alur — papan aktif selalu bersih.
3. **Badge `lane: R/G/U/P/D/N`** di kartu (saat roadmap dikonversi, jika pernah) + filter per-lane.
4. **Indikator SSOT aktif** di header — tandai sprint mana yang sedang dikerjakan.
5. **Loader** `load_archive()` + `render_archive()` — pola sama `render_board`, nol dependency.

---

## Ringkas gate
| Blok | Status | Penghalang |
|------|--------|-----------|
| A roadmap (referensi) | **SIAP** | hanya butuh aba-aba Owner |
| B dev-task-2/3 | **MENUNGGU** | konfirmasi tim lain / PR #18-19 merged |
| C arsip + execute-done | **SIAP** | hanya butuh aba-aba Owner |

_Versi 1 — 2026-10-12. Simpan di board (bukan standard-docs): ini rencana kerja, bukan landasan._
