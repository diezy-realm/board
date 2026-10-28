---
id: sprint-07
type: sprint
goal: Tuntaskan sisa isolasi crate channel eksternal (T3-03), OS service installer (T3-20 / BL-10), dan state migration tooling (T3-21 / BL-11)
category: Integration
status: closed
start: 2026-10-27
end: 2026-10-27
author: kirocrew
---
# Sprint 07 — Channel Completion, OS Service & State Tooling (T3-03, T3-20, T3-21)

> **Sprint Goal:** Menyelesaikan isolasi crate channel eksternal yang tersisa (`galleon-channel-*`), membangun command CLI installer OS daemon systemd/launchd tanpa root privilege (`galleon service install/status/uninstall`), dan menyediakan tooling migrasi state (`jobs.db`, memory SQLite WAL mode, config).

## Cakupan Utama & Rencana Tiket (Dev Task 3)
1. **T3-03 (Final Batch):** Ekstraksi sisa channel dari `clawcrew-channels` monolith menjadi independent crates.
2. **T3-20 (BL-10):** Subcommand CLI `service install/status/uninstall` untuk Linux (systemd user unit) dan macOS (launchd plist) dengan hak akses non-root.
3. **T3-21 (BL-11):** Tooling migrasi state SQLite WAL checkpoint dan verifikasi zero data-loss saat upgrade/migrasi host.

## Dependensi & Prasyarat
- **Prasyarat:** Sprint 06 selesai.
- **Memblokir:** Sprint 08 (Rename Massal).
