# RES-2026-10-29 — Baseline Fakta Codebase untuk Migrasi Rust Bahasa Tunggal

> Peran penyusun: Senior Lead Engineer (teknis) + Senior Product Manager (dampak produk).
> Metode: audit statis (baca kode, `git log`, `grep`, hitung baris). **Tidak ada build/test yang dijalankan** — `cargo`, `go`, dan `protoc` tidak terpasang di sandbox audit. Setiap angka di bawah dapat diulang dengan perintah di bagian "Cara Reproduksi".
> Disusun oleh asisten AI atas instruksi Owner (Achmad). Bukan hasil eksekusi agent `agy`/`kirocrew`.

## 0. Baseline Commit

| Repo | Branch | Commit | Tanggal |
|---|---|---|---|
| `diezy-realm/galleon-fleet` | `testing` | `3f3a7298cc0b22a145c5799befc0ee9e7c46b297` | 2026-10-28 (`docs(normative)… (#95)`) |
| `diezy-realm/board` | `import-main` | `de99aff14d0e5457382d3c8bee60dd99029e850c` | 2026-10-26 |

Semua klaim "baris X" merujuk ke commit di atas. Kalau `testing` sudah bergerak, jalankan ulang TASK-051 (re-baseline) sebelum memulai sprint.

## 1. Temuan Kritis (urut berdasarkan dampak ke migrasi)

### F-01 — Router produksi Rust gateway hanya memasang sebagian kecil rute (regresi refactor)

- Produksi memakai `galleon_gateway::run_gateway*` → `build_gateway_router()` di `crates/galleon-gateway/src/gateway.rs:134`. Router itu hanya memasang **~23 rute**: `/health`, `/ready`, `/api/sections*`, `/api/config/sections*`, `/ws`, `/ws/chat`, `/api/status`, `/api/health`, `/api/config`, `/api/config/drift`, `/api/logs`, `/api/auth/ratelimit`.
- Commit `db18a3745` (2026-10-03, "feat: refactoring rust") menghapus **4.927 baris** dari `crates/clawcrew-gateway/src/lib.rs`. Sebelum commit itu, `lib.rs` berisi **157 panggilan `.route(` / 152 path unik** (cek: `git show db18a3745^:crates/clawcrew-gateway/src/lib.rs`). Setelah itu `gateway.rs` sempat `unimplemented!()` sampai TASK-030 (`f94e8b091`, #75) membangun router minimal.
- Yang hilang dari produksi tetapi **masih dipanggil konsumen internal**:
  - CLI `src/main.rs:8271` → `/admin/shutdown`; `:8328` → `/admin/sop/pending`; `:8513` → `/admin/paircode`.
  - ACP bridge `src/bin/clawcrew-acp-bridge.rs:291` → `/pair`.
  - Channel webhook (`/whatsapp`, `/linq`, `/nextcloud-talk`, `/webhook/gmail`) dibangun di `optional_channel_routes()` (`lib.rs:515`) tetapi fungsi itu **tidak pernah dipanggil**.
  - `/api/pair` hanya dipasang di test (`api_pairing.rs:1141`).
  - `register_core_handlers()` (`handlers/mod.rs:332`, berisi `/api/turn`, `/api/audit`, `/api/webauthn`, `/api/version/*`) hanya dipanggil di test.
- Layer keamanan router lama (`RequestBodyLimitLayer` 64 KB, `TimeoutLayer` 30 s, `security_headers::apply[_with_hsts]`, `into_make_service_with_connect_info`) — lihat `lib.rs` lama baris 2288–2453 — **tidak ada** di `build_gateway_router` sekarang.
- Dampak: migrasi tidak bisa sekadar "pindahkan rute Go ke Rust". Langkah pertama adalah **memulihkan router Rust yang punya konsumen**, dengan layer keamanannya.

### F-02 — Dashboard web & desktop bergantung pada Go `:9090`, tetapi Go tidak dikirim di image produksi

- `web/` (Vite) mem-proxy `/api` ke `ENGINE_URL` atau `http://127.0.0.1:9090`. 28 path API dipanggil dari `web/src` (lihat §3).
- Tauri `apps/tauri/src/main.rs`: default `GALLEON_ENGINE_URL` = `:9090`; sidecar hanya menjalankan Rust `galleon daemon` (port gateway 42617), **tidak pernah** menjalankan Go. CSP `connect-src` ke `:9090`.
- `nginx/galleon.conf` upstream `127.0.0.1:9090`.
- `Dockerfile` hanya build Rust.
- Dampak produk: tanpa Go dijalankan manual, dashboard (Fleet, Crow's Nest, Settings, Remote Access) menampilkan error. Ini **bukan** risiko teoretis; ini status `testing` saat ini.

### F-03 — Kontrak Go↔Rust sudah drift secara diam-diam (concern utama Owner terbukti)

- `proto/agent_service.proto` + `crates/galleon-gateway/build.rs`. Go `engine/src/crew/services.go` mengirim `ExecuteTurnRequest.system_prompt` (field 3), `tools` (5), `max_tokens` (7).
- Rust `grpc_system_gateway.rs::execute_turn` hanya memakai `messages`, `model/agent_alias`, `temperature` — field 3/5/7 **diabaikan**, dan tidak pernah mengirim `TurnToolCall` → tool-calling lewat boundary mati.
- Go loop: saat `io.EOF` langsung emit `EventTurnCompleted "Turn completed successfully."` tanpa event `Complete` dari Rust (≈ `services.go:151`, `:296`) → **false success**.
- Event tool di-flatten jadi teks (`"Executing tool '%s' with arguments"`), `tool_call_id` hilang.
- `start_grpc_server()` (SystemGateway `127.0.0.1:50052`, `gateway.rs:17`) **diekspor tetapi tidak pernah dipanggil**. Arah sebaliknya: Rust `/api/turn` → `strangler_runner.rs:475 handle_api_turn` → Go AgentEngine `127.0.0.1:50051` (`DEFAULT_ENGINE_GRPC_ENDPOINT`, baris 19), tanpa `require_auth`, dan handler itu sendiri tidak dipasang di produksi (F-01).
- Kesimpulan: dua bahasa + protobuf menghasilkan dua sumber kebenaran yang tidak dijaga test kontrak. Bahasa tunggal menghapus kelas masalah ini.

### F-04 — Celah keamanan di Go fleet API (harus dikontain sampai Go dihapus)

| ID | Lokasi | Masalah | Kategori |
|---|---|---|---|
| S-01 | `engine/core/metrics/metrics.go:108` `Addr: fmt.Sprintf(":%d", port)`; `core/config/config.go:27` default 9090 | Bind ke semua interface | OWASP A02:2025 Security Misconfiguration |
| S-02 | `engine/src/fleet/delivery.go:442–490` `handleTerminalExec` (dipasang di **dua** path: `/api/terminal/exec` dan `/api/engine/execute`, `delivery.go:72,75`) | Identitas hanya dicek bila `approved=true`; perintah tier `EXECUTE` dieksekusi tanpa auth, diteruskan ke Rust `ExecuteNativeTool("bash")` (`services.go:846`) | A01 Broken Access Control; API5 BFLA |
| S-03 | `engine/src/fleet/terminal_policy.go` `EvaluateTerminalCommand` | Denylist regex (bukan allowlist) | A06 Insecure Design |
| S-04 | Rust `ExecuteNativeTool` / `GetDecryptedSecret` (`grpc_system_gateway.rs`), `SystemGatewayService::new(None)` | Tidak ada auth bila token tidak diset | A07 Authentication Failures |
| S-05 | `engine/src/fleet/services.go:491–508` `SaveCollection` | Cek kuota dilewati bila body bukan JSON array (`json.Unmarshal(...) == nil` jadi syarat); `os.WriteFile(path, raw, 0644)` non-atomic padahal komentar "Atomic" | API4 Unrestricted Resource Consumption; A08 Integrity |
| S-06 | `engine/src/fleet/services.go:931–987`, `delivery.go:567–573` `GetProjectGitStatus` | `projectPath` diabaikan; saat gagal mengembalikan `{branch:"main", clean:true, PolicyCheck:"evaluated-pass"}` | A10:2025 Mishandling of Exceptional Conditions (false success) |
| S-07 | Rust `build_gateway_router` (F-01) | Tanpa body limit / timeout / security headers | API4; A02 |

### F-05 — Banyak kode Go tidak terhubung ke graf produksi (YAGNI: jangan di-port)

Tidak punya importer di jalur produksi Go: `squad` (140 baris), `ship` (68), `mission` (212), `approval`/learning handler (227; `NewLearningHandler` tidak dipanggil → `/api/v1/learning/proposals*` 404 walau web memanggilnya), `schedule` (128), `protocol` (333, Galleon Client Protocol WS — tidak direferensikan), `policy` (62), `treasury` (10), `pkg/store/sqlite` (628, hanya test). Stub 3 baris: `audit`, `briefing`, `charter`, `integration`, `navigator`. Wire: `fleet.NewHTTPHandler(fleetService)` tanpa resolver/pairing → rute `/api/pairing/*` **tidak terpasang**.

Ukuran Go: 193 file, ±21,4k baris produksi (4.087 di antaranya generated `pkg/pb`), ±8,4k baris test. `go.mod` `go 1.27.1`, tetapi `engine-ci.yml` memakai `go-version: '1.25'` (drift).

### F-06 — Data seed terduplikasi dengan penamaan berbeda

`engine/data/` (snake_case: `chat_messages.json`, `global_steering.json`, …, 17 file) vs `web/data/` (camelCase: `chatMessages.json`, `globalSteering.json`, …, 10 file). Allowlist koleksi Go ada di `services.go:684–700` (15 nama). Migrasi harus memilih satu sumber (rekomendasi: `engine/data` → pindah ke crate Rust).

### F-06b — Direktori data fleet bergantung pada working directory

`engine/src/fleet/services.go:57–69 resolveDataDir()`: `GALLEON_DATA_DIR` → `FLEET_DATA_DIR` → bila ada folder `engine` di CWD pakai `engine/data` → selain itu `data`. Artinya saat Go dijalankan dari root repo, data dashboard pengguna **ditulis ke folder seed yang di-commit** (`engine/data`). Ini berbeda dari `cfg.DataDir` (`os.UserConfigDir()/galleon-fleet`, `core/config/config.go:85–95`) yang dipakai store lain. Port Rust harus: (1) memakai direktori data di bawah workspace Galleon, (2) tetap menghormati `GALLEON_DATA_DIR` untuk kompatibilitas, (3) mengimpor sekali file lama bila direktori baru kosong, tanpa menghapus sumber.

### F-07 — Higiene Rust: lint workspace tidak diwarisi crate

- Root `Cargo.toml` mendefinisikan `[workspace.lints]` (`unsafe_code = "warn"`, `clippy::unwrap_used/expect_used = "warn"`), tetapi dari 60 `Cargo.toml` di `crates/*` dan `apps/*`, **hanya `galleon-channel-wecom-ws`** yang punya `[lints] workspace = true`.
- `scripts/ci/run_clippy.sh:79` menjalankan `-- -D warnings`. Artinya mewarisi lint tanpa baseline akan langsung memecahkan CI. Perlu ratchet (lihat SPEC-016).
- Perkiraan atas `.unwrap()`/`.expect(` (termasuk `mod tests` inline, jadi batas atas): runtime 6.278, tools 3.451, memory 1.456, config 1.181, providers 1.033, infra 914, log 453, plugins 431, channels 383, gateway 337.
- Kata kunci `unsafe` (termasuk komentar/`unsafe_code` attr): config 130, runtime 66, tools 27, channels 17, log 15. Hanya `galleon-spawn` yang `#![forbid(unsafe_code)]`.

### F-08 — `galleon-runtime` adalah god crate

±272k LOC. Modul terbesar: `agent` ±81k, `sop` 43,3k, `tools` ±42k, `security` ±16,6k, `skills` 13,7k, `acp` ±12k, `cron` 11k, `control_plane` ±7k. Coupling (jumlah `crate::<modul>` keluar):

| Modul | LOC | Dipakai oleh N file lain | Bergantung ke |
|---|---|---|---|
| `cron` | 11.037 | 11 | platform, control_plane, health, security |
| `sop` | 43.293 | 16 | agent, security, health, tools, control_plane, cron |
| `skills` | 13.693 | 16 | tools, i18n, security, agent, platform, cost |
| `approval` | 1.216 | 11 | i18n, security |
| `doctor` | 3.526 | 0 | i18n, service, observability, tools, daemon |
| `tunnel` | 1.828 | 0 | — |

Kandidat ekstraksi pertama yang aman adalah modul dengan sedikit dependensi keluar (`approval`, `tunnel`), bukan `agent`/`sop`.

### F-08b — Penamaan crate baru

Nama package root sudah `galleon-fleet`; crate baru **tidak boleh** bernama `galleon-fleet` (bentrok). Gunakan `galleon-fleet-core`.

### F-09 — Drift build & test tooling

- `.cargo/config.toml` memasang `rustc-wrapper = "sccache"` tanpa syarat dengan komentar "harmless". Cargo gagal ("could not execute process `sccache`") di mesin tanpa sccache → klaim "harmless" tidak benar.
- `.config/nextest.toml`: profil `default` `retries = 0` padahal komentarnya "Retry sekali"; profil `ci` `retries = 2`, slow-timeout 60 s × 4.
- CI tidak punya lane doctest. `cargo nextest` tidak menjalankan doctest, jadi doctest saat ini tidak dijalankan di CI.
- 25 referensi `--exclude clawcrew-desktop` (11 di `.github/`, 14 di `Containerfile`, `dev/ci.sh`, `scripts/ci/*`) padahal `apps/tauri` sudah di-`exclude` dari workspace dan nama package-nya `galleon-desktop`.
- `homepage = https://www.clawcrew.com` dan crate fixture `clawcrew-*` tersisa (drift terhadap ODR-19 rebrand).
- `codeql.yml` bahasa: `javascript-typescript`, `rust` (tanpa Go). Tidak ada `sonar-project.properties`.
- `rust-conventions.md` mengajarkan `tracing`/`#[instrument]`, padahal `clippy.toml` melarang macro log langsung (wajib `::galleon_log::record!`, komentar masih menyebut `clawcrew_log`).

### F-10 — Kemampuan Rust yang sudah ada (reuse, jangan tulis ulang)

| Kebutuhan migrasi | Sudah ada di Rust |
|---|---|
| Agent loop + streaming | `galleon_runtime::agent::Agent::turn_streamed*` (dipakai `/ws/chat`, `crates/galleon-gateway/src/ws/dispatch.rs:499`) |
| Policy perintah shell | `galleon-config/src/policy.rs:3250 validate_command_execution`, `:3400 is_command_allowed` |
| Approval HITL | `galleon-runtime/src/approval/mod.rs:84 ApprovalManager` |
| Pairing & device | `galleon-gateway/src/api_pairing.rs:34 DeviceRegistry` (SQLite SSOT, ODR-2026-10-09 T-08), `galleon-config/src/pairing.rs:347 PairingGuard` |
| Auth bearer | `galleon-gateway/src/api/mod.rs:36 require_auth` |
| Metrik sistem | `sysinfo 0.36` (galleon-infra, galleon-runtime), `runtime/process_stats.rs` |
| QR code | `qrcode 0.14` (sudah di `Cargo.lock`) |
| SQLite | `rusqlite` (sudah di `Cargo.lock`) |
| Snapshot test | `insta` (sudah di `Cargo.lock`) |
| JSON schema | `schemars` (sudah di `Cargo.lock`) |

Artinya port fleet API **tidak memerlukan dependensi baru**.

### F-13 — Sebagian respons Go fleet adalah data rekaan (penting untuk definisi "paritas")

| Endpoint | Fakta di `engine/src/fleet/services.go` | Konsekuensi untuk port |
|---|---|---|
| `GET /api/fleet/metrics` | `SystemUptime: "99.98%"`, `GatewayLatencyMs: 14` konstanta (148–170, komentar "telemetry placeholders"); `TotalTreasuryLedgers` menghitung koleksi `treasuryLedger` padahal nama file `treasury_ledger` → selalu 0 | Port bentuk JSON, **bukan** konstanta. Nilai tanpa sumber nyata → `null`. |
| `GET /api/providers/harbor` | Daftar provider hard-coded (Ollama/Gemini dll. dengan latency & status karangan, 271+) | Ganti dengan provider yang benar-benar dikonfigurasi di `galleon-config`. |
| `POST /api/diagnostics/remedy` | Mengubah semua item jadi `healthy` / `12ms` tanpa melakukan apa pun (399–408) | **Tidak di-port.** Tombol UI dihapus. |
| `GET /api/diagnostics` | Cek d-1 ke port 50052 (gRPC yang tidak pernah dijalankan → selalu down); d-2…d-5 status `unknown` statis (77–81) | Port dengan cek nyata yang tersedia di Rust (gateway self, data dir writable, provider terkonfigurasi, memory backend); sisanya tidak ditampilkan. |
| `POST /api/snapshots` | `SizeMB: 26.4`, `EntityCount: 42` konstanta; snapshot hanya di memori, tidak menyalin data (416–436) | Port sebagai snapshot nyata (salin file koleksi ke `snapshots/<id>/`, ukuran & jumlah dihitung) **atau** hapus fitur — keputusan Owner (PRD-002 Q2). |
| `GET /api/system/metrics` | Meneruskan ke `s.gateway.GetSystemMetrics` via gRPC; gateway tidak pernah berjalan → error | Port langsung dengan `sysinfo`. |
| `POST /api/fleet/deck-bell` | Mengembalikan string konstanta (218–220) | Port apa adanya (tidak mengklaim efek apa pun). |

Definisi paritas di program ini: **bentuk kontrak JSON sama, nilai harus jujur**. Ini perubahan perilaku yang disengaja dan dicatat di PRD-002.

### F-11 — Referensi Go di luar `engine/` (76 file)

Daftar lengkap: `RES-2026-10-29-go-reference-inventory.txt`. Yang berupa kode/test, bukan dokumen:

- `tests/architecture/tier_boundaries.rs` dan `no_duplicate_risk_tier.rs` mengunci aturan 4-tier (risk-tier SSOT = Go `engine/src/fleet/services.go`). Test ini akan merah/irrelevan begitu Go dihapus → harus ditulis ulang, bukan dihapus diam-diam.
- `apps/galleoncode/src/config/mod.rs:276–310` punya section `[engine]` (default `enabled: false`, `http://localhost:9090`, `localhost:50051`) + `tests/contract_test.rs` "Contract tests for Go Engine". TUI sendiri berbicara JSON-RPC ke daemon (`client.rs`), jadi section ini sisa.
- `crates/galleon-eval/src/runner.rs` memakai nama `GoTurnRequest` dan doc "Go engine", padahal mengimpor `galleon_runtime::agent::agent::Agent` — drift penamaan saja.
- Komentar: `crates/galleon-gateway/Cargo.toml:32` (gRPC D1), `apps/tauri/Cargo.toml:20`, `crates/galleon-api/src/sop.rs:4`.
- Root `AGENTS.md` dan `CLAUDE.md` **tidak** memuat referensi Go (koreksi atas catatan sesi sebelumnya).

### F-14 — `galleon-gateway/src/tests.rs` yatim; handler admin sudah terhapus dari kode

- `crates/galleon-gateway/src/tests.rs` (7.596 baris, 188 atribut `#[test]`/`#[tokio::test]`) **tidak dideklarasikan** sebagai modul di `lib.rs` (tidak ada `mod tests;`), sehingga tidak pernah dikompilasi. Isinya mereferensikan fungsi yang sudah tidak ada (mis. `require_localhost`, dipakai di `tests.rs:6199–6218`).
- `plugin_webhook/tests.rs:13` mengimpor `crate::tests::admin_paircode_state`, padahal `crate::tests` tidak ada. `plugin_webhook.rs:204–205` memasang `#[cfg(test)] mod tests;`. **Dugaan kuat:** build test `galleon-gateway --lib` gagal kompilasi. Belum diverifikasi karena cargo tidak tersedia di lingkungan audit — wajib dicek di TASK-063.
- Handler `handle_admin_shutdown`, `handle_admin_reload`, `handle_admin_paircode`, `handle_admin_paircode_new`, `handle_pair`, `handle_pair_code`, `require_localhost` **tidak ada lagi** di `crates/galleon-gateway/src` (hanya di riwayat: `git show db18a3745^:crates/clawcrew-gateway/src/lib.rs`, baris 2621, 4619, 4675, 4758, 4805, 4954). Yang masih ada: `api_pairing.rs` (`initiate_pairing:362`, `submit_pairing_enhanced:388`, `list_devices:533`, `revoke_device:568`, `update_my_capabilities:623`, `rotate_token:674`), `api_sop.rs` (`handle_sop_pending:131`, `handle_sop_approve:160`), `optional_channel_routes` (`lib.rs:514`), konstanta `MAX_BODY_SIZE`/`REQUEST_TIMEOUT_SECS`/`LONG_RUNNING_REQUEST_TIMEOUT_SECS` (`lib.rs:72–75`), `security_headers` (`lib.rs:54`), dan `AppState.shutdown_tx/reload_tx/device_registry/pending_pairings` (`state.rs:54–63`).
- Dampak: SPEC-012 harus **memulihkan** handler admin dari riwayat (diadaptasi ke `galleon_*`), bukan sekadar "mount".

### F-15 — Web tidak punya alur auth; sebagian besar request tanpa Bearer

- `web/src/utils/apiClient.ts` memanggil 20 `fetch('/api/...')` mentah. Hanya `executeTerminalCommand` (`:338–349`) yang menambahkan `Authorization: Bearer` dari `localStorage['galleon_auth_token']`; **tidak ada kode web yang pernah menulis** key itu (`rg "galleon_auth_token" web/src` → hanya `apiClient.ts:343`). `get<T>`/`post<T>` (`:427–460`) juga tanpa header.
- Web tidak memakai WebSocket `/ws/chat` sama sekali.
- `require_pairing` default `true` (`galleon-config/src/schema.rs:7804`); `require_auth` (`galleon-gateway/src/api/mod.rs:36`) menolak tanpa token.
- `/api/health` sudah ada di Rust (`api/mod.rs:437`, wajib auth, bentuk `{"health": snapshot}`), sedangkan web mengharapkan bentuk Go `{status, uptime, timestamp}` (`apiClient.ts:411`, Go `delivery.go:398–408`) → **bentrok path**, harus diputuskan di SPEC-013.
- Tauri: web memanggil `invokeTauri('get_api'|'post_api')` (`apiClient.ts:431,446`) tetapi command itu **tidak ada** di `apps/tauri/src/main.rs` (251 baris; hanya proxy per-fitur ke `GALLEON_ENGINE_URL`, tanpa header auth) → selalu jatuh ke `fetch` relatif.
- Dampak: cutover (SPEC-014) wajib menambahkan layar pairing + satu wrapper `authFetch` **sebelum** web diarahkan ke gateway; kalau tidak, seluruh dashboard 401.

### F-16 — Kunci seed tidak cocok antara Go dan web; dua salinan seed berbeda

- Go `GetSeedData` (`engine/src/fleet/services.go:680–718`) membaca `engine/data/<snake_case>.json` dan mengembalikan kunci snake_case (`treasury_ledger`, `journal_sessions`, `chat_messages`, `training_skills`, `global_steering`, `steering_directives`, `training_hooks`) di `{"status":"ok","seed":{...}}` (`delivery.go:292–308`).
- Web `hydrateFleet` (`web/src/store/fleetStore.ts:405–450`) membaca kunci camelCase (`treasuryLedger`, `journalSessions`, …) → **7 dari 15 koleksi seed tidak pernah terisi** hari ini. `fetchRealData` (`fleetStore.ts:340–372`) memakai nama koleksi camelCase untuk `/api/collections/{name}` → file Go `chatMessages.json` dst., berbeda dari file seed snake_case.
- Koleksi Go **tidak di-allowlist**: nama apa pun disanitasi `[^a-zA-Z0-9_-]` (`services.go:26`) lalu dibaca/ditulis sebagai file.
- `web/data/*.json` (15 file camelCase, 64 KB) tidak direferensikan kode mana pun dan isinya **berbeda** dari `engine/data` (76 KB) — dicek dengan `cmp` pada `ships`, `crew`, `quests`, `treasury_ledger`.
- Dampak: SPEC-013 menetapkan nama koleksi kanonik = camelCase (yang dipakai web), allowlist 15 nama + `policies`/`riskTiers`, seed dari `engine/data` dengan pemetaan nama, dan menghapus `web/data` di Sprint 13 (Q7 PRD).

### F-17 — Test arsitektur dan gate yang sudah ada (reuse, bukan buat baru)

- `tests/architecture/no_duplicate_risk_tier.rs` memindai `web-2/src` (`SCAN_ROOTS`, baris ±18) yang **tidak ada** lagi; `scan_dir` mengembalikan diam-diam bila direktori tidak ada (`:43–46`) → test lolos tanpa memeriksa apa pun. Dokumentasinya menyatakan Go sebagai SSOT risk tier.
- `tests/architecture/tier_boundaries.rs` menegakkan model 4-tier dengan Go Tier 3 (`:1–6`, `test_go_engine_tier_boundaries` `:158`).
- `tests/architecture/dependency_direction.rs` sudah menegakkan arah dependensi crate (R-04) → Sprint 15 **memperluas** file ini, tidak membuat test DAG baru.
- `scripts/ci/check_production_unwrap.py` (gate diff "zero-unwrap baru" T-CI-01) dan `scripts/ci/brand_gate.py` (larangan `clawcrew`/`zeroclaw`) sudah ada, `check_production_unwrap.py` sudah dirujuk `.github/workflows/pr-testing-gate.yml:69` dan `principle-review-trigger.yml:31` (dikoreksi 2026-10-29); `brand_gate` tidak dirujuk workflow mana pun (hanya `.github/workflows/README.md:45`). `gates.sh` lokal Owner (`~/Apps/dev-ci`, `ci.yml:3–5`) di luar repo, tidak bisa diaudit.
- `galleon-api/src/doctor.rs:11` (`DiagResult {severity, category, message}`) + `galleon-runtime/src/doctor/mod.rs:95` (`diagnose(&Config)`) dapat dipakai untuk `/api/diagnostics` nyata.
- `CommandRiskLevel {Low, Medium, High}` (`galleon-config/src/policy.rs:13`) adalah sumber risk-tier Rust; `engine/data/riskTiers.json` adalah tabel tampilan 1..N dengan `maxBudgetUSD`.
- Go terminal exec mempercayai field `approved`/`approved_by` dari klien (`engine/src/fleet/terminal_policy.go:26–28`) — persetujuan dapat dipalsukan klien.
- Approval di dashboard (`fleetStore.ts:727–750`) adalah item koleksi `approvals`; pemanggilan `/api/v1/tool-executions/{id}/{approve|deny}` (Go `engine/src/tool/delivery.go:29`, layanan in-memory) gagal diabaikan (`console.warn`). Tidak ada eksekusi tool nyata yang terhubung.

### F-18 — Wiring `serve` gateway yang hilang di `db18a3745`

- `run_gateway_with_plugin_webhooks` (`crates/galleon-gateway/src/gateway.rs:58–108`) kini hanya `TcpListener::bind` + `axum::serve(listener, app)`.
- **TLS/mTLS:** `tls::build_tls_acceptor` (`tls.rs:16`) tidak dipanggil di mana pun; OLD membangun acceptor dan loop accept TLS (OLD:2360–2440). Akibat: `[gateway.tls] enabled = true` diabaikan → HTTP polos. Deps `hyper`, `hyper-util`, `rustls`, `tokio-rustls` masih ada (`crates/galleon-gateway/Cargo.toml:43–51`).
- **Peringatan public bind** (OLD:891–905) hilang; `galleon_config::pairing::is_public_bind` (`pairing.rs:767`) masih ada.
- **`path_prefix`** (`schema.rs:7662`) tidak dipakai gateway (OLD:2336–2347 memakai `nest`).
- **Tunnel:** `create_tunnel` hanya dipanggil test (`src/tunnel/mod.rs`); OLD memulai tunnel di OLD:1574–1605. Dicek dengan `git log -S 'create_tunnel('` → penghapusan terakhir di `db18a3745`.
- **mDNS:** `nodes/mdns.rs` ada, `MdnsAdvertisedGateway::new` tidak dipanggil (OLD:1772).
- Dampak: SPEC-017 (Sprint 15). Semua ini **tidak terkait Go**; hanya bergantung pada TASK-059.

## 2. Inventaris Rute Go yang Terpasang (sumber: `grep` `Handle/HandleFunc/RegisterRouteFunc` di `engine/src`)

`/api/chat/quartermaster`, `/api/collections/`, `/api/diagnostics`, `/api/diagnostics/remedy`, `/api/engine/execute`, `/api/engine/processes`, `/api/fleet/deck-bell`, `/api/fleet/metrics`, `/api/fleet/policies`, `/api/fleet/seed`, `/api/health`, `/api/network/qrcode`, `/api/pairing/{claim,devices,initiate,revoke}` (kode ada, **tidak terpasang**), `/api/project/git-status`, `/api/providers/harbor`, `/api/query`, `/api/snapshots`, `/api/system/{executive-briefing,metrics,network}`, `/api/terminal/{audit,exec}`, `/api/turn`, `/api/v1/{approvals/,artifacts/,audit/trail,crews,crews/,entitlement/usage,learning/proposals[/],runs[/],tasks/,tool-executions/,tool-requests,tools,workflows[/]}`, `/test/runs`, plus `/metrics`, `/healthz`.

## 3. Inventaris Konsumen (path yang dipanggil `web/src`)

`/api/collections/${name}` (2), `/api/snapshots` (2), `/api/v1/tool-executions/${id}/${action}`, `/api/v1/learning/proposals[/${id}/{approve,reject,revert,feedback}]`, `/api/project/git-status`, `/api/network/qrcode`, `/api/v1/audit/trail`, `/api/terminal/exec`, `/api/system/{network,metrics,executive-briefing}`, `/api/providers/harbor`, `/api/pairing/{revoke,initiate,devices}`, `/api/health`, `/api/fleet/{seed,policies,metrics,deck-bell}`, `/api/engine/processes`, `/api/diagnostics[/remedy]`, `/api/chat/quartermaster`.

Tidak dipanggil web: `/api/turn`, `/api/query`, `/api/v1/{crews,runs,tasks,tools,tool-requests,workflows,approvals,artifacts,entitlement/usage}`, `/api/engine/execute`, `/api/terminal/audit`, `/test/runs`. → Kandidat **tidak di-port** (YAGNI), kecuali Tauri/CLI memakainya (cek di TASK-058).

Tauri commands (`apps/tauri/src/main.rs`): `get_fleet_metrics`, `ring_deck_bell`, `get/save_collection`, system metrics, executive briefing, harbor providers, diagnostics, remedy, snapshots, engine processes, fleet policies, `chat_quartermaster`.

## 4. Cara Reproduksi

```bash
# F-01
git -C galleon-fleet show db18a3745 --stat | grep gateway
git -C galleon-fleet show db18a3745^:crates/clawcrew-gateway/src/lib.rs | grep -c '\.route('
sed -n 134,223p galleon-fleet/crates/galleon-gateway/src/gateway.rs
# F-03
grep -n 'system_prompt\|tools\|max_tokens' galleon-fleet/crates/galleon-gateway/src/grpc_system_gateway.rs
# F-05
grep -rhoE '(Handle|HandleFunc|Register[A-Za-z]*)\("(/[^"]*)"' galleon-fleet/engine/src --include=*.go | grep -v _test
# F-07
for f in galleon-fleet/crates/*/Cargo.toml; do grep -q '^\[lints\]' $f && echo $f; done
# §3
grep -rhoE "['\"\`]/api/[a-zA-Z0-9_/{}\$.:-]*" galleon-fleet/web/src | sort | uniq -c
```

## 5. Batasan Audit (jujur)

- Statis saja; tidak ada `cargo build/test/clippy` maupun `go test`. Status hijau/merah CI tidak diverifikasi.
- Hitungan `unwrap/expect/unsafe` adalah batas atas berbasis `grep` dan berbeda tergantung pola (mis. pola `\.unwrap\(\)|\.expect\(` di seluruh folder crate termasuk `tests/` memberi runtime 8.516). Angka resmi ratchet = output clippy saat task Sprint 14 dikerjakan.
- Board snapshot masih menampilkan beberapa task `blocked` di sprint 04–08; Owner menyatakan pekerjaan board selesai 100%. Paket ini mengikuti pernyataan Owner dan menandai drift itu di RPT-108.
