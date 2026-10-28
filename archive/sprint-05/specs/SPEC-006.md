---
id: SPEC-006
type: spec
spec_kind: tech
title: Arsitektur Strangler Pattern dan Isolasi Turn Execution clawcrew-runtime ke Engine Go
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Crate `clawcrew-runtime` saat ini masih berukuran sangat masif dan memuat logika bisnis orkestrasi agent, loop percakapan, memory recall, dan tool execution. Hal ini memperlambat proses kompilasi workspace, meningkatkan ketergantungan erat antar-komponen, dan menghalangi target arsitektur hybrid di mana domain logic orkestrasi dipindahkan ke mesin Go (`engine/`).

## Solusi yang Diusulkan (Proposed Solution)
Menerapkan **Strangler Pattern (T3-05 / BR-D1)** secara modular:
1. **Façade Boundary Interface**: Membuat lapisan abstraksi di `clawcrew-runtime` yang mengekspos trait `AgentRunner` dan mendelegasikan eksekusi turn ke gRPC / IPC client menuju Go engine.
2. **Ekstraksi Turn Loop**: Memindahkan perakitan context prompt, token billing, dan evaluasi turn state ke modul `engine/domain/crew`.
3. **Penyusutan Runtime Rust**: Menjadikan crate runtime Rust sebagai *thin adapter* dan membersihkan modul-modul yang redundan.

## Model Data (Data Model)
- Menggunakan protobuf `proto/agent_service.proto` (`StartTurnRequest`, `ExecuteTurnRequest`, `TurnResponse`) untuk kontrak wire gRPC antar-bahasa.
- DTO Rust menerjemahkan event streaming ke format wire WebSocket Axum gateway.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Tulis ulang runtime Go dari nol sekaligus*: Ditolak (pelanggaran prinsip incremental dan risiko downtime/regresi fatal). Pola strangler memungkinkan migrasi per fitur turn.

## Pertimbangan Keamanan (Security Considerations)
- Komunikasi IPC/gRPC lokal dilindungi mTLS loopback atau Unix domain socket permission terisolasi.

## Rencana Pengujian (Testing Plan)
- Uji kesetaraan fungsional: respons turn engine Go harus identik dengan runner Rust pada test fixtures yang sama.
- `cargo check -p clawcrew-runtime` dan `go test ./engine/...`.

## Rollout / Migrasi
Dikerjakan dalam 3 sub-task berantai (TASK-034 s.d. TASK-036).
