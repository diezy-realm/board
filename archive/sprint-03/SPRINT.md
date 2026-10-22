---
id: sprint-03
type: sprint
goal: Dekomposisi file produksi gateway raksasa >2000 baris (T3-04) untuk memantapkan arsitektur sebelum strangler runtime & rename massal
category: refactoring
status: active
start: 2026-10-22
end:
author: kirocrew
---
# Sprint 03 — Dekomposisi File Raksasa Gateway (T3-04 / SAFE RF-A)

> **Sprint Goal:** Memecah 3 berkas produksi monolitik gateway yang melebihi batas 2.000 baris (`api_config.rs` 4.9k LOC, `ws.rs` 4.2k LOC, dan `api_sections.rs` 2.4k LOC) menjadi submodul direktori terstruktur tanpa mengubah kontrak API dan tanpa breaking changes, guna menyelesaikan seluruh mandat T3-04 (BR-C7) sebelum melangkah ke ramping modul runtime (T3-05).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-027 (todo, agy):** Dekomposisi `api_config.rs` (4.940 LOC) → `api_config/`
2. **TASK-028 (blocked, agy):** Dekomposisi `ws.rs` (4.259 LOC) → `ws/` (menunggu PR TASK-027 merged)
3. **TASK-029 (blocked, agy):** Dekomposisi `api_sections.rs` (2.413 LOC) → `api_sections/` (menunggu PR TASK-028 merged)

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-004.md`
- Backlog Item: `product-backlog/backlog/BL-004.md`
- User Story: `product-backlog/stories/US-002.md`
- Master Roadmap: `reference/dev-task-3/README.md` (Tiket T3-04)
