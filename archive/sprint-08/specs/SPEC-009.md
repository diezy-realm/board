---
id: SPEC-009
type: spec
spec_kind: tech
title: Spesifikasi Teknis Rename Massal Ekosistem Galleon Fleet Sesuai ODR-16 s.d. ODR-19
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Setelah seluruh penyusutan runtime (T3-05), retargeting harness (T3-06), dan integrasi platform (T3-03/20/21) selesai, codebase siap untuk rebranding massal ke identitas Galleon Fleet sesuai mandat ODR-16 s.d. ODR-19. Seluruh rujukan nama lama `clawcrew`, `zerocode`, `zerorelay` harus diubah secara bersih tanpa memicu dual-read atau merusak riwayat atribusi lisensi upstream ZeroClaw.

## Solusi yang Diusulkan (Proposed Solution)
Eksekusi sekuensial terstruktur:
1. **Metadata & Slug (T3-14/15)**: Root Cargo.toml package `galleon-fleet`, image `ghcr.io/diezy-realm/galleon-fleet`.
2. **Apps Directory (T3-16)**: `git mv apps/zerocode apps/galleoncode` dan `git mv apps/zerorelay apps/galleonrelay`.
3. **Crates Renaming Bawah-ke-Atas (T3-17 / RB-21)**: Rename 27 crate berurutan berdasarkan topological sort cargo metadata (daun duluan, `clawcrew-runtime` $\rightarrow$ `galleon-runtime` paling terakhir). Verifikasi `cargo check --workspace` di setiap crate.
4. **Environment & Paths (T3-18 / RB-22/23)**: Migrasi `CLAWCREW_*` $\rightarrow$ `GALLEON_*`, `~/.clawcrew` $\rightarrow$ `~/.config/galleon` secara atomik pada boot pertama tanpa fallback dual-read permanen.
5. **Dokumen Normatif (T3-19 / RB-30)**: Update `AGENTS.md`, `CLAUDE.md`, standard-docs. **Preservasi mutlak klausul hak cipta ZeroClaw di `LICENSE` dan `NOTICE`**.

## Model Data (Data Model)
- Skema konfigurasi baru tersimpan di path kanonikal `~/.config/galleon/config.toml`.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Mempertahankan dual-read alias selamanya*: Ditolak (ODR-19), sistem beralih penuh ke Galleon tanpa beban teknis alias ganda.

## Pertimbangan Keamanan (Security Considerations)
- Preservasi lisensi upstream ZeroClaw menjamin kepatuhan hukum open-source MIT/Apache-2.0.
- Skrip migrasi data user tidak melakukan logging terhadap isi kredensial atau token API.

## Rencana Pengujian (Testing Plan)
- `cargo check --workspace` dan `cargo build --workspace` lulus hijau.
- Scanner lisensi memverifikasi atribusi ZeroClaw utuh.

## Rollout / Migrasi
Dikerjakan dalam 5 sub-task berseri: TASK-042 s.d. TASK-046.
