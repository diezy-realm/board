---
id: sprint-01
type: sprint
goal: Fondasi — setup board, konvensi kerja, dan koordinasi KiroCrew ⇄ agy
category: Foundation
status: active
start: 2026-10-12
end:
author: kirocrew
---
# Sprint 01 — Foundation

> **Sprint Goal:** Membangun fondasi papan kerja bersama + alur koordinasi dua
> mesin, sehingga sprint-sprint berikutnya bisa mengeksekusi fitur produk.

## Kategori Sprint (sekuensial / incremental)
| Sprint | Kategori | Fokus |
|--------|----------|-------|
| 01 | **Foundation** | Setup, konvensi, infrastruktur koordinasi |
| 02 | **Core** | Fitur inti produk (vertical slice pertama) |
| 03 | **Integration** | Integrasi antar-komponen, bridge, data flow |
| 04 | **Hardening** | Test, keamanan, perbaikan bug, performa |
| 05 | **Release** | Rilis, dokumentasi, polish akhir |

> Kategori default yang bisa Achmad ubah. Sprint baru dibuat berurutan, tidak melompat.

## Definition of Done (DoD) — Sprint ini
- [ ] Pekerjaan selesai sesuai `acceptance` di task
- [ ] Ada Report (`reports/RPT-xxx.md`) dengan Cek Penerimaan + bukti
- [ ] Report lolos validator
- [ ] (jika kode) perubahan ter-commit / ter-push, bukan hanya lokal

## Sprint Backlog
Task di `tasks/`, spec pendukung di `specs/`, hasil di `reports/`.

## Aturan tutup sprint & carry-over
Lihat `../../RULES.md` §8. Saat semua task `done` → sprint `closed` → folder dipindah
ke `archive/sprint-01/`. Task yang belum `done` di-carry-over ke sprint berikutnya.
