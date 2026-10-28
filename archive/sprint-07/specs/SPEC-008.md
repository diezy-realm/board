---
id: SPEC-008
type: spec
spec_kind: tech
title: Arsitektur Ekstraksi Final Channel, Daemon Service Systemd/Launchd, dan SQLite WAL Migration
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Sebelum rebranding menyeluruh di Sprint 08, ekosistem membutuhkan penyelesaian 3 kebutuhan teknis: pemecahan channel monolith yang tersisa (T3-03), integrasi instalasi service daemon OS tanpa privilege root (T3-20 / BL-10), dan prosedur migrasi state yang aman terhadap database SQLite dengan WAL mode aktif (T3-21 / BL-11).

## Solusi yang Diusulkan (Proposed Solution)
1. **Final Channel Split (T3-03)**:
   - Mengekstrak channel tersisa di `clawcrew-channels` ke crate `galleon-channel-<nama>` mandiri.
2. **OS Service Management (T3-20 / BL-10)**:
   - CLI command `galleon service install/status/uninstall`.
   - Menghasilkan unit systemd user di Linux (`~/.config/systemd/user/galleon.service`) dan launchd plist di macOS (`~/Library/LaunchAgents/`).
   - Daemon berjalan strictly sebagai non-root user.
3. **State Migration Tooling (T3-21 / BL-11)**:
   - Tooling migrasi state mengeksekusi `PRAGMA wal_checkpoint(TRUNCATE)` sebelum menyalin berkas database SQLite (`jobs.db`, memory db), mencegah korupsi `.db-wal`.

## Model Data (Data Model)
- Format unit systemd standar dan launchd property list XML.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Menjalankan service sebagai root*: Ditolak keras (pelanggaran prinsip least privilege).

## Pertimbangan Keamanan (Security Considerations)
- Hak akses elevasi sudo hanya dibatasi saat penulisan service descriptor jika diperlukan, runtime daemon berjalan dengan UID user biasa.

## Rencana Pengujian (Testing Plan)
- Dry-run pembuatan service descriptor dan validasi sintaks systemd-analyze / plutil.
- Simulasi checkpoint WAL dan checksum perbandingan SQLite.

## Rollout / Migrasi
Dikerjakan dalam 3 sub-task: TASK-039 (channels), TASK-040 (service CLI), TASK-041 (state migration).
