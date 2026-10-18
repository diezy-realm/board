---
title: ADR (Usulan) — Antarmuka Control Plane Mandiri: Permukaan MCP, SPI Runtime, Batas Isolasi
status: draft
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: control-plane-multi-runtime-landscape-2026-10-18.md
---

# ADR (Usulan): Antarmuka Control Plane Mandiri

> **Status: Diusulkan (Proposed).** Dokumen ini belum mengikat. Menurut konvensi proyek, keputusan hanya final bila Owner menerimanya dan mencatatnya sebagai ODR/ADR di repo produk (untuk Galleon: `standard-docs/decisions/owner-decisions/`). Selama itu belum terjadi, isi di bawah adalah rekomendasi.
>
> **Cara membaca bukti.** Klaim penting diberi tag:
> - **[V]** diverifikasi sendiri dengan perintah atau uji pada 2026-10-18 (UTC). Perintah dan hasilnya ada di §10-B (ID `E1`…`E14`).
> - **[S]** dilaporkan sumber luar, tidak diverifikasi mandiri. Rujukan di §10-A (ID `S` sama dengan dokumen riset induk).
> - **[I]** inferensi atau penilaian penulis.
>
> Angka `[^n]` menunjuk catatan kaki di §11.
>
> **Dokumen induk:** `control-plane-multi-runtime-landscape-2026-10-18.md` (riset). ADR ini mengubah salah satu rekomendasinya menjadi rancangan antarmuka konkret setelah Achmad memilih bentuk "produk mandiri, opsional untuk Galleon".

---

## 1. Ringkasan Usulan

Bangun **control plane mandiri** (daemon lokal, repo dan siklus rilis sendiri) yang menjalankan harness agen pihak ketiga dalam sesi terisolasi, dengan tiga antarmuka yang dikunci oleh dokumen ini:

| # | Usulan | Intinya |
|---|---|---|
| D1 | Produk mandiri | Tidak mengimpor kode Galleon; interaksi hanya lewat MCP, ACP, dan HTTP |
| D2 | Permukaan koordinasi = server MCP | 10 tool, asinkron untuk sesi panjang, otorisasi per klien dengan scope |
| D3 | Model sesi dan log event | State machine tetap, event ternormalisasi, tersimpan di SQLite |
| D4 | SPI Runtime | Kontrak adapter dengan tiga tingkat kesesuaian (L0, L1, L2) |
| D5 | Batas isolasi | Worktree per sesi (wajib), kontainer untuk runtime tanpa callback izin (wajib, fail-closed), kredensial dan git push di luar sesi |
| D6 | Integrasi | Klien: agy, KiroCrew, board bridge. Galleon: sebagai runtime lewat ACP bridge yang sudah ada. Arah Galleon memanggil control plane **belum punya jalur** (§3, P1) |
| D7 | Bukan tujuan v1 | Multi-tenant, akses jarak jauh, publikasi otomatis, layanan memori, UI, A2A |
| D8 | Versi dan kompatibilitas | Perubahan aditif; nama tool stabil |

---

## 2. Konteks

- Riset induk menyimpulkan bahwa lapisan koordinasi multi-harness berbeda kelas dari Galleon: Galleon menegakkan kebijakan di dalam loop agennya sendiri (Go → Rust sandbox), sedangkan harness pihak ketiga hanya bisa dipagari dari luar.
- Opsi "Galleon menjadi host banyak runtime" dianalisis dampaknya terhadap ODR-03 dan ODR-11. Hasilnya: hanya sah lewat ODR baru dan berbenturan dengan empat prinsip lain. Achmad lalu menanyakan bentuk opsional/mandiri.
- Bentuk plugin WASM tidak layak (§5). Bentuk server MCP mandiri sejalan dengan ADR `adr-wasm-plugin-vs-mcp.md` yang menyatakan MCP sebagai jalur untuk alat CLI dan integrasi OS[^1] [V, E13].
- Komponen yang diperlukan memetakan ke spesifikasi OpenAI Symphony: Workspace Manager, Agent Runner, Orchestrator, Status Surface[^2] [S, S12]. Board + bridge + dev-ci hari ini hanya memiliki sebagian (tidak ada Workspace Manager; Agent Runner terikat pada agy).
- Pemicu praktis: bridge menjalankan agy dengan `--dangerously-skip-permissions` dan akses tulis ke checkout utama [V, E12].

---

## 3. Verifikasi Prasyarat (2026-10-18)

Permintaan Achmad: verifikasi dulu jalur Go ke klien MCP dan siapa yang memasang `McpCommandBoundary` di produksi.

| # | Pertanyaan | Hasil | Tag, bukti |
|---|---|---|---|
| **P1** | Apakah engine Go bisa memanggil server MCP? | **Tidak ada jalur.** Hanya 4 berkas Go non-test menyebut MCP: kode hasil-generate `agent_service.pb.go` (3 kali) dan `tool/{interfaces,services,dto}.go` (1 kali masing-masing). Tidak ada kode Go yang meregistrasi tool bersumber `mcp:*`; yang ada hanya komentar dan field `Source` (`dto.go:87`, `services.go:446`). Roadmap Go (`G-go-engine.md`) memuat 0 baris MCP. Gateway gRPC `ExecuteNativeTool` menolak tool di luar `ALLOWED_TOOLS`, dan `ToolCallRequest` tidak punya field server atau tool MCP | [V] E1, E2, E3 |
| **P2** | Siapa memasang `McpCommandBoundary` di produksi? | **Terpasang.** `runtime_shell_assembly` (`runtime/src/tools/mod.rs:731`) membuat `RuntimeMcpCommandBoundary` dan memanggil `set_mcp_command_boundary(Some(..))` (baris 751); dipanggil dari baris 769 dan 1111. Ditambahkan commit `f2af74175` pada 2026-10-07 ("feat(BL-19): sandboxing mcp stdio child process"). **Efektivitasnya bersyarat:** `create_sandbox` (`security/detect.rs:353`) menghasilkan `NoopSandbox` bila backend dimatikan, bila runtime Docker terpilih, atau bila backend yang diminta tidak tersedia. Apakah host ini punya backend efektif: **tidak diverifikasi**. `apply_default_mcp_sandbox` hanya fallback bila tak ada boundary, dan fungsi itu bukan pengurungan OS (menolak profil `deny-all`, mengatur `cwd`, membuang 7 variabel env rahasia) | [V] E4, E5, E6 |
| **P3** | Transport MCP/ACP apa yang dipahami klien kita? | agy: server `stdio` atau `http` (dengan `--header`). Skema Galleon: `Stdio`, `Http`, `Sse`. kiro-cli: subcommand `acp` ada (versi 2.29.0). Konfigurasi MCP di KiroCrew: **tidak diverifikasi** | [V] E6, E7, E8 |
| **P4** | Primitif isolasi apa yang benar-benar tersedia di host ini? | `bwrap` terpasang tetapi **tidak bisa dipakai**: `unshare -Ur true` ditolak (EPERM) dan `apparmor_restrict_unprivileged_userns=1`. Landlock ada di daftar LSM aktif (kernel 7.0.0-38) tetapi belum diuji. Docker dipakai dev-ci dengan `--cap-drop=ALL`, `no-new-privileges`, `--pids-limit=2048`, batas CPU dan memori, `tmpfs` | [V] E9, E10 |
| **P5** | Apa yang bisa dikendalikan dari agy? | Izin bersifat biner: `--dangerously-skip-permissions`, `--mode accept-edits/auto/plan`, `--sandbox`. Tidak ada callback izin di `--help`. `--input-format stream-json` menerima satu pesan NDJSON per baris dan menjalankan satu giliran per pesan. Apakah stream-json memancarkan permintaan izin: **belum diuji** | [V] E7 |
| **P6** | Berapa batas waktu panggilan sinkron? | Default timeout tool MCP di klien Galleon 180 detik; komentar proto `ToolCallRequest.timeout_seconds` menyebut batas keras 1–300 detik. Bridge agy hari ini memakai `TimeoutStartSec=14400` | [V] E3, E6, E12 |

**Konsekuensi untuk ADR ini:**
- Arah **control plane → Galleon** (Galleon sebagai runtime) tidak butuh perubahan di Galleon, selama ACP bridge dipertahankan (ODR-24) [V, E11].
- Arah **Galleon → control plane** (Galleon memanggil control plane sebagai tool) **tidak punya jalur hari ini** dan tidak ada tiket Go-nya. Itu menjadi pekerjaan terpisah di sisi Galleon (§8, OQ6).
- Sesi harness berjalan menit sampai jam, jadi antarmuka wajib asinkron (D2).

---

## 4. Keputusan yang Diusulkan

### D1. Produk mandiri

- Daemon lokal dengan repo, versi, dan rilis sendiri. Tidak mengimpor kode atau skema Galleon; Galleon hanyalah satu klien dan satu runtime [I].
- Uji independensi: antarmuka sesi yang sama berjalan untuk adapter agy, kiro, dan Galleon tanpa perubahan API (T10, §7).
- Nama, repo, organisasi, bahasa implementasi, dan lisensi: terbuka (§8).

### D2. Permukaan koordinasi: server MCP

**Transport.** Streamable HTTP pada `127.0.0.1` atau Unix socket. Shim stdio (`mcp-stdio`) merelai ke daemon untuk klien yang hanya mendukung stdio. Alasannya: agy dan skema Galleon mendukung `http` [V, P3], dan satu daemon bersama menghindari state ganda serta jalur spawn stdio MCP yang efektivitas sandbox-nya bersyarat (P2) [I]. Apakah klien HTTP MCP milik Galleon bekerja terhadap server ini: **tidak diuji**.

**Sepuluh tool v0.** Nama memakai `snake_case` agar aman terhadap klien yang membatasi karakter dan panjang nama [I].

| Tool | Scope | Sifat | Perilaku |
|---|---|---|---|
| `runtime_list` | read | sinkron | Daftar runtime: `id`, `kind`, `level` (L0/L1/L2), kapabilitas, kesehatan |
| `session_start` | run | **asinkron** (kembali ≤ 2 detik) | Argumen: `runtime`, `prompt`, `workspace` (`{id}` atau `{repo, base_ref}`), `mode?`, `limits?`, `idempotency_key` (**wajib**), `metadata?`. Mengembalikan `{session_id, workspace_id, state:"starting"}`. Kunci sama dengan parameter sama mengembalikan sesi yang sama; kunci sama dengan parameter berbeda menghasilkan `conflict` |
| `session_get` | read | sinkron | `state`, `runtime`, `workspace_id`, `started_at`, `last_seq`, `exit{reason,code}`, `resumable` |
| `session_list` | read | sinkron | Filter `state`/`runtime`/`metadata`, paging |
| `session_events` | read | long-poll | `after_seq`, `limit` ≤ 200, `wait_ms` ≤ 25000. Mengembalikan `events[]` dan `next_seq`. Batas 25 detik menjaga panggilan jauh di bawah timeout klien (P6) |
| `session_send` | run | ack sinkron | Mengirim pesan; hanya runtime L1 ke atas, selain itu `unsupported` |
| `permission_resolve` | run | ack sinkron | `request_id`, `decision` (`allow_once` atau `deny`), `reason`; hanya runtime L2 |
| `session_cancel` | run | ack asinkron | Menghentikan sesi; state menjadi `cancelling` lalu `cancelled` |
| `workspace_diff` | read | sinkron | Daftar berkas dan statistik; patch diambil bertahap dengan batas ukuran |
| `workspace_discard` | workspace_admin | sinkron | Menghapus worktree; ditolak bila ada sesi aktif di dalamnya |

**Scope pemanggil.** `read`, `run`, `workspace_admin`. Setiap klien memegang token sendiri (disimpan sebagai hash di sisi daemon, berkas konfigurasi mode 0600, dibandingkan dengan waktu konstan [I]). Penegakan scope terjadi **di sisi server**; petunjuk risiko pada tool hanya saran bagi klien dan tidak dipercaya[^3].

**Model kesalahan.** Hasil MCP dengan `isError: true` dan kode terstruktur: `invalid_argument`, `not_found`, `forbidden_scope`, `unsupported`, `conflict`, `limit_exceeded`, `runtime_unavailable`, `isolation_unavailable`, `internal`.

**Pemetaan ke kebijakan klien.** `session_start` adalah panggilan bertier eksekusi. Pada klien yang punya mesin kebijakan (Galleon: `PolicyEngine` mengembalikan `REQUIRE_APPROVAL` untuk tier `write` dan `execute`, `policy.go:52` [V, E13]) panggilan itu meminta persetujuan dengan argumen runtime, workspace, dan prompt. Persetujuan klien berlaku di **batas yang ia kendalikan**; isi sesi diatur kontrol di D5.

### D3. Model sesi dan log event

State: `starting` → `running` ⇄ `waiting_permission`; `cancelling`; terminal: `completed`, `failed`, `cancelled`, `timed_out`, `lost`.

Event ternormalisasi, append-only, dengan `seq` monoton per sesi:

| Tipe | Isi |
|---|---|
| `state` | transisi state |
| `message` | `role`, `text` |
| `tool_call` | nama, `args_digest`, status |
| `permission_request` | `request_id`, ringkasan aksi, `args_digest`, `expires_at` |
| `permission_decision` | keputusan dan pemutus |
| `file_change` | path relatif, operasi |
| `usage` | token, bila dilaporkan runtime |
| `log` | kutipan stderr yang dipotong |
| `error` | kode dan detail |

`args_digest` = SHA-256 dari argumen kanonik, agar klien dapat mengikat persetujuan ke aksi tertentu [I].

**Persistensi.** SQLite (WAL) satu berkas per instalasi. **Pemulihan.** Saat daemon restart, sesi yang prosesnya sudah tidak ada menjadi `lost` dan log tetap tersimpan. Daemon tidak me-resume otomatis; pemanggil memutuskan lewat sesi baru dengan token resume bila adapter menyediakannya [I].

### D4. SPI Runtime

Kontrak adapter (pseudo-IDL, netral bahasa):

```
Runtime
  id        : string                          # "agy", "kiro", "galleon"
  kind      : "acp" | "print-stream" | "rest-async"
  level     : L0 | L1 | L2
  capabilities : { resume, send, permission_callbacks, structured_output, native_sandbox }
  health()  -> { ok, detail }
  start(ctx: SessionContext) -> Handle
  send(h, text)                                # L1+
  resolve_permission(h, request_id, decision)  # L2
  cancel(h)
  events(h) -> stream<Event>                   # ternormalisasi, wajib berakhir dengan event terminal
  resume_token(h) -> string | null

SessionContext
  session_id, workspace_path, prompt, mode
  env             : map (sudah disaring allowlist)
  credentials_dir : path (hanya-baca)
  state_dir       : path (tulis, per runtime)
  limits          : { wall_s, mem_mb, cpus, pids }
  isolation       : "I1-container" | "none"    # "none" hanya untuk uji
```

**Tingkat kesesuaian.**

| Level | Kemampuan | Kandidat | Status |
|---|---|---|---|
| **L0** jalankan-sampai-selesai | `start`, `cancel`, `events` | agy mode print (`-p --output-format json`) | flag terverifikasi [V]; perilaku adapter belum diuji |
| **L1** interaktif | L0 + `send`, event streaming, `resume` | agy `--input-format stream-json --output-format stream-json`, `--conversation` | flag terverifikasi [V]; perilaku belum diuji |
| **L2** terkendali | L1 + callback izin | agen ACP, target pertama `kiro-cli acp` | subcommand ada [V]; perilaku izin belum diuji |

**Aturan adapter.**
1. Tidak menyentuh path di luar `ctx` (workspace, `state_dir`, `credentials_dir`).
2. Wajib memancarkan event terminal untuk setiap akhir proses.
3. Tidak boleh menyalakan flag yang mematikan permintaan izin (mis. `--dangerously-skip-permissions`) kecuali `ctx.isolation = "I1-container"`.
4. Menyunting kredensial dari event dan log.
5. Memetakan kode keluar proses ke state terminal.

**Adapter v1.** `agy` (L0/L1), `kiro` (ACP, target L2), `galleon` (ACP lewat `clawcrew-acp-bridge`, target L2). `rest-async` (mis. Manus) dicadangkan, tidak masuk v1. Bahwa registry ACP memuat puluhan agen[^4] [S] belum berarti satu adapter ACP otomatis cocok untuk semuanya; kesesuaian per agen harus diuji [I].

### D5. Batas isolasi

**Tiga lapis.**

| Lapis | Berlaku untuk | Isi |
|---|---|---|
| **I0** workspace | semua runtime, wajib | `git worktree` per sesi dari mirror bare (pola `sync_mirror` ada di dev-ci [V, E10]); cabang `cp/<session_id>`; runtime tidak pernah melihat checkout milik pemilik; path divalidasi sebelum setiap operasi `workspace_*` |
| **I1** proses | L0 dan L1, wajib | Kontainer Docker dengan `--cap-drop=ALL`, `no-new-privileges`, batas CPU/memori/pids, `tmpfs`, tanpa soket Docker, tanpa HOME pemilik. Bila Docker tidak tersedia, `session_start` gagal dengan `isolation_unavailable`; **tidak boleh jatuh ke eksekusi tanpa kurungan** |
| **I2** izin per aksi | L2 | Permintaan izin runtime menjadi event `permission_request`; keputusan lewat `permission_resolve`; permintaan tanpa jawaban ditolak setelah batas waktu (fail-closed) |

**Alasan memilih kontainer.** Di host ini `bwrap` tidak bisa dipakai (P4) dan Landlock belum diuji; Docker sudah terbukti dipakai dev-ci dengan flag di atas [V]. Landlock tetap kandidat pengganti jika diuji [I].

**Kredensial.**
- Dibaca hanya dari direktori kredensial per runtime yang disediakan operator, dipasang hanya-baca. Tidak pernah dari HOME pemilik.
- Variabel lingkungan: allowlist nama per runtime.
- Kredensial `git push` dan pembuatan PR **tidak** diberikan ke sesi. Penerbitan dilakukan di luar sesi (pemanggil, atau tool `workspace_publish` di masa depan, OQ3). Pola ini mengikuti Symphony: kredensial tracker disimpan di sisi host dan tidak diteruskan ke proses anak[^2] [S, S12].

**Sumber daya.** Batas aktif global default 1 sesi (host 4 core [V]), antrean FIFO, `wall_s` default 3600 yang dapat diubah, serta CPU, memori, dan pids per kontainer. Angka default ini adalah titik awal untuk disetel [I].

**Matriks penegakan (v1).**

| Kontrol | Ditegakkan oleh | L0/L1 | L2 | Status |
|---|---|---|---|---|
| Workspace terpisah | Control plane | wajib | wajib | direncanakan |
| Proses dikurung | Control plane + Docker | wajib, fail-closed | sangat dianjurkan | direncanakan; flag terbukti dipakai dev-ci [V] |
| Izin per aksi | Runtime + `permission_resolve` | **tidak ada** | ada | bergantung adapter; belum diuji |
| Kredensial | Control plane | direktori khusus + allowlist | sama | direncanakan |
| Push dan PR | di luar sesi | sama | sama | OQ3 |
| Jaringan | Docker bridge | **residual**: dapat menjangkau LAN dan layanan host yang terikat ke 0.0.0.0 | sama | diakui; sama dengan dev-ci [V, E10] |
| Batas sumber daya | Docker + control plane | ya | ya | direncanakan |
| Otorisasi pemanggil | Control plane | token + scope | sama | direncanakan |
| Isi percakapan harness dengan vendor | tidak ada | **tidak terlihat dan tidak dikontrol** | sama | diakui |

**Residual yang diakui.** Isi workspace dikirim ke vendor harness sebagai bagian dari kerjanya. Memori internal harness (mis. percakapan agy, memori kiro) berada di luar kendali control plane.

### D6. Integrasi

- **Klien MCP:** agy (`agy mcp add --header "Authorization: Bearer <token>" <nama> http://127.0.0.1:<port>/mcp` [V, E7]), KiroCrew (bentuk konfigurasi tidak diverifikasi), dan board bridge sebagai klien pertama yang menggantikan `_run_agy`.
- **Galleon sebagai runtime:** lewat adapter `galleon` memakai `clawcrew-acp-bridge` (fitur `acp-bridge`). Dari 45 baris pertama yang kubaca, bridge menyambung ke gateway lewat WebSocket dengan token pairing; sisi stdio ke editor tidak kubaca penuh [V parsial, E11]. Lokasi server ACP (`runtime/src/acp/`) berada di wilayah R-00 dan R-42 akan mengubah targetnya, jadi jalur ini bisa bergeser [V].
- **Galleon memanggil control plane:** belum ada jalur (P1). Pilihan: klien MCP di sisi Go, atau tool jembatan di Rust yang masuk `ALLOWED_TOOLS`. Itu keputusan Galleon dan **di luar ADR ini** (OQ6).

### D7. Bukan tujuan v1
Multi-tenant; akses jarak jauh (butuh TLS dan keputusan setara ODR-06); penerbitan dan merge otomatis; layanan memori (nama `memory_*` dicadangkan, tidak dispesifikasikan); UI (dashboard adalah klien, bukan bagian inti); fasad A2A; orkestrasi antar-server; Kubernetes.

### D8. Versi dan kompatibilitas
Versi semantik pada info server. Perubahan hanya aditif (field dan tool baru). Pemecah kompatibilitas memakai nama tool baru, bukan mengubah yang lama.

---

## 5. Alternatif yang Dipertimbangkan

| Alternatif | Putusan | Alasan |
|---|---|---|
| Plugin WASM di Galleon | Ditolak | Berjalan in-process di Wasmtime. `PluginPermission` hanya `HttpClient`, `WebSocketClient`, `SocketClient`, `FileRead`, `FileWrite`, `ConfigRead`, `MemoryRead`, `MemoryWrite`; `wit/v1` hanya berisi `README.md` dan `types.wit`. Tidak ada izin men-spawn proses [V, E14] |
| Add-on terkompilasi (Tier B) | Ditolak | Mekanisme Tier B didefinisikan untuk channel (definisi produk §3). Masuk ke workspace Rust yang CI-nya merah dan modulnya sedang dipindah (R-00, R-41), dan memaksa pengecualian ODR-03 serta ADR 0001 ke inti [I] |
| Di dalam engine Go | Ditolak | Go dilarang melakukan operasi OS dan men-spawn proses (boundary policy Tier 3); engine tidak punya `exec.Command` non-test [V, E1, E13] |
| Adopsi Symphony atau Agent Orchestrator apa adanya | Belum diputuskan | Belum dijalankan; asumsi harness utamanya Codex/Claude. Dapat dipakai sebagai referensi implementasi atau sumber adapter [I] |
| Menjadikan KiroCrew sebagai control plane | Ditolak sebagai inti | Ia sudah menjadi klien ACP untuk satu harness [V], tetapi menyatukannya dengan perencana membuat kontraknya tidak mandiri [I] |

---

## 6. Konsekuensi

**Positif.**
- ODR-03, ODR-11, ODR-07, dan ADR 0001 tidak tersentuh; Galleon tidak menanggung pengecualian apa pun [I].
- Satu kontrak untuk semua harness; menambah runtime berarti menulis satu adapter.
- Isolasi dan kredensial dimiliki satu tempat, sehingga celah di bridge agy sekarang bisa ditutup di sana.

**Negatif dan risiko.**
- Sepenuhnya baru: daemon, auth pemanggil, manajemen worktree, dan supervisi kontainer harus dibangun dan dirawat. Ukuran kerja tidak diestimasi.
- Perilaku izin agy dan kiro belum diuji. Bila agy ternyata tidak punya callback izin sama sekali, ia tetap L0/L1 dan hanya aman karena I0 + I1, bukan karena persetujuan per aksi.
- Isolasi kontainer tidak memfilter jaringan (residual di D5).
- Jalur Galleon → control plane belum ada dan membutuhkan keputusan di sisi Galleon.
- Kategori produk ini ramai (Symphony, Agent Orchestrator, dan lainnya[^5] [S]); nilai diferensiasi bersandar pada isolasi, kontrak lintas-harness, dan integrasi dengan memori tata-kelola, bukan pada orkestrasi itu sendiri [I].

---

## 7. Kriteria Penerimaan (dapat diuji)

| # | Uji | Lulus bila |
|---|---|---|
| T1 | Dua `session_start` paralel di dua workspace | `git status` checkout pemilik tidak berubah; sesi A tidak bisa membaca berkas canary milik sesi B |
| T2 | `session_start` oleh token tanpa scope `run` | `forbidden_scope` |
| T3 | `session_start` dua kali dengan `idempotency_key` dan parameter sama | `session_id` sama; parameter berbeda → `conflict` |
| T4 | `session_events` dengan `wait_ms` maksimum | kembali ≤ 26 detik; tidak ada panggilan tool yang melebihi 60 detik |
| T5 | Adapter L2: permintaan izin | muncul sebagai event; tanpa jawaban → `deny` setelah batas waktu; `allow_once` → sesi melanjutkan |
| T6 | Adapter L0/L1 dengan Docker tidak tersedia | `isolation_unavailable`; tidak ada proses harness yang berjalan |
| T7 | Restart daemon saat sesi aktif | sesi yang prosesnya hilang menjadi `lost`; log tetap utuh |
| T8 | Variabel env canary di proses pemanggil | tidak ada di dalam kontainer sesi |
| T9 | `session_cancel` | kontainer berhenti ≤ 10 detik dan worktree dilepas |
| T10 | Siklus hidup sesi yang sama untuk adapter agy dan kiro | tanpa perubahan API; adapter `galleon` sebagai uji tambahan |

---

## 8. Pertanyaan Terbuka

1. **Nama, repo, organisasi.** ODR-19 mengatur penamaan Galleon, bukan produk mandiri.
2. **Bahasa implementasi.** Python (cepat dibuat; board dan dev-ci sudah Python), Go, atau Rust.
3. **Siapa yang `push` dan membuat PR?** Tool `workspace_publish`, atau pemanggil.
4. **Primitif I1:** kontainer (terbukti di host ini) atau Landlock (tersedia, belum diuji).
5. **Akses jarak jauh:** kebutuhan, TLS, dan model pairing.
6. **Jalur Galleon → control plane:** klien MCP di Go atau tool jembatan di Rust.
7. **Apakah stream-json agy memancarkan permintaan izin?** Menentukan apakah agy bisa naik ke L2.
8. **Lisensi.**
9. **Memori:** kapan dan bagaimana `memory_*` didefinisikan (fase terpisah; lihat dokumen induk §6.4).

---

## 9. Log Koreksi

| # | Pernyataan sebelumnya | Setelah verifikasi |
|---|---|---|
| 1 | Chat 2026-10-18 (analisis bentuk opsional): "tidak menemukan kode produksi yang memasang `McpCommandBoundary`" | **Salah.** Terpasang di `runtime/src/tools/mod.rs:751`. Pencarianku memotong keluaran dengan `head -6` dan melewatkannya [V]. |
| 2 | Chat yang sama: "fungsi `apply_default_mcp_sandbox` bukan pengurungan OS, jadi sandbox MCP Galleon belum nyata" | **Sebagian benar.** Fungsi itu memang bukan pengurungan OS, tetapi hanya fallback; jalur produksi memakai boundary yang membungkus perintah dengan sandbox runtime. Efektivitasnya bergantung `create_sandbox` yang bisa menghasilkan `NoopSandbox` (P2). |
| 3 | Roadmap R-60 ("sandbox MCP stdio") masih `[ ]` | Kemungkinan usang: commit `f2af74175` (2026-10-07) menambahkan boundary. Apakah kriteria penerimaan R-60 ("akses di luar workspace ditolak OS-level") terpenuhi **tidak diverifikasi**. |
| 4 | Chat yang sama: "jalur Go ke klien MCP belum terbukti" | Sekarang terverifikasi: **tidak ada jalur** (P1). |

---

## 10. Rujukan dan Bukti

### A. Sumber eksternal

ID sama dengan dokumen riset induk §11-A (lihat di sana untuk tingkat baca setiap sumber). Yang dipakai ADR ini:

| ID | Sumber | URL | Tingkat baca | Dipakai untuk |
|---|---|---|---|---|
| S6 | Blog MCP, "MCP joins the Agentic AI Foundation" | http://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/ | CUPLIKAN | Status MCP sebagai standar terbuka |
| S10 | DEV, "Agent Client Protocol (ACP): Connect Any AI Agent to Any Editor" | https://dev.to/dmaxdev/agent-client-protocol-acp-connect-any-ai-agent-to-any-editor-2p0m | SEBAGIAN | Registry ACP, Kiro terdaftar |
| S12 | OpenAI, Symphony SPEC.md | https://github.com/openai/symphony/blob/main/SPEC.md | SEBAGIAN (±8.000 dari 89,9 KB) | Komponen, kredensial tracker sisi host, workspace per issue |
| S18 | Augment Code, "9 Open-Source Agent Orchestrators for AI Coding (2026)" | https://www.augmentcode.com/tools/open-source-agent-orchestrators | SEBAGIAN (artikel vendor) | Worktree sebagai primitif isolasi konsensus |
| S21 | Dokumentasi agent-sandbox | https://agent-sandbox.sigs.k8s.io/docs/ | CUPLIKAN | Gagasan identitas stabil dan workspace persisten per agen |

Tidak ada sumber eksternal baru yang dibuka untuk ADR ini.

### B. Bukti internal (dapat diulang)

Versi: `agy 1.4.0`, `kiro-cli 2.29.0`, `kirocrew 0.9.0`; `galleon-fleet origin/testing = 295d7a7065`; kernel `7.0.0-38-generic`; `dev-ci HEAD = 3dbceecbf4`; `board HEAD` saat verifikasi = `2bf8f37`.

| ID | Bukti | Cara mengulang |
|---|---|---|
| E1 | Referensi MCP di engine Go | `grep -rIlic mcp engine --include=*.go \| grep -v _test` → `engine/pkg/pb/agent_service.pb.go` (3), `engine/src/tool/interfaces.go`, `services.go`, `dto.go` (1 masing-masing). `grep -rnE 'Source: *"mcp\|"mcp:' engine --include=*.go \| grep -v _test` → hanya komentar `services.go:446` dan `dto.go:87` |
| E2 | Roadmap | `grep -ciE '\bMCP\b' standard-docs/roadmap/G-go-engine.md` → 0; baris MCP hanya R-60..R-63 di `R-rust.md` |
| E3 | Gateway dan proto | `crates/clawcrew-gateway/src/grpc_system_gateway.rs:14` (`ALLOWED_TOOLS`), `:438-444` (penolakan); `proto/agent_service.proto:113-118` (`ToolCallRequest`: `tool_name`, `arguments_json`, `workspace_path`, `timeout_seconds` "hard timeout (1-300s)") |
| E4 | Pemasangan boundary | `crates/clawcrew-runtime/src/tools/mod.rs`: `:704` (struct), `:714` (impl), `:731` (`runtime_shell_assembly`), `:751` (`set_mcp_command_boundary(Some(..))`), `:769` dan `:1111` (pemanggil). `git log -S"RuntimeMcpCommandBoundary" origin/testing -- crates/clawcrew-runtime/src/tools/mod.rs` → `f2af74175 2026-10-07 feat(BL-19): sandboxing mcp stdio child process` |
| E5 | Pabrik sandbox | `crates/clawcrew-runtime/src/security/detect.rs:353` (`create_sandbox`): `NoopSandbox` bila backend `None` atau dimatikan, bila runtime Docker terpilih, atau bila backend yang diminta tidak tersedia |
| E6 | Transport MCP | `crates/clawcrew-tools/src/mcp_transport.rs:55` (`apply_default_mcp_sandbox`), `:696-707` (cabang spawn); `crates/clawcrew-config/src/schema.rs:5552` (`McpTransport`), `:5673` (`tool_timeout_secs`); `crates/clawcrew-tools/src/mcp_client.rs:31` (`DEFAULT_TOOL_TIMEOUT_SECS = 180`) |
| E7 | agy | `agy --help`; `agy mcp add --help` (tipe `stdio` atau `http`, `--header`) |
| E8 | kiro-cli | `kiro-cli --version` → 2.29.0; `kiro-cli acp --help` → "Start Agent Client Protocol (ACP) agent" |
| E9 | Isolasi host | `unshare -Ur true` → "Operation not permitted"; `cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns` → 1; `cat /sys/kernel/security/lsm` memuat `landlock`; `command -v bwrap` → `/usr/bin/bwrap`; `command -v podman` → tidak ada |
| E10 | dev-ci | `~/Apps/dev-ci/bin/ci-poller`: `:112` (`sync_mirror`), `:133-135` (`--network bridge/none`, `--cpus`, `--memory`, `--pids-limit=2048`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--tmpfs`) |
| E11 | ACP bridge dan server | `src/bin/clawcrew-acp-bridge.rs` (702 baris; `tokio-tungstenite`, env `CLAWCREW_ACP_BRIDGE_TOKEN`); `Cargo.toml:117-119` dan `:322` (fitur `acp-bridge`); `crates/clawcrew-runtime/src/acp/server.rs`: hitungan string `session/new` 66, `session/prompt` 17, `session/cancel` 3, `"initialize"` 5, `request_permission` 1 |
| E12 | Bridge agy | `~/Apps/board/tools/agy-bridge/board_agy_bridge.py:201-203,213` (`--dangerously-skip-permissions`, `--add-dir`, `cwd`); `systemctl --user cat agy-bridge.service` → `TimeoutStartSec=14400` |
| E13 | Dokumen baku | `decisions/owner-decisions/ODR-2026-10-04-product-direction.md` (ODR-03, ODR-07), `...-addendum-1.md` (ODR-11), `...-addendum-4.md` (ODR-24); `decisions/0001-llm-ssot-rust.md`; `decisions/adr-wasm-plugin-vs-mcp.md:10-11,35-36`; `tech-standart/architecture/01-boundary-policy.md` (Tier 3, Forbidden); `engine/src/tool/policy.go:52` |
| E14 | Plugin WASM | `crates/clawcrew-plugins/src/lib.rs:123` (`enum PluginPermission`, 8 varian); `ls wit/v1` → `README.md`, `types.wit`; `grep -rnEi "spawn\|process\|exec\|command\|subprocess\|shell" wit/v1` → kosong |

---

## 11. Catatan Kaki

[^1]: ADR `adr-wasm-plugin-vs-mcp.md` (Accepted, Sprint 5, BL-22) baris 35 menyebut MCP dipakai "untuk memanfaatkan ekosistem open-source MCP yang sudah ada (alat CLI, bridge database, integrasi sistem operasi)" dan baris 36 mewajibkan eksekusi MCP stdio melalui `apply_default_mcp_sandbox`. Pernyataan terakhir ini menggambarkan fallback; jalur produksi memakai boundary (§3, P2).
[^2]: Spesifikasi Symphony (S12) dibaca sebagian: komponen §3.1, goals dan non-goals §2, serta kredensial tracker sisi host. Bagian state machine, retry, dan rekonsiliasi tidak terbaca (lihat dokumen induk, catatan kaki 7).
[^3]: Spesifikasi MCP mendefinisikan anotasi tool berupa petunjuk (mis. hanya-baca, destruktif). Ini pengetahuan umum penulis dan **tidak diverifikasi pada sesi ini**. Karena petunjuk dikirim oleh server dan klien tidak dapat memverifikasinya, penegakan scope tetap di sisi server.
[^4]: Dokumen induk catatan kaki 5: registry ACP melaporkan 50 agen per Juni 2026 (sumber sekunder, S10); kesesuaian per agen tidak diuji.
[^5]: Dokumen induk §5.2 dan catatan kaki 11: ringkasan orkestrator berasal dari artikel vendor pesaing (S18).
