---
title: ADR (Usulan) — Antarmuka Orkestrasi Multi-Runtime di Galleon: Server MCP, SPI Runtime, Batas Isolasi
status: draft
revision: 2
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: control-plane-multi-runtime-landscape-2026-10-18.md
informs: standard-docs/decisions/owner-decisions/ODR-2026-10-18-multi-runtime-orchestration.md (Proposed)
supersedes_revision: 1 (produk mandiri; tersimpan di commit board e962636)
---

# ADR (Usulan): Antarmuka Orkestrasi Multi-Runtime di Galleon

> **Status: Diusulkan (Proposed), revisi 2.** Belum mengikat. Menurut konvensi proyek, keputusan hanya final bila Owner meratifikasinya sebagai ODR di repo produk (`standard-docs/decisions/owner-decisions/`). Draf ODR pendamping berstatus `Proposed`. Selama itu, isi di bawah adalah rekomendasi.
>
> **Cara membaca bukti.**
> - **[V]** diverifikasi sendiri dengan perintah, uji, atau pembacaan sumber pada 2026-10-18 (UTC). Perintah dan hasilnya ada di §10-B (ID `E1`…`E25`).
> - **[A]** dilaporkan sub-agen riset, tidak dibaca ulang oleh penulis. Rujukan di dokumen riset pendamping.
> - **[S]** dilaporkan sumber luar, tidak diverifikasi mandiri. Rujukan di §10-A.
> - **[I]** inferensi atau penilaian penulis.
> - **[?]** tidak terverifikasi.
>
> Angka `[^n]` menunjuk catatan kaki di §11.
>
> **Dokumen pendamping:** riset induk `control-plane-multi-runtime-landscape-2026-10-18.md`; riset lanjutan `multi-runtime-orchestration-feasibility-2026-10-18.md` (ketentuan vendor, temuan internal, tantangan teknis).

## Catatan Revisi 2

Revisi 1 mengusulkan **produk mandiri** di luar Galleon (D1) dengan antarmuka MCP untuk klien seperti KiroCrew. Setelah Achmad menegaskan bahwa tujuannya adalah menjadikan **Galleon sendiri** orkestrator multi-runtime, dan bahwa board, `agy-bridge`, dan `dev-ci` hanyalah percobaan di luar produk, revisi ini:

- **Mengganti D1** (Galleon sebagai orkestrator; produk mandiri menjadi alternatif yang tidak dipilih, §5).
- **Mengubah D2**: permukaan MCP kini adalah server MCP **Galleon** yang dipanggil agen di dalam sesi (tugas, memori, skills), bukan 10 tool kontrol sesi untuk klien luar.
- **Memindahkan** SPI runtime dan isolasi ke tier Rust dan keputusan ke Go (selaras ODR-03, ODR-07, ODR-11, ODR-22).
- **Menambah** D6 (proyeksi konteks), D7 (onboarding dan uji kepatuhan), D8 (memori bersama dengan provenance), D9 (invarian legal vendor).
- **Mengganti** kriteria penerimaan (T1–T12) dan pertanyaan terbuka.
- **Menambah** log koreksi (§9) dan bukti E15–E25 (§10-B).

---

## 1. Ringkasan Usulan

Galleon menjalankan crew/agent pada **runtime yang dapat berbeda-beda**: `native` (loop agen Galleon, default) atau adapter CLI headless pihak ketiga. Go memutuskan; Rust men-spawn dan mengurung; satu server MCP Galleon menjadi antarmuka koordinasi bagi sesi runtime eksternal.

| # | Usulan | Intinya |
|---|---|---|
| D1 | Galleon sebagai orkestrator multi-runtime (**menggantikan** "produk mandiri") | Binding `runtime` per crew/agent; Go memutuskan, Rust men-spawn dan mengurung |
| D2 | Server MCP Galleon | 7 tool untuk agen dalam sesi: tugas, memori, skills; identitas dari token sesi; state machine ditegakkan server |
| D3 | Model sesi dan log event | State machine tetap, event ternormalisasi, disimpan di store Go (ODR-05) |
| D4 | SPI Runtime di Rust | Kontrak adapter L0/L1/L2; tingkat ditetapkan uji kepatuhan |
| D5 | Batas isolasi | Worktree per sesi, kurungan proses fail-closed, kredensial dan push di luar sesi |
| D6 | Konteks per runtime | Dihasilkan deterministik dari satu sumber ke worktree sesi |
| D7 | Onboarding dan uji kepatuhan | Runtime baru wajib lulus uji sebelum ditugaskan |
| D8 | Memori bersama | Satu store Go; tulisan runtime berupa proposal dengan provenance wajib |
| D9 | Invarian legal vendor | Binary resmi, tanpa menyentuh token, API key untuk otomasi kontinu |
| D10 | Integrasi | ACP (ODR-24), Galleon Client Protocol (ODR-23); fasad MCP untuk kontrol luar bukan v1 |
| D11 | Bukan tujuan v1, versi | Multi-tenant hosted, A2A, pooling kredensial, commerce lewat runtime eksternal |

---

## 2. Konteks

- Riset induk menyimpulkan bahwa lapisan koordinasi multi-harness berbeda kelas dari loop agen Galleon: Galleon menegakkan kebijakan di dalam loop agennya sendiri (Go → Rust sandbox), sedangkan harness pihak ketiga hanya dapat dipagari dari luar.
- Achmad menegaskan arah produk: **Galleon Fleet menjadi AI harness orkestrator multi-runtime yang optimal**. Percobaan di luar produk (board, `agy-bridge`, CI lokal) hanya menunjukkan bahwa satu runtime eksekutor (agy) dapat dijalankan headless berurutan dan dinilai gerbang independen.
- Memasukkan orkestrasi runtime pihak ketiga ke Galleon menyentuh ODR-03 (Go otak tunggal), ODR-07 (eksekusi lewat Go lalu sandbox Rust), ODR-11 (orkestrator di Go), ODR-22 (identitas di Go), dan ADR 0001 (SSOT LLM di Rust) [V]. Penempatan yang selaras: Go memutuskan, Rust men-spawn proses (§4 D1). Hal ini tetap memerlukan ODR baru; draf pendamping ada.
- Bentuk plugin WASM tidak layak (§5). Server MCP sejalan dengan `adr-wasm-plugin-vs-mcp.md` yang menyatakan MCP sebagai jalur untuk alat CLI dan integrasi OS[^1] [V, E13].
- Komponen yang dibutuhkan memetakan ke spesifikasi OpenAI Symphony: Workspace Manager, Agent Runner, Orchestrator, Status Surface[^2] [S, S12].
- Fondasi yang sudah ada di Galleon: binding provider per agen, provider CLI satu-giliran, memori Go bercakupan dengan jalur consent, `AGENTS.md` sebagai file identitas workspace, skills `SKILL.md`, ACP bridge [V, E16, E19–E22].

---

## 3. Verifikasi Prasyarat (2026-10-18)

Bagian P1–P6 berasal dari revisi 1 dan tetap berlaku; P7–P9 baru.

| # | Pertanyaan | Hasil | Tag, bukti |
|---|---|---|---|
| **P1** | Apakah engine Go bisa memanggil server MCP? | **Tidak ada jalur.** Hanya 4 berkas Go non-test menyebut MCP (kode hasil-generate dan `tool/{interfaces,services,dto}.go`), tanpa registrasi tool `mcp:*`. Roadmap Go memuat 0 baris MCP. Gateway menolak tool di luar `ALLOWED_TOOLS`. **Relevansi berubah di revisi 2:** yang dibutuhkan bukan klien MCP di Go, melainkan **server** MCP milik Galleon (P7) | [V] E1, E2, E3 |
| **P2** | Siapa memasang `McpCommandBoundary` di produksi? | **Terpasang** (`runtime/src/tools/mod.rs:751`, commit `f2af74175`, 2026-10-07). **Efektivitas bersyarat:** `create_sandbox` (`security/detect.rs:353`) dapat menghasilkan `NoopSandbox`. Apakah host pengembangan punya backend efektif: **tidak diverifikasi** | [V] E4, E5, E6 |
| **P3** | Transport MCP/ACP yang dipahami klien kita | agy: server MCP `stdio` atau `http` (`--header`). Skema Galleon: `Stdio`, `Http`, `Sse`. kiro-cli: subcommand `acp` ada | [V] E6, E7, E8 |
| **P4** | Primitif isolasi di host pengembangan | `bwrap` terpasang tetapi **tidak dapat dipakai** (`unshare -Ur` EPERM; `apparmor_restrict_unprivileged_userns=1`). Landlock ada di daftar LSM (kernel 7.0.0-38), belum diuji. Docker dipakai `dev-ci` dengan `--cap-drop=ALL`, `no-new-privileges`, `--pids-limit=2048`, batas CPU/memori, `tmpfs` | [V] E9, E10 |
| **P5** | Apa yang dikendalikan dari agy dan kiro? | agy: izin biner (`--dangerously-skip-permissions`, `--mode`, `--sandbox`), tanpa callback di `--help`, tanpa subcommand ACP. kiro: `acp --auth-method` hanya soal siapa menjawab permintaan **token** engine v3, **bukan** izin per aksi. Apakah `stream-json` agy memancarkan permintaan izin: **belum diuji** | [V] E7, E23 |
| **P6** | Batas waktu panggilan sinkron | Default timeout tool MCP klien Galleon 180 detik; komentar proto menyebut batas keras 1–300 detik. Jalur yang kini berlaku: gRPC streaming dari Rust ke Go, bukan long-poll | [V] E3, E6 |
| **P7** | Apakah Galleon sudah punya server MCP? | **Tidak ditemukan.** Pola implementasi server (`impl ServerHandler`, `serve(`, `"tools/list" =>`, `handle_tools_list`, `fn serve_stdio`) tidak menghasilkan temuan di repo; semua `McpServer*` adalah klien/konfigurasi. Keterbatasan: hanya pola yang dicoba | [V] E15 |
| **P8** | Apakah memori Go sudah mendukung provenance dan consent? | **Consent ya, provenance sebagian.** `MemoryProposal` berstatus pending/approved/rejected/reverted, bersifat versi dan dapat di-revert, bercakupan Fleet/Workspace/Project/Ship/Crew/Run. `Document` hanya punya `Metadata map[string]string` bebas; `MemoryProposal` tidak mencatat pembuat atau tujuan | [V] E20 |
| **P9** | Apakah provider yang ada selaras dengan ketentuan vendor? | **Dua tidak.** `openai_codex.rs` memanggil `chatgpt.com/backend-api/codex/responses` dengan token OAuth ChatGPT; provider Anthropic menerima setup-token langganan sebagai Bearer. `gemini_cli.rs` menjalankan binary resmi (pola yang dibolehkan staf Google) tetapi menarget CLI yang sudah diganti `agy` untuk tier gratis/Google One. Apakah jalur-jalur ini aktif default: **tidak diperiksa** | [V] E17, E18, E16; ketentuan [V] E24 |

**Konsekuensi untuk ADR ini:**
- Server MCP Galleon harus **dibangun dari nol** (P7). Lokasinya (Go atau proxy Rust) menunggu pemeriksaan terhadap `01-boundary-policy.md` (OQ1).
- Provenance penulis dan tujuan harus ditambahkan sebagai field wajib (P8).
- Jalur legal bermasalah di P9 harus ditangani sebelum rilis (D9).
- Sesi runtime berjalan menit sampai jam, jadi antarmuka antara Go dan Rust bersifat streaming dan asinkron.

---

## 4. Keputusan yang Diusulkan

### D1. Galleon sebagai orkestrator multi-runtime (menggantikan "produk mandiri")

- Setiap crew/agent terikat pada satu **runtime**: `native` (loop Galleon; default) atau adapter CLI headless. Hierarki ODR-03 (Quartermaster → Ship → Squad → Crew) tidak berubah.
- **Go memutuskan**: penugasan, kebijakan, persetujuan, state tugas, memori, audit, penerbitan token sesi (ODR-03, ODR-11, ODR-22).
- **Rust men-spawn dan mengurung**: proses CLI dijalankan hanya oleh Rust melalui RPC baru pada `SystemGateway`, dalam sandbox. Go dan UI tidak men-spawn proses. Ini mengikuti ODR-07 (Tauri/UI → Go → Rust sandbox) [I]. Pola sama dengan provider CLI yang sudah men-spawn subprocess di Rust [V, E16].
- **ADR 0001**: SSOT LLM di Rust berlaku untuk loop agen Galleon. Runtime eksternal memanggil modelnya sendiri; Galleon tidak membaca atau menyimpan token vendor mereka. Diperlukan errata cakupan (OQ7).
- Uji independensi: antarmuka sesi yang sama berjalan untuk adapter agy dan kiro tanpa perubahan API (T10, T12).

### D2. Server MCP Galleon (permukaan koordinasi untuk agen dalam sesi)

**Transport.** Streamable HTTP pada `127.0.0.1` atau Unix socket, dengan autentikasi token sesi. Klien MCP di CLI vendor memanggilnya sebagai server MCP biasa. agy mendukung server `http` dengan `--header` [V, E7]; dukungan runtime lain: **tidak diverifikasi langsung**. Cara menyuntik konfigurasi MCP **per sesi** tanpa mengubah konfigurasi global pengguna berbeda per CLI dan belum dipecahkan (OQ6).

**Token sesi.** Diterbitkan Go saat sesi dimulai; terikat ke `(session_id, task_id, crew_id)`; berlaku selama batas waktu sesi; tidak dapat dipakai sesi lain; disuntik ke proses anak lewat environment atau berkas sesi, tidak masuk prompt. Identitas penulis pada memori dan laporan **selalu** berasal dari token, bukan dari klaim agen.

**Tujuh tool v0.** Nama `snake_case`.

| Tool | Scope | Perilaku |
|---|---|---|
| `task_get` | read | Kontrak tugas: tujuan, kriteria penerimaan, batasan, penunjuk konteks, cakupan tulis yang diizinkan. Idempoten |
| `task_progress` | write-event | Menambah catatan progres non-terminal; dibatasi laju |
| `task_report` | write-report | Mengirim laporan akhir dengan bukti (path, commit, hasil uji). Server memvalidasi skema; menggeser tugas ke `reported`; idempoten menurut `(task_id, hash_laporan)`. **Tidak dapat menandai `verified`** |
| `memory_search` | read | Pencarian memori dalam cakupan yang diturunkan dari token (Ship/Crew/Project); hasil membawa provenance dan dibatasi ukurannya |
| `memory_propose` | write-proposal | Membuat usulan `pending` dengan `purpose`; server mengisi `author` dari token. Tidak menulis langsung ke store |
| `skill_list` | read | Skills yang tersedia bagi crew (format agentskills.io) |
| `skill_read` | read | Isi `SKILL.md` dan berkas pendukungnya; hanya-baca |

**Model kesalahan.** `isError: true` dengan kode terstruktur: `invalid_argument`, `not_found`, `forbidden_scope`, `unsupported`, `conflict`, `limit_exceeded`, `isolation_unavailable`, `internal`.

**Penegakan di sisi server.** Penutupan tugas hanya lewat `task_report` bermuatan bukti; status `verified` hanya diberikan gerbang independen yang dijalankan Go (bukan agen). Petunjuk risiko pada tool hanya saran bagi klien dan tidak dipercaya[^3].

**Permukaan kontrol sesi untuk klien luar.** Kontrol sesi oleh UI/CLI lewat Galleon Client Protocol (ODR-23). Fasad MCP untuk kontrol sesi oleh orkestrator luar (rancangan 10 tool di revisi 1, commit board `e962636`) **bukan v1**.

### D3. Model sesi dan log event

State sesi: `starting` → `running` ⇄ `waiting_permission`; `cancelling`; terminal: `completed`, `failed`, `cancelled`, `timed_out`, `lost`. State tugas (milik Go): `assigned` → `in_progress` → `reported` → `verified` | `rejected`; `blocked` dapat disisipkan. Nama state tugas final ditetapkan saat desain.

Event ternormalisasi, append-only, `seq` monoton per sesi: `state`, `message`, `tool_call` (nama, `args_digest`, status), `permission_request` (`request_id`, ringkasan aksi, `args_digest`, `expires_at`), `permission_decision`, `file_change`, `usage`, `log` (stderr dipotong), `error`, `context_projected` (hash isi berkas konteks), `task_report`. `args_digest` = SHA-256 argumen kanonik.

**Persistensi.** Store Go yang ditetapkan ODR-05 (SQLite lokal atau PostgreSQL), bukan basis data baru. **Pemulihan.** Saat daemon restart, sesi yang prosesnya hilang menjadi `lost`; log tetap utuh; tidak ada resume otomatis.

### D4. SPI Runtime di Rust

```
Runtime
  id        : string                          # "agy", "kiro", ...
  kind      : "acp" | "print-stream" | "rest-async"
  level     : L0 | L1 | L2                    # ditetapkan uji kepatuhan (D7)
  capabilities : { resume, send, permission_callbacks, structured_output, native_sandbox }
  context_targets : [path]                    # berkas yang dibaca runtime (D6)
  health()  -> { ok, detail }
  start(ctx: SessionContext) -> Handle
  send(h, text)                                # L1+
  resolve_permission(h, request_id, decision)  # L2
  cancel(h)
  events(h) -> stream<Event>                   # wajib berakhir dengan event terminal
  resume_token(h) -> string | null

SessionContext
  session_id, task_id, workspace_path, prompt, mode
  mcp_endpoint, session_token_ref
  env             : map (allowlist)
  credentials_dir : path (hanya-baca; dibaca hanya oleh CLI itu sendiri)
  state_dir       : path (tulis, per runtime)
  limits          : { wall_s, mem_mb, cpus, pids }
  isolation       : sandbox yang aktif (tidak boleh "none" di luar uji)
```

RPC `SystemGateway` baru (nama usulan): `StartRuntimeSession`, `StreamRuntimeEvents`, `SendRuntimeInput`, `ResolveRuntimePermission`, `CancelRuntimeSession`. Go memanggilnya seperti `ExecuteTurn` memanggil Rust hari ini.

**Tingkat kesesuaian.**

| Level | Kemampuan | Kandidat | Status |
|---|---|---|---|
| **L0** | `start`, `cancel`, `events` | agy mode print (`-p --output-format json`) | flag [V]; perilaku adapter belum diuji |
| **L1** | L0 + `send`, streaming, `resume` | agy `--input-format stream-json --output-format stream-json`, `--conversation` | flag [V]; perilaku belum diuji |
| **L2** | L1 + callback izin | agen ACP, target pertama `kiro-cli acp` | subcommand [V]; perilaku izin belum diuji; `--auth-method` bukan callback izin [V, E23] |

**Aturan adapter.**
1. Tidak menyentuh path di luar `ctx`.
2. Wajib memancarkan event terminal untuk setiap akhir proses.
3. Tidak menyalakan flag yang mematikan permintaan izin (mis. `--dangerously-skip-permissions`) kecuali kurungan proses aktif (D5-I1).
4. Menyunting kredensial dari event dan log.
5. Memetakan kode keluar ke state terminal.
6. **Tidak membaca, menyalin, atau meneruskan token OAuth/session vendor.** Direktori login CLI hanya dipasang hanya-baca agar CLI itu sendiri dapat memakainya (OQ4).

**Adapter v1.** `agy` (L0/L1) dan `kiro` (ACP, target L2) sebagai dua runtime spike (T12). Claude Code, Codex CLI, dan Qwen Code menyusul setelah tinjauan legal (D9) dan hanya dengan API key sebagai default untuk otomasi. Runtime `galleon-native` bukan adapter. Registry ACP memuat puluhan agen[^4] [S], tetapi kesesuaian tiap agen harus diuji [I].

### D5. Batas isolasi

| Lapis | Berlaku untuk | Isi |
|---|---|---|
| **I0** workspace | semua runtime eksternal, wajib | `git worktree` per sesi dari mirror (pola `sync_mirror` ada di `dev-ci` [V, E10]); cabang `session/<id>`; runtime tidak melihat checkout milik pengguna; path divalidasi sebelum setiap operasi workspace |
| **I1** proses | L0 dan L1, wajib | Kurungan lewat abstraksi sandbox Galleon (`create_sandbox`); **fail-closed**: bila hasilnya `NoopSandbox` untuk runtime eksternal, sesi ditolak dengan `isolation_unavailable`. Backend kandidat: Landlock (disebut di arsitektur System Core; belum diuji di host), atau kontainer Docker (terbukti di `dev-ci`). Pilihan: OQ2 |
| **I2** izin per aksi | L2 | Permintaan izin runtime menjadi event `permission_request`; keputusan lewat `ResolveRuntimePermission`; tanpa jawaban ditolak setelah batas waktu (fail-closed) |

**Kredensial.** API key milik pengguna disuntik dari vault ke environment sesi menurut allowlist per runtime. Token OAuth/session vendor tidak disentuh Galleon. Kredensial `git push` dan pembuatan PR tidak diberikan ke sesi; penerbitan dilakukan di luar sesi (OQ5). Pola ini mengikuti Symphony: kredensial tracker di sisi host, tidak diteruskan ke proses anak[^2] [S, S12].

**Sumber daya.** Batas sesi aktif global default 1 (host 4 core), antrean FIFO, `wall_s` default 3600 yang dapat diubah, serta CPU, memori, dan pids per sesi. Titik awal untuk disetel [I].

**Matriks penegakan (v1).**

| Kontrol | Ditegakkan oleh | L0/L1 | L2 | Status |
|---|---|---|---|---|
| Workspace terpisah | Rust (worktree) | wajib | wajib | direncanakan |
| Proses dikurung | Rust sandbox | wajib, fail-closed | wajib | direncanakan; backend belum diputuskan |
| Izin per aksi | Runtime + `ResolveRuntimePermission` | **tidak ada** | ada | bergantung adapter; belum diuji |
| **Kebijakan tool Galleon** (`PolicyEngine`, payment-lockout, DAC) | Go dan Rust, atas tool Galleon | **tidak berlaku** atas tool internal CLI vendor | sama | **diakui**; runtime eksternal tidak ditugaskan pekerjaan commerce/finansial |
| Kredensial | Rust (vault) + allowlist | ya | ya | direncanakan |
| Push dan PR | di luar sesi | sama | sama | OQ5 |
| Jaringan | sandbox/Docker bridge | **residual**: dapat menjangkau LAN dan layanan host | sama | diakui |
| Batas sumber daya | sandbox + Go | ya | ya | direncanakan |
| Otorisasi pemanggil MCP | Go (token sesi) | ya | ya | direncanakan |
| Isi percakapan dengan vendor | tidak ada | **tidak terlihat dan tidak dikontrol** | sama | diakui |

**Residual yang diakui.** Isi workspace dikirim ke vendor sebagai bagian dari kerja harness. Memori internal harness (percakapan agy, memori kiro) di luar kendali Galleon.

### D6. Konteks per runtime: proyeksi deterministik

**Masalah.** Tiap runtime membaca berkas konteks di workspace-nya sendiri; menulis tangan per runtime menimbulkan duplikasi dan drift. Contoh terukur di luar produk: 17 berkas, 95.115 byte, tiga format (`AGENTS.md`; `.gemini/*` dan `~/.gemini/GEMINI.md`; `.kiro/steering/*`) [V, riset induk I8].

**Usulan.** Satu sumber kanonik (steering Galleon global dan workspace, `AGENTS.md`, skills agentskills.io) diproyeksikan secara **deterministik** ke berkas yang dibaca tiap runtime, di dalam worktree sesi. Berkas hasil proyeksi tidak ikut di-commit ke repo pengguna. Masukan yang sama menghasilkan keluaran identik; hash isi dicatat sebagai event `context_projected`.

Urutan penggabungan: steering global → steering workspace → peran crew → kontrak tugas.

**Target proyeksi (kandidat, perlu dibuktikan oleh uji C1):**

| Runtime | Berkas konteks | Status |
|---|---|---|
| agy | `AGENTS.md`, `.agents/skills/*/SKILL.md`; string `GEMINI.md` ada di binary | `AGENTS.md` dan skills terbukti dimuat (n=1) [V, riset induk I4]; `CLAUDE.md` tidak ditemukan di binary [V, riset induk I3] |
| KiroCrew (referensi) | `AGENTS.md`, `.kiro/steering/*` | terbukti dimuat [V, riset induk I10] |
| kiro-cli (ACP) | belum diketahui | [?] |
| Claude Code, Codex CLI, Qwen Code | `CLAUDE.md`, `AGENTS.md`, dst. | [?] belum diuji |

**Sumber kanonik belum ditetapkan.** Lokasi dan format steering kanonik Galleon belum ditetapkan; ada desain di `archive/dev-task-2-standalone-docs/steering-end-user-design-spec.md` yang belum kubaca (OQ8). Galleon sudah memuat file identitas workspace (SOUL, IDENTITY, USER, AGENTS, TOOLS, HEARTBEAT, BOOTSTRAP, MEMORY) lewat `personality.rs` [V, E21]; mekanisme proyeksi dapat memanfaatkan konvensi itu [I].

### D7. Onboarding dan uji kepatuhan

Runtime baru melewati alur:

1. Pendaftaran adapter (tipe, biner, tujuan konteks).
2. `health()`.
3. **Uji kepatuhan** (di bawah).
4. Penetapan level L0/L1/L2 dari hasil uji.
5. Agen **boleh mengusulkan** tambahan aturan lewat `memory_propose`; Owner menyetujui. Agen tidak menulis aturan kanonik. Ini sejalan dengan *learning by consent* [V, E20] dan larangan melemahkan batas kepercayaan di `AGENTS.md` repo.
6. Aktivasi per crew oleh Go.

**Uji kepatuhan.**

| Kode | Uji | Lulus bila |
|---|---|---|
| C1 | Konteks termuat | Kata sandi acak di berkas proyeksi disebutkan dengan benar oleh runtime |
| C2 | MCP terjangkau | `task_get` dengan token sesi berhasil; token sesi lain ditolak |
| C3 | Batas dihormati | Upaya menulis di luar worktree ditolak sandbox |
| C4 | Laporan sesuai skema | `task_report` diterima; laporan tanpa bukti ditolak |
| C5 | Event terminal | Proses dibunuh → event terminal tetap dipancarkan |
| C6 | Tidak ada kredensial bocor | Variabel canary dan berkas token tidak ada di sesi |

Hasil uji menentukan level; runtime tidak lulus tidak ditugaskan. Uji perilaku yang pernah dilakukan hanya untuk agy dan terbatas pada C1 [V].

### D8. Memori bersama dan provenance

- **Satu store**: memori Go (cakupan Fleet/Workspace/Project/Ship/Crew/Run). Memori internal CLI vendor bukan bagian sistem.
- **Tulisan runtime eksternal selalu berupa proposal** `pending` yang disetujui lewat jalur consent yang ada.
- **Provenance wajib** (ditambahkan sebagai field, bukan `Metadata` bebas): `author` = `{principal, runtime, session_id}`, `purpose`, `source_task`. Disarankan selaras dengan skema memori yang sudah teruji di KiroCrew: `source`, `scope`, `confidence`, `valid_from`, `observed_at`, `revision`, `content_hash` [V, riset induk: ringkasan poin 6 dan tabel perbandingan skema].
- **Identitas dari token sesi**, bukan klaim agen.
- **Tidak dapat dipaksa**: agen vendor tidak dapat dipaksa "ingat menulis". Karena itu Galleon menyuntik konteks relevan ke tugas, dan penutupan tugas mensyaratkan `task_report`; memori yang berguna ditangkap dari laporan dan event, bukan dari disiplin agen [I].

### D9. Invarian legal vendor

Ketentuan vendor adalah pembacaan teks publik oleh penulis, **bukan nasihat hukum**[^6]. Ringkas (rincian di dokumen riset pendamping):

| Jalur | Anthropic | Google | OpenAI |
|---|---|---|---|
| API key | Diwajibkan untuk produk [V] | Didukung [V] | Diizinkan [A] |
| Binary resmi, login sendiri, lokal | Tidak dilarang tertulis [V] | Diizinkan menurut staf, bersyarat [V] | Abu-abu [V/I] |
| Mengambil atau memproksi token | Dilarang tertulis [V] | Pelanggaran [V] | Berisiko [V/I] |

**Invarian yang diusulkan:**
1. Hanya binary resmi yang tidak dimodifikasi.
2. Tidak membaca, menyalin, atau meneruskan token OAuth/session.
3. Login langganan hanya milik pengguna, lokal, satu pengguna, volume rendah/interaktif.
4. Otomasi kontinu atau paralel tinggi memakai API key.
5. Tidak ada layanan hosted/bersama, pooling, atau perputaran kredensial.
6. Nama dan logo vendor hanya sebagai teks biasa.
7. Provider yang memanggil backend vendor dengan token langganan (bukan lewat binary resmi), yaitu `openai_codex.rs` dan jalur setup-token Anthropic, **default nonaktif**; pengaktifan memerlukan keputusan Owner eksplisit.
8. Ketentuan diverifikasi ulang tiap rilis.

### D10. Integrasi

- **ACP:** Galleon sebagai agen ACP lewat `galleon-acp-bridge` (ODR-24); sebagai klien ACP terhadap runtime ACP (kiro, dan lainnya) lewat adapter Rust. Server ACP lama berada di `runtime/src/acp/` yang berada di wilayah R-00 dan R-42 akan mengubah targetnya, jadi jalur ini bisa bergeser [V, E22].
- **Galleon Client Protocol (ODR-23):** UI dan CLI mengendalikan sesi lewat Go.
- **Orkestrator luar** (mis. KiroCrew) yang ingin mengendalikan Galleon: fasad MCP untuk kontrol sesi bukan v1.

### D11. Bukan tujuan v1, dan versi

Bukan tujuan v1: layanan hosted multi-pengguna atau akses jarak jauh publik untuk runtime eksternal (butuh keputusan setara ODR-06 dan tinjauan legal); pooling atau pemakaian bersama kredensial; fasad A2A; Kubernetes; layanan memori terpisah; pekerjaan commerce atau finansial oleh runtime eksternal (DAC tetap gate wajib). Versi: perubahan antarmuka MCP bersifat aditif; pemecah kompatibilitas memakai nama tool baru.

---

## 5. Alternatif yang Dipertimbangkan

| Alternatif | Putusan | Alasan |
|---|---|---|
| **Produk mandiri di luar Galleon (usulan revisi 1)** | Tidak dipilih untuk v1 | Pilihan arah Owner: Galleon sendiri menjadi harness. Keunggulan revisi 1 (tidak menyentuh ODR, terpisah dari perubahan ketentuan vendor) hilang; sebagai gantinya diperlukan ODR baru. Pemisahan tetap mungkin kelak bila beban lisensi atau risiko vendor menuntutnya [I] |
| Plugin WASM di Galleon | Ditolak | Berjalan in-process di Wasmtime. `PluginPermission` hanya `HttpClient`, `WebSocketClient`, `SocketClient`, `FileRead`, `FileWrite`, `ConfigRead`, `MemoryRead`, `MemoryWrite`; `wit/v1` hanya berisi `README.md` dan `types.wit`. Tidak ada izin men-spawn proses [V, E14] |
| Add-on terkompilasi (Tier B) | Ditolak | Mekanisme Tier B didefinisikan untuk channel; memaksa pengecualian ODR-03 dan ADR 0001 ke inti tanpa batas yang jelas [I] |
| Men-spawn dari engine Go | Ditolak | Go dilarang melakukan operasi OS dan men-spawn proses (boundary policy Tier 3 [V, E13]); engine tidak punya `exec.Command` non-test [V, E1] |
| CLI sebagai provider satu-giliran saja (yang ada) | Dipertahankan sebagai tingkat 2, tidak cukup | Galleon tetap memegang loop dan CLI sekadar pengganti LLM; tidak memberi agen vendor otonom penuh, sehingga tidak menjawab tujuan multi-runtime [I, E16] |
| Adopsi Symphony atau Agent Orchestrator apa adanya | Belum diputuskan | Belum dijalankan; asumsi harness utamanya Codex/Claude. Dapat dipakai sebagai referensi implementasi [I] |

---

## 6. Konsekuensi

**Positif.**
- Satu orkestrator, satu memori, satu alur kerja untuk runtime native dan eksternal.
- Memanfaatkan fondasi yang sudah ada: memori bercakupan dengan consent, `AGENTS.md` dan skills agentskills.io, ACP bridge, binding provider per agen [V].
- Kepatuhan ditegakkan oleh server MCP dan gerbang, bukan oleh prompt.
- Menutup celah isolasi dengan satu penegak (Rust), bukan per bridge.

**Negatif dan risiko.**
- **Lingkup besar.** Adapter, server MCP, onboarding, proyeksi konteks, dan isolasi. Galleon belum rilis dan baseline CI masih merah di beberapa gerbang [V]. Ukuran kerja tidak diestimasi.
- **Bukti baru satu runtime.** Percobaan di luar produk baru menjalankan satu runtime eksekutor (agy). Gerbang bukti dua runtime (T12) harus lulus sebelum desain dikunci.
- **ODR dan ADR tersentuh** (ODR-03/07/11/22, ADR 0001); sah hanya lewat ODR baru.
- **Kebijakan tool Galleon tidak mencakup tool internal vendor.** Penegakan atas runtime eksternal terbatas pada isolasi dan, bila ada, callback izin L2.
- **Izin tidak seragam.** Hanya runtime dengan callback izin yang bisa L2; sisanya aman hanya karena I0 + I1.
- **Backend sandbox belum terbukti di host pengembangan** (`bwrap` tidak dapat dipakai; Landlock belum diuji).
- **Ketentuan vendor berubah cepat** dan dua provider yang ada perlu ditinjau (D9).
- **Isolasi jaringan residual** (D5).
- Kategori produk ini ramai (Symphony, Agent Orchestrator, dan lainnya[^5] [S]); diferensiasi bersandar pada organisasi AI, memori persisten dengan consent, dan kepatuhan yang ditegakkan, bukan pada orkestrasi semata [I].

---

## 7. Kriteria Penerimaan (dapat diuji)

| # | Uji | Lulus bila |
|---|---|---|
| T1 | Dua sesi paralel di dua worktree | `git status` checkout pengguna tidak berubah; sesi A tidak bisa membaca berkas canary sesi B |
| T2 | Token sesi dipakai di sesi/tugas lain | `forbidden_scope`; memori di luar cakupan token tidak terbaca |
| T3 | `task_report` dua kali dengan isi sama; lalu tanpa bukti | Pertama idempoten; tanpa bukti ditolak; agen tidak dapat menyetel `verified` |
| T4 | `memory_propose` dari runtime eksternal | Tercatat `pending` dengan `author`/`runtime`/`session`/`purpose`/`source_task` dari token; tidak ada tulisan langsung ke store |
| T5 | Adapter L2: permintaan izin | Muncul sebagai event; tanpa jawaban → `deny` setelah batas waktu; `allow_once` → sesi melanjutkan |
| T6 | Sandbox tidak tersedia (`NoopSandbox`) | Sesi ditolak `isolation_unavailable`; tidak ada proses runtime yang berjalan |
| T7 | Restart daemon saat sesi aktif | Sesi tanpa proses menjadi `lost`; log utuh |
| T8 | Variabel env dan berkas token canary | Tidak ada di dalam sesi; Galleon tidak membuka direktori login CLI (pemeriksaan statis dan runtime) |
| T9 | `session_cancel` | Proses berhenti ≤ 10 detik dan worktree dilepas |
| T10 | Uji kepatuhan C1–C6 untuk agy dan kiro | Hasil deterministik; level ditetapkan; runtime gagal tidak dapat ditugaskan |
| T11 | Proyeksi konteks dijalankan dua kali | Berkas identik byte-per-byte; tidak ada berkas proyeksi di commit repo pengguna |
| T12 | **Spike dua runtime eksekutor** (agy dan kiro) mengerjakan tugas yang sama | Keduanya lulus T10; hasil dinilai gerbang independen; tidak ada tulisan di luar worktree; provenance lengkap; tidak ada kredensial bocor |

---

## 8. Pertanyaan Terbuka

1. **Lokasi server MCP.** Opsi A: di Go (memiliki tugas dan memori; HTTP :9090 sudah ada). Opsi B: front MCP tipis di Rust yang meneruskan ke Go. Pertimbangan: tugas Q-2 di arsip dev-tasks menghapus `tool/mcp_client.go` dan `tool/plugin.go` dari Go dengan catatan "MCP client dibuat ulang di Rust bila dibutuhkan" [V, E25], jadi menaruh permukaan MCP di Go berlawanan dengan arah yang sudah diambil (Q-2 adalah centang rekomendasi di dev-tasks, bukan ODR). Opsi B membutuhkan arah panggilan Rust → Go yang hari ini belum ada (gRPC yang ada berarah Go → Rust). `01-boundary-policy.md` belum dibaca penuh.
2. **Primitif I1**: Landlock (tersedia, belum diuji) atau Docker (terbukti di `dev-ci`), dan interaksinya dengan `create_sandbox`.
3. **Runtime v1 dan daftar berikutnya**: agy dan kiro diusulkan; urutan Claude Code, Codex CLI, Qwen Code menunggu tinjauan legal.
4. **Direktori login CLI**: apakah memasangnya hanya-baca ke sandbox, agar CLI memakainya sendiri, dianggap "meneruskan kredensial" menurut vendor (Google: "No OAuth tokens, cookies, or credentials are extracted, read, or passed").
5. **Siapa yang `push` dan membuat PR**: tool `workspace_publish` di Go/Rust, atau pemanggil.
6. **Konfigurasi MCP per sesi**: bagaimana tiap CLI menerima server MCP tanpa mengubah konfigurasi global pengguna. `agy mcp add` "menambah atau memperbarui konfigurasi server MCP" [V, E7]; lokasi penyimpanan dan cakupannya (pengguna atau proyek) **tidak diperiksa**, dan mekanisme runtime lain belum diselidiki.
7. **Errata ADR 0001** dan penyesuaian `01-boundary-policy.md` serta `galleon-product-definition.md` setelah ratifikasi.
8. **Sumber kanonik konteks**: lokasi dan format steering Galleon; lihat desain arsip.
9. **Apakah `stream-json` agy memancarkan permintaan izin**: menentukan apakah agy dapat naik ke L2.
10. **Kebijakan kredensial default**: langganan untuk pemakaian ringan, API key untuk loop otomatis (keputusan Owner; biaya per token vs risiko akun).
11. **Hubungan dengan tier komunitas dan lisensi**: apakah mengirim adapter yang menjalankan CLI vendor sesuai dengan tier yang direncanakan.
12. **Nama crate dan tool** mengikuti ODR-19 (`galleon-*`).
13. **Penanganan `openai_codex.rs`, setup-token Anthropic, dan `gemini_cli.rs`** (D9-7).

---

## 9. Log Koreksi

| # | Pernyataan sebelumnya | Setelah verifikasi |
|---|---|---|
| 1 | Chat 2026-10-18 (revisi 1): "tidak menemukan kode produksi yang memasang `McpCommandBoundary`" | **Salah.** Terpasang di `runtime/src/tools/mod.rs:751`; pencarianku memotong keluaran dengan `head -6` [V]. |
| 2 | Chat yang sama: "`apply_default_mcp_sandbox` bukan pengurungan OS, jadi sandbox MCP Galleon belum nyata" | **Sebagian benar.** Fungsi itu fallback; jalur produksi memakai boundary yang membungkus perintah dengan sandbox runtime, efektivitas bergantung `create_sandbox` yang bisa `NoopSandbox` (P2). |
| 3 | Roadmap R-60 masih `[ ]` | Kemungkinan usang (commit `f2af74175`); kriteria penerimaannya **tidak diverifikasi**. |
| 4 | "Jalur Go ke klien MCP belum terbukti" | Terverifikasi **tidak ada** (P1). |
| 5 | Revisi 1 dan chat: board, `agy-bridge`, `dev-ci` diperlakukan sebagai "yang sudah ada" untuk Galleon | **Salah bingkai.** Itu percobaan di luar produk; D1 diganti (Catatan Revisi 2). |
| 6 | Chat: "`prompt.rs` memuat `AGENTS.md` ke prompt agen" | **Salah.** Pemuatan produksi ada di `personality.rs:10-19`; di `prompt.rs` hanya blok uji (E21). |
| 7 | Sub-agen: Kiro punya callback izin lewat `--auth-method client` | **Ditolak.** Opsi itu hanya soal token engine v3 (E23). |
| 8 | Revisi 1: `agy 1.4.0` | `agy --version` = 1.4.2; tidak ada subcommand ACP di `--help` (E23). |
| 9 | Revisi 1 §2: "berbenturan dengan empat prinsip lain" (termasuk "tanpa multi-agent spawning generik") | **Tidak ditemukan ulang**; dicabut. Yang dirujuk hanya ODR-03/07/11/22 dan ADR 0001 [V]. |
| 10 | Chat: Anthropic tidak mengizinkan login langganan untuk program pihak ketiga | **Lebih bernuansa:** pengguna boleh masuk ke binary Claude Code yang tidak dimodifikasi dengan langganannya sendiri, termasuk bila platform menghostingnya; yang dilarang adalah merutekan permintaan lewat kredensial paket, mengumpulkan atau menyimpan token, dan menawarkan login claude.ai di aplikasi sendiri [V, E24]. |

---

## 10. Rujukan dan Bukti

### A. Sumber eksternal

ID `S` sama dengan dokumen riset induk §11-A; ketentuan vendor memakai ID `X` pada dokumen riset lanjutan §11. Yang dipakai ADR ini:

| ID | Sumber | URL | Tingkat baca | Dipakai untuk |
|---|---|---|---|---|
| S6 | Blog MCP, "MCP joins the Agentic AI Foundation" | http://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/ | CUPLIKAN | Status MCP sebagai standar terbuka |
| S10 | DEV, "Agent Client Protocol (ACP): Connect Any AI Agent to Any Editor" | https://dev.to/dmaxdev/agent-client-protocol-acp-connect-any-ai-agent-to-any-editor-2p0m | SEBAGIAN | Registry ACP |
| S12 | OpenAI, Symphony SPEC.md | https://github.com/openai/symphony/blob/main/SPEC.md | SEBAGIAN (±8.000 dari 89,9 KB) | Komponen, kredensial tracker sisi host, workspace per issue |
| S18 | Augment Code, "9 Open-Source Agent Orchestrators for AI Coding (2026)" | https://www.augmentcode.com/tools/open-source-agent-orchestrators | SEBAGIAN (artikel vendor) | Worktree sebagai primitif isolasi konsensus |
| S21 | Dokumentasi agent-sandbox | https://agent-sandbox.sigs.k8s.io/docs/ | CUPLIKAN | Identitas stabil dan workspace persisten per agen |
| X1–X5 | Ketentuan Anthropic, Google, OpenAI yang dibaca langsung | lihat dokumen riset lanjutan §11 | [V] | D9, Log Koreksi 10 |

### B. Bukti internal (dapat diulang)

Versi: `agy 1.4.2`, `kiro-cli 2.29.0`, `kirocrew 0.9.0`; `galleon-fleet origin/testing = 295d7a706`; kernel `7.0.0-38-generic`; `dev-ci HEAD = 3dbceecbf4`.

| ID | Bukti | Cara mengulang |
|---|---|---|
| E1 | Referensi MCP di engine Go | `grep -rIlic mcp engine --include=*.go \| grep -v _test` → `engine/pkg/pb/agent_service.pb.go` (3), `engine/src/tool/interfaces.go`, `services.go`, `dto.go` (1 masing-masing). Hanya komentar `services.go:446` dan `dto.go:87` untuk sumber bertanda `mcp` |
| E2 | Roadmap | `grep -ciE '\bMCP\b' standard-docs/roadmap/G-go-engine.md` → 0; baris MCP hanya R-60..R-63 di `R-rust.md` |
| E3 | Gateway dan proto | `crates/clawcrew-gateway/src/grpc_system_gateway.rs:14` (`ALLOWED_TOOLS`), `:438-444` (penolakan); `proto/agent_service.proto:113-118` (`ToolCallRequest`, `timeout_seconds` "hard timeout (1-300s)"); `:149-151` (`ExecuteTurnRequest`, field `model`) |
| E4 | Pemasangan boundary | `crates/clawcrew-runtime/src/tools/mod.rs`: `:731` (`runtime_shell_assembly`), `:751` (`set_mcp_command_boundary(Some(..))`), `:769` dan `:1111` (pemanggil). `git log -S"RuntimeMcpCommandBoundary" origin/testing -- crates/clawcrew-runtime/src/tools/mod.rs` → `f2af74175 2026-10-07 feat(BL-19)` |
| E5 | Pabrik sandbox | `crates/clawcrew-runtime/src/security/detect.rs:353` (`create_sandbox`): `NoopSandbox` bila backend `None`/dimatikan, runtime Docker terpilih, atau backend diminta tidak tersedia |
| E6 | Transport MCP | `crates/clawcrew-tools/src/mcp_transport.rs:55`, `:696-707`; `crates/clawcrew-config/src/schema.rs:5552` (`McpTransport`), `:5673` (`tool_timeout_secs`); `crates/clawcrew-tools/src/mcp_client.rs:31` (`DEFAULT_TOOL_TIMEOUT_SECS = 180`) |
| E7 | agy | `agy --help`; `agy mcp add --help` (tipe `stdio`/`http`, `--header`) |
| E8 | kiro-cli | `kiro-cli --version` → 2.29.0; `kiro-cli acp --help` → "Start Agent Client Protocol (ACP) agent" |
| E9 | Isolasi host | `unshare -Ur true` → "Operation not permitted"; `cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns` → 1; `cat /sys/kernel/security/lsm` memuat `landlock`; `command -v bwrap` → `/usr/bin/bwrap` |
| E10 | dev-ci | `~/Apps/dev-ci/bin/ci-poller`: `:112` (`sync_mirror`), `:133-135` (`--network`, `--cpus`, `--memory`, `--pids-limit=2048`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--tmpfs`) |
| E11 | ACP bridge dan server | `src/bin/clawcrew-acp-bridge.rs` (702 baris); `Cargo.toml:117-119`, `:322` (fitur `acp-bridge`); `crates/clawcrew-runtime/src/acp/server.rs` |
| E12 | Bridge agy (percobaan di luar produk) | `~/Apps/board/tools/agy-bridge/board_agy_bridge.py:201-203,213` (`--dangerously-skip-permissions`, `--add-dir`) |
| E13 | Dokumen baku | `decisions/owner-decisions/ODR-2026-10-04-product-direction.md` (ODR-03, ODR-07), `...-addendum-1.md` (ODR-11, ODR-12), `...-addendum-4.md` (ODR-22, ODR-23, ODR-24); `decisions/0001-llm-ssot-rust.md`; `decisions/adr-wasm-plugin-vs-mcp.md:10-11,35-36`; `tech-standart/architecture/01-boundary-policy.md`; `engine/src/tool/policy.go:52` |
| E14 | Plugin WASM | `crates/clawcrew-plugins/src/lib.rs:123` (`enum PluginPermission`, 8 varian); `ls wit/v1` → `README.md`, `types.wit` |
| E15 | Server MCP tidak ditemukan | `grep -rnE 'impl ServerHandler\|ServiceExt.*serve\(\|"tools/list" *=>\|handle_tools_list\|fn serve_stdio' --include=*.rs .` → kosong (2026-10-18); `grep -rn 'McpServer' crates --include=*.rs` → hanya klien dan konfigurasi (`mcp_client.rs`, `mcp_transport.rs`, `schema.rs`) |
| E16 | Provider CLI | `crates/clawcrew-providers/src/gemini_cli.rs:1-40` ("Gemini CLI subprocess model_provider", biner `gemini`, timeout 120 detik), `kilocli.rs:1-30` (biner `kilo`), `grok_cli.rs:1-25` (ACP `grok agent stdio`, login cache CLI); registrasi di `factory.rs:1724-1800` |
| E17 | Jalur backend OpenAI | `crates/clawcrew-providers/src/openai_codex.rs:21` (`DEFAULT_CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"`), `:1329` (header `originator: pi`), `:1219-1273` (`oauth_access_token`); `factory.rs:1260` ("Codex variant routing: OAuth subscription auth → Codex responses protocol") |
| E18 | Setup-token Anthropic | `crates/clawcrew-providers/src/anthropic/mod.rs:196` (`ANTHROPIC_OAUTH_BETA_FEATURES`), `:709-727` (`is_setup_token`: awalan `sk-ant-oat01-`), `auth/anthropic_token.rs:9` ("Subscription / setup token via `Authorization: Bearer`") |
| E19 | Binding provider per agen | `crates/clawcrew-config/src/schema.rs:4068` (`AliasedAgentConfig`), `:4084` (`model_provider: ModelProviderRef`); `engine/src/{crew,orchestrator,fleet}/services.go` memanggil `gateway.ExecuteTurn(`; cara binding sampai ke Go: tidak ditelusuri |
| E20 | Memori Go | `engine/src/memory/interfaces.go` (`Document{ID, Content, Embedding, Metadata, Scope}`, `MatchesScope`), `engine/src/memory/proposal.go` (`MemoryProposal`, `ProposalStatus`, `ProposalStore`); `scope_isolation_test.go` ada |
| E21 | Konteks dan skills | `crates/clawcrew-runtime/src/agent/personality.rs:10-19` (`PERSONALITY_FILES`), `agent/prompt.rs` (AGENTS.md hanya di blok uji, `#[cfg(test)]` baris 590); `crates/clawcrew-plugins/src/host.rs:648-652` (validasi `SKILL.md` agentskills.io); `crates/clawcrew-runtime/src/skills/` |
| E22 | ACP dan Client Protocol di roadmap | `standard-docs/roadmap/PR-plan.md` PR-51, PR-58; `R-rust.md` R-42; `G-go-engine.md` G-36; `N-rename-and-legacy-cleanup.md` N-20 |
| E23 | agy dan kiro, versi dan opsi | `agy --version` → 1.4.2; `agy --help \| grep -ci acp` → 0; `kiro-cli acp --help` memuat `--agent-engine`, `--trust-tools`, dan `--auth-method` ("Authentication owner for the v3 engine … use \"client\" to answer the engine's access-token requests from the ACP client") |
| E24 | Ketentuan vendor | Halaman dibaca langsung 2026-10-18: Anthropic Legal and compliance (X1); Gemini CLI tos-privacy (X2); forum Google staf 7 Okt 2026 (X3); OpenAI Terms of Use (X4); Gemini CLI headless banner (X5) |
| E25 | Q-2 dev-tasks | `standard-docs/archive/dev-tasks/08-carryover-from-finalize.md:40` ("**Q-2 `tool/plugin.go` & `tool/mcp_client.go`:** hapus … atau pindah ke Rust plugin host. MCP client dibuat ulang di Rust bila dibutuhkan"); `archive/research-closed-loop/fleet-wide-mcp-governance-followup.md:84` (verifikasi: `plugin.go`/`mcp_client.go` sudah tidak ada) |

---

## 11. Catatan Kaki

[^1]: ADR `adr-wasm-plugin-vs-mcp.md` (Accepted, Sprint 5, BL-22) baris 35 menyebut MCP dipakai "untuk memanfaatkan ekosistem open-source MCP yang sudah ada (alat CLI, bridge database, integrasi sistem operasi)" dan baris 36 mewajibkan eksekusi MCP stdio melalui `apply_default_mcp_sandbox`. Pernyataan terakhir menggambarkan fallback; jalur produksi memakai boundary (§3, P2).
[^2]: Spesifikasi Symphony (S12) dibaca sebagian: komponen §3.1, goals dan non-goals §2, serta kredensial tracker sisi host. State machine, retry, dan rekonsiliasi tidak terbaca (lihat dokumen induk, catatan kaki 7).
[^3]: Spesifikasi MCP mendefinisikan anotasi tool berupa petunjuk (mis. hanya-baca, destruktif). Ini pengetahuan umum penulis dan **tidak diverifikasi pada sesi ini**. Karena petunjuk dikirim server dan klien tidak dapat memverifikasinya, penegakan scope tetap di sisi server.
[^4]: Dokumen induk catatan kaki 5: registry ACP melaporkan 50 agen per Juni 2026 (sumber sekunder, S10); kesesuaian per agen tidak diuji.
[^5]: Dokumen induk §5.2 dan catatan kaki 11: ringkasan orkestrator berasal dari artikel vendor pesaing (S18).
[^6]: Ketentuan vendor dibaca dari halaman publik pada 2026-10-18. Pernyataan staf Google di forum adalah penjelasan, bukan teks ToS; laporan sub-agen ([A]) tidak dibaca ulang oleh penulis. Ini bukan nasihat hukum; keputusan risiko akun dan lisensi tetap pada Owner.
