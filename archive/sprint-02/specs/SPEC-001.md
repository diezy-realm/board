---
id: SPEC-001
type: spec
spec_kind: tech
title: Jembatan Identitas CrewMember (Go) <-> AliasedAgentConfig (Rust)
status: draft
source_prd:
author: kirocrew
created: 2026-10-18
---
## Pernyataan Masalah (Problem Statement)
`CrewMember` (Go: identitas organisasi — ID/Name/Role/Status/Capabilities, hidup di bawah
Squad→Ship→Fleet) dan `AliasedAgentConfig` (Rust: identitas eksekusi — model_provider,
skill_bundles, mcp_bundles, risk_profile, runtime_profile, SSOT lewat `config.agents.get(alias)`
dipakai konsisten di 15+ lokasi) hidup sebagai **dua sistem identitas paralel yang tidak
terhubung secara struktural**, hanya oleh konvensi penamaan manual.

Dibuktikan [V] 2026-10-18:
- `ExecuteTurnRequest` (`proto/agent_service.proto:149`) hanya bawa `session_id`+`model`
  (string polos)+`messages`+`tools` — tidak ada `agent_id`/`crew_member_id`/`agent_alias`.
- `SopStep.agent: Option<String>` di titik eksekusi (`sop/mod.rs:1200`) hanya dirender jadi teks
  bullet markdown, tidak pernah di-resolve lewat `config.agents.get()`.

Dampak: SOP Constraint/RACI layer yang sudah didesain (`sop-constraint-layer-design.md`,
`RoleRestriction`/`DistinctPerformer`) TIDAK BISA ditegakkan — constraint berbasis role perlu tahu
role mana yang SEDANG eksekusi, tapi `step.agent` tidak pernah benar-benar diresolve jadi identitas
nyata di titik eksekusi.

## Solusi yang Diusulkan (Proposed Solution)
Tiga perubahan kecil, independen secara file, membentuk satu jembatan:

```
CrewMember (Go)                    AliasedAgentConfig (Rust)
┌──────────────────┐               ┌─────────────────────────┐
│ ID, Name, Role    │               │ model_provider           │
│ Status            │               │ skill_bundles            │
│ Capabilities       │               │ mcp_bundles              │
│ AgentAlias (BARU)  │───alias ref──▶│ risk_profile             │
└──────────────────┘   string       │ runtime_profile           │
         │                          └─────────────────────────┘
         │ ExecuteTurnRequest.agent_alias (field proto BARU, optional)
         ▼
   Rust ExecuteTurn handler: resolve config.agents.get(agent_alias)
   kalau ada & valid -> pakai; kalau tidak -> fallback ke `model` lama
```

1. **BL-001**: `ExecuteTurnRequest` proto + field `agent_alias` opsional. Rust handler resolve
   kalau terisi+valid, fallback kalau tidak (backward compatible, tidak breaking).
2. **BL-002**: `CrewMember.AgentAlias string` (Go) + titik panggil `ExecuteTurn` menyertakannya.
3. **BL-003**: `SopStep.agent` di titik EKSEKUSI (bukan render) resolve lewat `config.agents.get()`,
   konsisten dengan pola 15+ lokasi lain yang sudah ada.

Urutan: BL-001 dulu (proto, prasyarat BL-002) → BL-002 (Go, depend BL-001). BL-003 independen,
bisa paralel (file Rust SOP, tidak bersinggungan dengan proto/gateway).

## Model Data (Data Model)
Tidak ada tabel/skema baru. Perubahan field pada struct yang sudah ada:
- `CrewMember` (Go, `engine/src/crew/dto.go`): `+AgentAlias string` (default `""`, omitempty di JSON)
- `ExecuteTurnRequest` (proto): `+optional string agent_alias` (field number menyusul slot kosong
  berikutnya di proto file — cek file sebelum assign nomor pasti, JANGAN reuse nomor terpakai)
- Tidak ada migrasi DB wajib — cek `engine/pkg/store/sqlite/schema.go` apakah `CrewMember`
  diserialisasi ke kolom individual (perlu `ALTER TABLE`) atau JSON blob (tidak perlu migrasi
  skema, cukup field baru di struct Go). **Verifikasi ini bagian dari BL-002, bukan diasumsikan
  di sini.**

## Desain API (API Design)
N/A — ini perubahan field pada API internal (gRPC) yang sudah ada, bukan API publik baru.
Perubahan proto didetailkan di BL-001.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
1. **Resolve di Go, kirim config lengkap ke Rust lewat proto** — DITOLAK. Melanggar boundary yang
   sudah ditetapkan (`01-boundary-policy.md`, ADR 0001: LLM execution SSOT = Rust). Go tidak boleh
   tahu detail provider/skill_bundles.
2. **Lookup table terpisah (Go DB) memetakan CrewMember.ID -> agent_alias, tanpa ubah proto** —
   DITOLAK. Menambah SATU LAGI sumber kebenaran (persis anti-pattern yang `AGENTS.md` root
   larang: "Do not duplicate state... identify the canonical source"). Field langsung di
   `CrewMember` + proto adalah jalur terpendek tanpa state tambahan.
3. **Pindahkan Squad/Ship/Fleet identity SEPENUHNYA ke Rust config** — DITOLAK, scope terlalu besar
   dan melanggar boundary (Go = organisasi/policy, Rust = eksekusi) untuk masalah yang cukup
   diselesaikan di level CrewMember saja.

## Pertimbangan Keamanan (Security Considerations)
- `agent_alias` adalah string internal (bukan secret) — aman dikirim lewat gRPC internal
  (:50052, internal-only per `00-overview.md`).
- Validasi alias HARUS fail-safe (fallback), BUKAN fail-hard, di titik request — mencegah satu
  CrewMember dengan alias salah mem-blokir seluruh turn execution. Validasi fail-LOUD yang lebih
  ketat (reject saat config load) adalah lapisan terpisah, sudah ada presedennya di
  `Config::validate()` ("fails loud on dangling references") — BL-002/BL-003 tidak menduplikasi
  mekanisme ini, hanya memastikan request-time tetap graceful.

## Rencana Pengujian (Testing Plan)
- Unit test Rust: `ExecuteTurn` dengan `agent_alias` valid/invalid/kosong (3 skenario, BL-001)
- Unit test Rust: SOP step dengan `step.agent` valid/invalid alias (2 skenario, BL-003)
- Unit test Go: `CrewMember.AgentAlias` terisi/kosong mempengaruhi payload request (2 skenario,
  BL-002)
- Regression: existing test yang panggil `ExecuteTurn` tanpa `agent_alias` TETAP lulus tanpa ubah
  assertion (bukti backward-compat tidak rusak)
- `cargo nextest run --workspace` + `go test ./engine/...` + `cargo check --workspace` semua hijau
  sebelum PR dibuka

## Rollout / Migrasi
- Tidak ada feature flag diperlukan — field opsional, default behavior tidak berubah untuk
  caller yang belum di-update.
- Urutan deploy: BL-001 (proto+Rust fallback) merge dulu → BL-002 (Go mulai kirim field) → BL-003
  independen kapan saja.
- Tidak ada downtime; tidak ada data existing yang perlu di-backfill (field baru, bukan field
  yang menggantikan data lama).

## ADDENDUM — Crosscheck Archive/Active Sprint (2026-10-18, PENTING: merevisi §Problem Statement)

Diminta Owner: crosscheck SPEC ini terhadap `board/archive/` dan sprint aktif sebelum eksekusi,
untuk cegah redundansi. Hasil crosscheck **mengubah pemahaman masalah secara material** — dicatat
di sini, bukan menulis ulang bagian atas, supaya jejak koreksi terlihat (konsisten pola riset lain
di repo ini: "log koreksi", bukan menghapus kesalahan analisis sebelumnya).

### Temuan 1 — `agent_id` BUKAN tidak ada; ia ada di pintu masuk tapi di-DROP di tengah jalan

Grep ke `archive/execute-done/go-rust-hybrid-engine-bootstrap/api-spec.md` (desain bootstrap
paling awal, sudah archived) menunjukkan `TurnRequest.agent_id = 2 // merujuk ke konfig agent
TOML` **sudah ada sejak desain pertama**. Verifikasi ke kode LIVE sekarang (`engine/src/crew/
services.go`, `dto.go`) membuktikan:

1. `TurnRequest.AgentID string` (`dto.go:6`) — field request masuk, **masih ada**, dipakai di
   `StartTurn` (`services.go:73-87`) untuk fallback (`"primary_agent"`) dan metrics label.
2. **BUG NYATA ditemukan** (`services.go:91-93`): saat `StartTurn` membangun `ExecuteTurnRequest`
   untuk dikirim ke Rust, `Model` di-HARDCODE `"gpt-4o"` — `agentID` yang sudah di-resolve di
   baris 75 **tidak pernah dipakai** untuk menentukan model/provider. `ExecuteTurnRequest` yang
   benar-benar dikirim ke Rust hanya bawa `SessionId`+`Model`(hardcode)+`Messages` — persis temuan
   SPEC ini di bagian atas, TAPI sebabnya bukan "proto tidak punya field," melainkan **Go
   menerima identitas lalu membuangnya sebelum sampai ke Rust**.
3. `UpdateCrewMemberStatus(ctx, crewID, agentID string, ...)` (`interfaces.go:29`) sudah
   memperlakukan `crewID` dan `agentID` sebagai DUA hal berbeda dalam signature yang ada —
   konsisten dengan analisis 3-sumbu-identitas (organisasi vs eksekusi vs runtime) di diskusi
   sesi ini, bukan temuan baru yang perlu didesain dari nol.

### Temuan 2 — Revisi Problem Statement (lebih presisi, scope LEBIH KECIL dari versi awal)

**Rumusan LAMA (bagian atas dokumen ini)**: "tidak ada jalur identitas sama sekali antara Go dan
Rust." INI TIDAK AKURAT — ada jalur masuk (`TurnRequest.AgentID`), masalahnya ia tidak diteruskan.

**Rumusan BARU (akurat, dasar revisi BL-001/002/003)**:
1. `CrewMember` (Go, identitas organisasi) **tidak punya field yang mengisi `TurnRequest.AgentID`
   secara terstruktur** — titik panggil `StartTurn` mengisi `AgentID` dari mana pun secara ad-hoc
   (perlu ditelusuri ULANG di BL-002: cari SEMUA pemanggil `StartTurn`/`TurnRequest{AgentID: ...}`,
   bukan hanya titik yang sudah ditemukan di `ws_server.go:219` dan test).
2. `services.go:91-93` **tidak meneruskan** `agentID` yang sudah di-resolve ke `ExecuteTurnRequest`
   — `Model` hardcode `"gpt-4o"`. **Ini bug konkret siap-perbaiki**, bukan desain baru.
3. `SopStep.agent` (temuan asli, masih valid) tetap benar: di titik render (`sop/mod.rs:1200`)
   hanya jadi teks, tidak resolve ke `config.agents`.

### Dampak ke BL-001/002/003 (REVISI SCOPE, bukan dibuang)

| Backlog | Scope LAMA (keliru sebagian) | Scope BARU (akurat, lebih kecil) |
|---|---|---|
| BL-001 | "Tambah field agent_alias ke proto" (implikasi: proto SAMA SEKALI tidak punya field) | **Proto `TurnRequest` SUDAH punya `agent_id`.** Scope sebenarnya: pastikan `agentID` yang di-resolve `StartTurn` (`services.go:75`) DITERUSKAN ke `ExecuteTurnRequest` (hapus hardcode `"gpt-4o"`, resolve `config.agents.get(agentID)` di titik `services.go:91` atau titik Rust yang menerima). Proto `ExecuteTurnRequest` MUNGKIN masih perlu field tambahan (`agent_alias`) KARENA `TurnRequest.agent_id` adalah identitas Go-level, sedangkan `ExecuteTurnRequest` adalah pesan terpisah ke Rust yang levelnya beda (lihat Temuan 1 poin 2) — tapi ini perlu diverifikasi ULANG di titik Rust-nya sebelum ditulis sebagai task final |
| BL-002 | "Tambah CrewMember.AgentAlias + kirim di call" | Tetap relevan, TAPI tambah langkah: telusuri ULANG semua titik yang mengisi `TurnRequest.AgentID` hari ini (bukan hanya asumsi "belum ada") — mungkin sudah ada logic ad-hoc yang perlu diselaraskan ke `CrewMember.AgentAlias`, bukan ditambah dari nol |
| BL-003 | "Wire SopStep.agent" | **Tidak berubah** — temuan ini tetap valid, tidak ada bukti sebaliknya di archive/sprint lain |

### Temuan 3 — Tidak ada ticket archive/aktif lain yang menduplikasi scope ini

Grep `agent_alias|AgentAlias|CrewMember|AliasedAgentConfig|ExecuteTurnRequest|SopStep\.agent` ke
`board/sprints/sprint-02/reference/` (konsolidasi 31 tiket T3-01..T3-28): **0 match**. Tidak ada
tiket dev-task-3 yang menyentuh jembatan identitas ini — US-001/BL-001..003 BUKAN duplikasi kerja
yang sudah direncanakan tim lain. Grep ke `archive/dev-task-2/` juga tidak menemukan desain
jembatan ini (hanya menemukan `agent_id` dalam konteks TIDAK TERKAIT: memory erase per-agent).

### Tindakan yang Diperlukan Sebelum Task Dieksekusi

**TASK-016/017/018 yang sudah dibuat MASIH VALID sebagai arah kerja**, tapi deskripsi
task-nya perlu di-update agar langkah pertama agy adalah MEMBACA ULANG `services.go:40-100` dan
addendum ini — bukan langsung menganggap proto `ExecuteTurnRequest` kosong dari nol seperti
asumsi awal. Lihat update task di bawah.
