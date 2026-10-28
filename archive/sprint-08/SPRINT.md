---
id: sprint-08
type: sprint
goal: Rename massal crate clawcrew-* ke galleon-*, rename binary & apps zerocode/zerorelay, migrasi config ~/.clawcrew, dan update dokumen normatif
category: Rebranding
status: closed
start: 2026-10-27
end: 2026-10-28
author: kirocrew
---
# Sprint 08 — Mass Renaming & Galleon Fleet Finalization (T3-14 s.d. T3-24)

> **Sprint Goal:** Melakukan rebranding dan rename massal seluruh ekosistem sesuai ODR-16 s.d. ODR-19 dan `naming-map.md`: rename 27 crate Rust (`clawcrew-*` $\rightarrow$ `galleon-*`) berurutan dari crate daun hingga `galleon-runtime` paling akhir, rename binary CLI dan apps (`zerocode` $\rightarrow$ `galleoncode`, `zerorelay` $\rightarrow$ `galleonrelay`), migrasi environment variable `CLAWCREW_*` $\rightarrow$ `GALLEON_*`, migrasi direktori konfigurasi `~/.clawcrew` $\rightarrow$ `~/.config/galleon`, serta sinkronisasi seluruh dokumen normatif dengan preservasi atribusi lisensi upstream ZeroClaw.

## Cakupan Utama & Rencana Tiket (Dev Task 3)
1. **T3-14 / T3-15 (Identity Slug):** Update slug repositori, URL org GHCR `diezy-realm/galleon-fleet`, dan package metadata root.
2. **T3-16 (Apps & Binaries):** `git mv apps/zerocode apps/galleoncode` dan `apps/zerorelay apps/galleonrelay` dengan preservasi git history.
3. **T3-17 (RB-21 Crate Renaming):** Rename berseri bawah-ke-atas 27 crate (`clawcrew-api`, `clawcrew-config`, ..., `clawcrew-runtime` paling terakhir) dengan verifikasi `cargo check --workspace` di setiap langkah.
4. **T3-18 (RB-22/23 Strings & Env):** Pembersihan string internal, migrasi env `CLAWCREW_*` $\rightarrow$ `GALLEON_*` tanpa dual-read alias, dan automigrasi path user `~/.clawcrew` $\rightarrow$ `~/.config/galleon`.
5. **T3-19 (RB-30 Normative Docs):** Update referensi normatif di `AGENTS.md`, `CLAUDE.md`, standard-docs dengan preservasi mutlak atribusi lisensi ZeroClaw di `LICENSE` dan `NOTICE`.

## Dependensi & Prasyarat
- **Prasyarat Mutlak:** Sprint 01 s.d. Sprint 07 harus berstatus `done` 100%. (Hard rule: `clawcrew-runtime` tidak boleh di-rename sebelum strangler T3-05 tuntas).
