---
id: SPEC-010
type: spec
spec_kind: tech
title: Hardening terminal outcome dan context propagation strangler_runner.rs
status: approved
source_prd:
author: kirocrew
created: 2026-10-27
---
## Pernyataan Masalah (Problem Statement)
`crates/clawcrew-gateway/src/strangler_runner.rs` adalah titik boundary strangler (gateway Rust -> AgentEngine Go via gRPC `ExecuteTurn`) yang dibangun di T3-05a/T3-05b (TASK-034/035, PR #76/#84, sudah merged ke `testing`). Audit kode langsung (2026-10-27) terhadap commit `a987cc3ef` (head `testing` saat ini) menemukan dua gap konkret pada fungsi penerima stream dan pembentuk request, keduanya di file yang sama:

1. **Terminal outcome ambigu** -- `Ok(None)` (stream gRPC ditutup tanpa event terminal) diperlakukan identik dengan `TurnCompleted` (event sukses eksplisit); keduanya `break` ke kode yang sama yang selalu mengembalikan `AgentTurnSuccess`.
2. **Context window selalu kosong** -- tiga titik pembentukan request (`TurnRequest`/payload serupa) mengisi `context_window: Vec::new()` meski `self.history` sudah menyimpan riwayat percakapan nyata.

## Solusi yang Diusulkan (Proposed Solution)

### Bagian A -- Terminal outcome (BL-084)
Ubah percabangan match pada hasil `stream.message()`:
- `Ok(Some(resp))` dengan `resp.r#type == TurnCompleted` -> tetap jalur sukses, lanjut ke pembentukan `AgentTurnSuccess`.
- `Ok(None)` -- **BARU**: jangan `break` ke jalur sukses. Return `Err(AgentTurnError)` dengan `committed_response: accumulated_response` (pertahankan partial output yang sudah terkumpul) dan pesan error yang menjelaskan "stream AgentEngine ditutup sebelum TurnCompleted diterima" sehingga caller dapat membedakannya dari gRPC transport error biasa (`Err(status)`, tidak diubah).
- Refactor minimal: tambahkan flag boolean lokal (`terminal_event_received: bool`, default `false`, di-set `true` hanya saat `TurnCompleted` diterima) di awal loop. Setelah loop berakhir (baik dari `break` pada `TurnCompleted` maupun dari jalur baru), percabangan terakhir (baris ~351) memeriksa flag ini sebelum membangun `AgentTurnSuccess` -- jika `false`, return error alih-alih sukses. Ini pola paling sederhana (ponytail: satu flag, bukan state machine baru) dan tidak mengubah jalur `Error` event atau `Err(status)` yang sudah benar.

### Bagian B -- Context propagation (BL-085)
**Keputusan desain WAJIB diambil dulu sebelum coding** (lihat Open Question di bawah): apakah `context_window` harus diisi dari `self.history` milik gateway Rust, atau AgentEngine Go sudah memiliki durable session/run store sendiri yang menjadikan field ini sengaja kosong di jalur ini. Spec ini TIDAK memutuskan itu secara sepihak -- implementer WAJIB membaca `engine/app/wire_gen.go`, `engine/src/crew/services.go`, dan listing `engine/pkg/store/sqlite/` untuk konfirmasi ada/tidaknya session store Go yang sudah menangani history sebelum memilih cabang implementasi.
- **Jika Go belum punya session store aktif untuk history turn-level**: isi `context_window` dari `self.history` (serialisasi `ConversationMessage` yang sudah ada ke representasi yang dipahami proto `TurnRequest.context_window: Vec<u8>` -- field sudah ada di struct, tinggal diisi, bukan field baru) dengan batas wajar (mis. N pesan terakhir atau budget token, didokumentasikan di PR).
- **Jika Go sudah punya session store aktif** (misal dibangun sebagian oleh PR #84): `context_window` kosong SAH by design -- tambahkan komentar kode menjelaskan ini dan early-return dari task BL-085 dengan report yang mendokumentasikan temuan, tanpa mengubah kode lebih jauh (hindari membuat riwayat kanonikal kedua yang bersaing dengan punya Go).

## Model Data (Data Model)
Tidak ada schema/entity baru. `TurnRequest.context_window: Vec<u8>` (baris ~372 di file yang sama) sudah ada di struct; perubahan hanya pada ISI yang dikirim, bukan bentuk kontrak.

## Desain API (API Design)
Bukan `spec_kind: api` -- tidak ada endpoint HTTP/gRPC baru. Perubahan terjadi pada logika internal client gRPC `strangler_runner.rs` yang memanggil `AgentEngine.ExecuteTurn` yang sudah ada.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- **State machine penuh untuk lifecycle turn** (ditolak) -- overkill untuk satu fungsi; satu flag boolean sudah cukup untuk membedakan dua kondisi terminal (ponytail: boring over clever).
- **Menduplikasi history di kedua sisi (Rust + Go)** (ditolak keras) -- melanggar Single Source of Truth (AGENTS.md); harus pilih SATU owner.

## Pertimbangan Keamanan (Security Considerations)
- Tidak ada perubahan permission/auth di spec ini.
- Jika `context_window` diisi dari history, pastikan tidak membawa data dari sesi/user lain (scope kebocoran lintas-sesi) -- `self.history` sudah scoped per-instance runner, verifikasi ini tetap benar setelah perubahan.

## Rencana Pengujian (Testing Plan)
- BL-084: unit test mensimulasikan stream mock yang berhenti (`Ok(None)`) sebelum `TurnCompleted` -> assert `Err`; test existing yang mengasumsikan `TurnCompleted` -> `Ok` harus tetap lulus (no regression).
- BL-085: integration test dua-turn yang membuktikan fakta turn pertama tersedia pada turn kedua MELALUI jalur nyata (bukan mock yang menyembunyikan kontrak), ATAU (jika keputusan = Go-owned) test yang memverifikasi Go session store menyimpan & memakai history-nya sendiri.
- `cargo check --workspace` dan `cargo nextest run -p clawcrew-gateway --locked` wajib 100% untuk kedua task.

## Rollout / Migrasi
- Tidak ada migrasi data/schema.
- Kedua task diserialkan (BL-084 dulu, merged, baru BL-085 mulai) karena sama-sama menyentuh `strangler_runner.rs` -- hindari dua PR bertabrakan di file yang sama (lihat AGENTS.md "serialkan penulis beririsan").
- Rollback: revert PR tunggal per task, tidak ada efek silang karena perubahan terisolasi di fungsi yang sama tanpa breaking change kontrak publik.
