---
id: sprint-04
type: sprint
goal: Verifikasi menyeluruh ketahanan dan integritas Galleon Fleet melalui End-to-End (E2E) testing berbasis data nyata dan socket riil tanpa mockup
category: Hardening
status: closed
start: 2026-10-22
end: 2026-10-27
author: kirocrew
---
# Sprint 04 — Hardening & End-to-End Testing (Zero-Mock Verification)

> **Sprint Goal:** Membangun dan mengeksekusi suite pengujian End-to-End (E2E) menyeluruh pada Galleon Fleet yang menguji integrasi lintas subsistem (Gateway REST/WS, Konfigurasi & Drift, Channel Webhook/Egress, dan Persistence Memory) menggunakan socket TCP aktual, berkas filesystem fisik, signature kriptografi nyata, dan database SQLite riil pada disk tanpa data mockup (kecuali fallback default value resmi sistem).

## Alur Kerja & Batching (Maksimal <= 1 Jam per Sub-task)
1. **TASK-030 (done, agy):** E2E-01: Verifikasi Gateway REST API & WebSocket Protocol Lifecycle (Real TCP Socket `127.0.0.1:0`)
2. **TASK-031 (done, agy):** E2E-02: Verifikasi Config Mutation, Atomic Disk Persistence & Live Drift Detection (Real Filesystem) *(menunggu PR TASK-030 merged)*
3. **TASK-032 (todo, agy):** E2E-03: Verifikasi Channel Ingress Signature & Sandbox Outbound Egress Enforcement (Real Network Socket) *(menunggu PR TASK-031 merged)*
4. **TASK-033 (blocked, agy):** E2E-04: Verifikasi Multi-Agent Session Continuity & SQLite Memory Persistence (Real Database File) *(menunggu PR TASK-032 merged)*

## Definition of Done (DoD) Sprint Ini
- [ ] Seluruh task (TASK-030 s.d. TASK-033) berstatus `done` dengan Report (`reports/RPT-xxx.md`) lengkap bukti nyata.
- [ ] Pengujian E2E membuktikan integrasi nyata tanpa menggunakan data mockup atau stubbing transport.
- [ ] `cargo check --tests` lolos 0 error pada seluruh crate yang disentuh.
- [ ] `cargo nextest run --locked` pada suite test E2E lulus 100%.
- [ ] Seluruh PR dibuka ke branch `testing` dengan CI `dev-ci` Required Gate berstatus hijau.

## Referensi & Pedoman
- Spesifikasi Teknis: `specs/SPEC-005.md`
- Backlog Item: `product-backlog/backlog/BL-005.md`
- User Story: `product-backlog/stories/US-003.md`
- Standard Testing Docs: `galleon-fleet/standard-docs/foundation/03-build-test-ci-release.md`
