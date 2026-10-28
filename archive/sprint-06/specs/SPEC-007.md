---
id: SPEC-007
type: spec
spec_kind: tech
title: Retargeting Harness Evaluasi Trace LLM dan Penghapusan Subsistem Legacy RPC
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Crate `clawcrew-eval` (2.470 LOC) saat ini bergantung langsung pada instans internal Rust `clawcrew_runtime::agent::agent::Agent` untuk mereplay rekaman trace LLM. Setelah logika turn dipindahkan ke engine Go pada Sprint 05, runner evaluasi harus diarahkan ulang agar mereplay trace melalui interface Go (`StartTurn`/`ExecuteTurn`). Selain itu, subsistem legacy RPC lama di runtime perlu dibersihkan tuntas (T3-08).

## Solusi yang Diusulkan (Proposed Solution)
1. **Eval Runner Retargeting (T3-06 / BR-D2)**:
   - Modifikasi runner di `clawcrew-eval/src/runner.rs` agar mengonsumsi interface client Go engine mock/live turn.
   - Mempertahankan file fixture trace JSON historis tanpa perubahan byte sedikit pun.
2. **Legacy RPC Elimination (T3-08 / BR-D4)**:
   - Menghapus modul `rpc/` lama di runtime dan merefaktor caller yang masih memanggil handler RPC usang.

## Model Data (Data Model)
- Struktur data trace LLM (`tests/support/trace.rs`) tetap kompatibel 100%.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Membuang crate eval*: Ditolak (eval diperlukan untuk verifikasi regresi kualitas model LLM).

## Pertimbangan Keamanan (Security Considerations)
- Menghapus endpoint legacy RPC menutup *attack surface* potensial yang tidak terawat.

## Rencana Pengujian (Testing Plan)
- Menjalankan `cargo test -p clawcrew-eval` dan memverifikasi seluruh replay test lulus.

## Rollout / Migrasi
Dikerjakan dalam 2 sub-task: TASK-037 (eval retarget) dan TASK-038 (RPC cleanup).
