---
id: SPEC-013
type: spec
spec_kind: api
title: Port fleet API ke crate galleon-fleet-core dan adapter gateway
status: approved
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta: RES baseline F-02, F-04, F-06b, F-10, F-13, F-15, F-16, F-17; ADR-0018 §3. Kontrak acuan: fixture `tests/fixtures/go-fleet/*.json` (TASK-065) dan tipe TS di `web/src/utils/apiClient.ts`. **Bila fixture Go berisi error** (mis. `/api/system/metrics` yang gagal karena gRPC SystemGateway tidak jalan), kontrak acuan = tipe TS.

## Pernyataan Masalah (Problem Statement)
Endpoint dashboard hanya ada di Go `:9090`, yang tidak dijalankan image produksi maupun sidecar desktop. Beberapa respons Go berisi data karangan (F-13), terminal exec mempercayai flag `approved` dari klien (F-17), kunci seed tidak cocok dengan web (F-16), dan `/api/system/metrics` selalu gagal (bergantung gRPC ke Rust yang tidak pernah start).

## Solusi yang Diusulkan (Proposed Solution)
**Struktur (ADR-0018 §3, rust-conventions amendment §2):**
```
crates/galleon-fleet-core/            # domain murni, tanpa axum/runtime/gateway
  src/lib.rs                          # #![forbid(unsafe_code)]; pub mod store, collections, snapshots, seed, metrics, policies, intent;
  src/error.rs                        # FleetError (thiserror)
  seed/*.json                         # salinan engine/data (nama camelCase), include_str!
crates/galleon-gateway/src/api_fleet/ # adapter HTTP (axum), require_auth, sysinfo, qrcode, agent
  mod.rs  routes()                    # Router<AppState>, di-merge di build_gateway_router
  collections.rs snapshots.rs fleet.rs system.rs project.rs terminal.rs quartermaster.rs harbor.rs diagnostics.rs
```
Dependensi `galleon-fleet-core`: `serde`, `serde_json`, `thiserror`, `tempfile`, `regex`, `sha2`, `tokio` (fitur `sync`, untuk `Mutex`) (keduanya sudah di `[workspace.dependencies]`, root `Cargo.toml:191,499`), dev: `insta`, `tempfile`. **Tidak ada crate pihak ketiga baru** di `Cargo.lock` (cek: `git diff Cargo.lock` hanya menambah entri `galleon-fleet-core`).

**Penyimpanan (TASK-067):** `FleetStore { root: PathBuf }` dengan `root = <Config.data_dir>/fleet` (`galleon-config/src/schema.rs:86–110`). Tulis atomik: `tempfile::NamedTempFile::new_in(root)` → `write_all` → `sync_all` → `persist` (pola `galleon-infra/src/session_store.rs:223`). Satu `tokio::sync::Mutex` per store untuk serialisasi tulis (single-tenant, ODR-05). Batas: 1 MiB per koleksi (`FLEET_MAX_BODY = 1_048_576`). Go tidak membatasi body `PUT /api/collections` (tidak ada `MaxBytesReader` di `engine/`), sedangkan batas global gateway 64 KB (`MAX_BODY_SIZE`, `lib.rs:72`) akan menolak koleksi besar seperti `chatMessages` → regresi. Karena itu router `api_fleet` memasang `RequestBodyLimitLayer::new(FLEET_MAX_BODY)` sendiri dan **tidak** berada di bawah batas 64 KB (TASK-059 memasang 64 KB pada router inti, bukan lapisan terluar; TASK-081 me-merge router fleet dengan batasnya sendiri). Batas file yang sama dicek saat tulis. Impor sekali: kandidat sumber berurutan `FLEET_DATA_DIR`, `GALLEON_DATA_DIR` (hanya file `<nama-koleksi>.json` di level atas), `<cwd>/engine/data`; file disalin (bukan dipindah) ke `root` bila belum ada; tulis marker `root/.imported` berisi sumber + waktu; impor tidak diulang bila marker ada.

**Koleksi (TASK-068):** allowlist 15 nama camelCase yang dipakai web (`fleetStore.ts:340–372`): `squads, ships, crew, trainingSkills, globalSteering, steeringDirectives, trainingHooks, quests, artifacts, approvals, logbook, treasuryLedger, notifications, journalSessions, chatMessages`. Nama lain → 404 (Go saat ini menerima nama apa pun, `services.go:26`). Body wajib JSON array.

**Snapshot (TASK-069, default Q2 PRD):** `POST /api/snapshots {label}` menyalin semua file koleksi ke `root/snapshots/<id>/` dan menghitung `sizeMB`, `entityCount`, `checksum` (SHA-256 gabungan isi) **nyata**. `GET` membaca direktori tersebut. Batas 20 snapshot (yang tertua dihapus) — dicatat sebagai konstanta.

**Seed (TASK-070, default Q6 PRD):** `engine/data/*.json` disalin ke `crates/galleon-fleet-core/seed/` dengan nama camelCase (`treasury_ledger.json` → `treasuryLedger.json`, dst.). `GET /api/fleet/seed` mengembalikan `{"status":"ok","seed":{<camelCase>: [...]}}` → 15/15 koleksi terisi (memperbaiki F-16). `scripts/migrations/extract-seed.mjs` tidak dirujuk file lain (`rg extract-seed` hanya menemukan dirinya) → dihapus di TASK-070.

**Nilai jujur (berlaku untuk semua endpoint):** nilai yang tidak bisa diukur → `null` (bukan konstanta). Tipe TS diperbarui menjadi `number | null` di TASK-084.

**Terminal (TASK-078):** auth (`require_auth`) → `SecurityPolicy::validate_command_execution(command, approved=false)` (`galleon-config/src/policy.rs:3250`). Field `approved`/`approved_by` dari klien **diabaikan**. Bila hasil `High` atau ditolak karena butuh approval → respons `requiresApproval: true`, tidak dieksekusi (tidak ada jalur approval HTTP sinkron di Sprint 11; persetujuan interaktif tetap lewat agent/WS). Eksekusi `Low/Medium` via `tokio::process::Command` tanpa shell (argv dari parser policy), timeout 30 s, output dipotong 64 KB. Audit ditulis ke log terstruktur `::galleon_log::record!` **dan** buffer ring 500 entri in-memory untuk `GET /api/v1/audit/trail` (Go juga in-memory; tidak ada kebutuhan persistensi yang tercatat — YAGNI).

**Quartermaster (TASK-079, TASK-080):** `fleet_core::intent::classify(&str) -> Intent` = port 1:1 regex Go (`engine/src/fleet/quartermaster_router.go`). `engine_room` dan `report` dijawab deterministik dari metrik nyata (tanpa LLM). `chat` dan `objective` (default Q3 PRD) → `galleon_api::agent::create_agent_session(config, alias, None, Some(canvas))` lalu `turn_streamed_with_steering_state` dan kumpulkan teks final. Alias: field opsional `agent_alias` di request → `[agents.quartermaster]` bila ada → satu-satunya agent terkonfigurasi → selain itu 422 dengan daftar alias. Kegagalan provider → 502 dengan pesan jujur (Go mengembalikan 200 dengan teks fallback).

## Model Data (Data Model)
| Endpoint | Kontrak acuan | Perbedaan yang disengaja vs Go (F-13) |
|---|---|---|
| `GET /api/fleet/metrics` | fixture + `FleetMetrics` TS | `systemUptime`: `"99.98%"` → `null`; `gatewayLatencyMs`: `14` → `null`; `activeWorkers`: goroutine → `null`; `memoryUsedMB`: RSS proses (sysinfo). Hitungan koleksi tetap. |
| `GET /api/system/metrics` | `SystemMetrics` TS (fixture Go = error) | `goVersion` dihapus dari tipe; ditambah `version` (`env!("CARGO_PKG_VERSION")`); `uptime` = uptime proses gateway (`galleon_infra::health::snapshot().uptime_seconds`); `gateway_latency_ms`, `isolation_mode`, `memory_db_mb` → `null` kecuali ada sumber nyata yang ditemukan di TASK-073 |
| `GET /api/system/network` | fixture | `engine_port` dihapus; `gateway_port` = port bind nyata |
| `GET /api/engine/processes` | fixture | daftar dari `sysinfo` untuk proses `galleon*` saja |
| `GET /api/network/qrcode?url=` | fixture `{url,dataUrl}` | `dataUrl` = `data:image/svg+xml;base64,...` (qrcode fitur `svg`, tanpa crate `image`); `url` wajib `http(s)://`, ≤ 2048 karakter; default = URL LAN gateway |
| `GET /api/system/executive-briefing` | fixture | `treasuryBurnRate` dihitung dari koleksi `treasuryLedger` atau `null` |
| `GET /api/project/git-status?path=` | fixture | `git -C <path> status --porcelain=v1 -b` via `tokio::process`; path wajib di dalam workspace dikonfigurasi; gagal → 4xx/5xx jujur (Go: sukses palsu) |
| `GET /api/providers/harbor` | fixture | dari `Config` provider terkonfigurasi; `status` ∈ `configured`/`missing_credentials`; `latencyMs` → `null`; tidak ada daftar hard-coded |
| `GET /api/diagnostics` | fixture | dari `galleon_runtime::doctor::diagnose(&config)` → `DiagResult` dipetakan ke `DiagnosticItem` (`severity`→`status`), `latency` → `"—"` |
| `POST /api/diagnostics/remedy` | — | **tidak di-port** (Go palsu, `services.go:399–408`) |
| `GET/PUT /api/collections/{name}` | fixture | allowlist; nama lain 404 |
| `GET/POST /api/snapshots` | `SnapshotItem` TS | nilai nyata |
| `GET /api/fleet/seed` | `SeedResponse` TS (`fleetStore.ts:409`) | kunci camelCase (Go snake_case) |
| `GET /api/fleet/policies` | fixture | `riskTiers` dari seed; test arsitektur memastikan tidak ada duplikasi di TS |
| `POST /api/fleet/deck-bell` | fixture | sama (pesan konfirmasi, bukan metrik) |
| `POST /api/terminal/exec` | `TerminalExecResponse` | `approved` klien diabaikan |
| `GET /api/v1/audit/trail` | fixture | ring buffer 500 |
| `POST /api/chat/quartermaster` | `{reply, suggestedActions?, generatedArtifactPreview?}` | 502 saat provider gagal |
| `POST /api/v1/tool-executions/{id}/{action}` | — | **tidak di-port**; tidak terhubung ke eksekusi nyata (F-17). Web berhenti memanggilnya di TASK-084 |
| `/api/v1/learning/proposals*` | — | **tidak di-port** (default Q1) |
| `GET /api/health` (Go) | — | tidak di-port: `apiClient.getHealth` tidak dipakai komponen mana pun (`rg getHealth web/src`); method dihapus di TASK-082. Rust `/api/health` yang ada tidak diubah |

## Desain API (API Design)
Semua rute di tabel atas (kecuali yang tidak di-port) → `require_auth` (Bearer). Error body seragam `{"error": "<pesan>"}`.

Contoh:
```http
POST /api/terminal/exec
Authorization: Bearer <token>
{"command":"git status","approved":true}

200 {"stdout":"...","exitCode":0,"duration":"41ms","riskTier":"low","auditId":"a-17"}
200 {"stdout":"","exitCode":-1,"duration":"0s","riskTier":"high","requiresApproval":true,"auditId":"a-18"}
401 {"error":"Unauthorized — pair first via POST /pair, then send Authorization: Bearer <token>"}
403 {"error":"command not allowed by security policy: <alasan>","auditId":"a-19"}
```
```http
PUT /api/collections/notes   → 404 {"error":"unknown collection"}
PUT /api/collections/ships   (body bukan array) → 400 {"error":"collection body must be a JSON array"}
PUT /api/collections/ships   (file > 1 MiB) → 413 {"error":"collection exceeds 1 MiB"}
```

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- Satu crate `galleon-fleet` berisi domain + axum → ditolak: nama bentrok dengan package root; domain jadi bergantung axum (MOD-01).
- Handler langsung di `galleon-gateway` tanpa crate domain → ditolak: logika store/seed/intent dapat diuji tanpa HTTP dan tidak boleh bergantung `galleon-runtime`.
- SQLite untuk koleksi → ditunda (ODR-32, YAGNI): pola akses = baca/tulis seluruh array per koleksi.
- Menyalin nilai Go apa adanya demi "paritas" → ditolak: melanggar G5 PRD (dashboard jujur).
- PNG QR via crate `image` → ditolak: menambah dependensi berat; SVG cukup untuk `<img>`.

## Pertimbangan Keamanan (Security Considerations)
- OWASP Top 10:2025 A01 (auth semua rute), A05 Injection (terminal tanpa shell, policy allowlist; `git -C` dengan path tervalidasi; koleksi allowlist → tidak ada path traversal), A06 Insecure Design (approval tidak dipercaya dari klien), A10 Mishandling Exceptional Conditions (error jujur, bukan sukses palsu).
- OWASP API Top 10 2023: API1 BOLA (single-tenant; tidak ada ID milik pengguna lain), API3 (respons tidak membocorkan path data/secret), API4 (body 64 KB, file 1 MiB, 20 snapshot, output terminal 64 KB, timeout), API9 (inventaris).
- Rust: `#![forbid(unsafe_code)]`; tanpa `unwrap/expect` di jalur produksi (gate `check_production_unwrap.py`); secret provider tidak pernah diserialisasi ke harbor (hanya status).
- Sonar Rust (bila aktif, Q4): Clippy diimpor sebagai issue; tidak ada aturan Sonar khusus yang membutuhkan perubahan desain.

## Rencana Pengujian (Testing Plan)
- Unit (`galleon-fleet-core`): store atomik (crash simulasi: file temp tidak menimpa), kuota, allowlist, impor sekali (marker), seed 15 kunci, intent classify (tabel kasus dari regex Go), snapshot checksum deterministik.
- Integrasi (`galleon-gateway/tests/api_fleet_*.rs`): server `127.0.0.1:0` + `tempfile::TempDir` sebagai `data_dir`; 401 tanpa token; kontrak bentuk: helper `assert_same_shape(rust_json, go_fixture, &ignored_keys)` membandingkan kunci & tipe JSON (nilai diabaikan; kunci yang sengaja berubah tercantum eksplisit).
- Terminal: perintah allowlist → jalan; perintah di luar allowlist → 403 + audit; `approved:true` dari klien untuk perintah High → tetap `requiresApproval`.
- Quartermaster: classify tanpa LLM; path agent diuji dengan provider palsu yang sudah ada di test-util `galleon-runtime` (fitur `test-util`, `galleon-gateway/Cargo.toml:109`).
- Per task: `cargo nextest run -p galleon-fleet-core -p galleon-gateway --locked`, `cargo clippy ... -- -D warnings`.

## Rollout / Migrasi
066 scaffold → 067 store/impor → 068 koleksi → 069 snapshot → 070 seed → 071 metrik fleet → 072 policies → 073 system → 074 QR/briefing → 075 git-status → 076 harbor → 077 diagnostics → 078 terminal → 079 intent → 080 agent → 081 mount + kontrak. Rute dipasang di gateway hanya di TASK-081 (sebelumnya handler diuji lewat router lokal per modul), sehingga tidak ada rute setengah jadi yang terekspos. Web masih ke Go sampai Sprint 12.
