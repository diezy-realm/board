---
title: Inventaris Komponen Galleon yang Belum Dibangun untuk Orkestrasi Multi-Runtime (Calon Backlog)
status: research
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: multi-runtime-orchestration-feasibility-2026-10-18.md; adr-control-plane-interface-2026-10-18.md (revisi 2)
informs: standard-docs/roadmap/CANDIDATES-multi-runtime-orchestration.md (catatan, bukan tiket); standard-docs/decisions/owner-decisions/ODR-2026-10-18-multi-runtime-orchestration.md (Proposed)
---

# Inventaris Komponen yang Belum Dibangun (Calon Backlog)

> **Status: riset, bukan rencana.** Daftar ini mencatat komponen yang dibutuhkan agar Galleon menjadi orkestrator multi-runtime tetapi belum ada di produk, supaya kelak dapat diubah menjadi backlog. Ia **bukan tiket** dan tidak menetapkan urutan atau jadwal. Menjadi tiket hanya setelah Owner meratifikasi ODR pendamping.
>
> **Cara membaca bukti.** **[V]** dibaca atau dijalankan langsung oleh penulis pada 2026-10-18 (UTC). **[S-lama]** berasal dari audit internal lama (2026-10-05) yang dicatat di indeks riset board dan tidak diverifikasi ulang hari ini. **[I]** inferensi penulis. **[?]** tidak terverifikasi.
>
> **Status bangun:** *Ada* · *Sebagian* (primitif ada, komponennya belum) · *Embrio* (kerangka ada, belum dipakai) · *Belum ada* · *Belum diketahui* (belum ditelusuri cukup untuk menyimpulkan) · *Hanya percobaan* (ada di luar produk, bukan bagian Galleon).
>
> Penulis **tidak** mencari secara menyeluruh seluruh repo; "tidak ditemukan" berarti tidak ditemukan pada paket dan pola yang disebut.

## 1. Pembatasan

Board (`~/Apps/board`), `agy-bridge`, dan `dev-ci` adalah **percobaan di luar produk** untuk menguji apakah antar-runtime dapat bekerja berurutan. Di sini ketiganya dipakai hanya sebagai **rujukan perilaku** untuk komponen yang mungkin perlu dibangun di Galleon. Tidak ada klaim bahwa kode percobaan itu layak dibawa ke produk (lihat §5).

## 2. Ringkasan

Dari 18 komponen: 0 berstatus *Ada* penuh, 6 *Sebagian* (UC-01, 05, 07, 10, 13, 15), 1 *Embrio* (UC-02), 9 *Belum ada* (UC-03, 04, 06, 08, 09, 11, 12, 14, 16), 1 *Belum diketahui* (UC-17), dan 1 berupa proses, bukan kode (UC-18). Galleon sudah punya primitif yang relevan (Quest, Task DAG, workflow, worker pool in-memory, memori consent, provider CLI satu-giliran, protokol klien), tetapi **tidak ada** papan beserta ketentuannya, reconciler untuk tugas berjalan, protokol antar-agen yang ditegakkan, server MCP, atau adapter runtime tingkat tugas.

## 3. Tabel Komponen

Kolom *Percobaan* menyebut padanan di luar produk. Kolom *Terkait* merujuk ke keputusan di draf ODR (`MR-xx`) dan bagian ADR revisi 2 (`D-xx`).

### A. Orkestrasi, papan kerja, dan protokol

| ID | Komponen | Percobaan (di luar produk) | Di Galleon hari ini | Status | Terkait |
|---|---|---|---|---|---|
| UC-01 | **Papan kerja dan ketentuannya**: model item kerja (story, backlog, PRD, spec, task, report), siklus status, gate antar-tahap, template, validator front-matter, RACI | `~/Apps/board`: `RULES.md`, `TEMPLATES.md`, `validate.py` (146 baris), `sprint-manager.py` (149 baris) [V] | `mission.Quest` (status `ready/underway/completed/failed/cancelled`; `RequiredArtifacts`, `BudgetLimitUSD`, `WorkflowID`, `MapSteps`) [V]; `workflow` (template menjadi DAG task) [V]; `task`/`run` Task DAG [V]. **Tidak ditemukan**: model backlog/PRD/spec/sprint, aturan gate, validator, UI papan; lane UI roadmap tidak punya tiket Quest atau papan [V] | Sebagian | MR-01, MR-05 |
| UC-02 | **Kontrak tugas dan laporan berbukti**: tujuan, kriteria penerimaan, cakupan tulis, skema laporan, bukti wajib, "selesai tanpa bukti = tidak sah" | `RULES.md` §3 butir 4, `reports/RPT-*.md`, bagian "Acceptance Check" [V] | `run.Artifact` bertipe `git_diff/file/report/diagram`; `Quest.RequiredArtifacts` [V]. Validasi skema laporan atau penolakan penutupan tanpa bukti **tidak ditemukan** pada struct yang dibaca [?] | Embrio | MR-05, MR-06; D2 `task_get/task_report` |
| UC-03 | **Poller/reconciler tugas berjalan**: loop periodik yang menyelaraskan state (kirim ke eksekutor, deteksi macet, retry berbatas, buka blokir saat prasyarat selesai, picu review dan gerbang), idempoten dan tahan restart | Tiga timer systemd `agy-bridge`, `board-review`, `board-unblock`; `board_switch.py` (134 baris), `board_agy_bridge.py` (492 baris), `bridge_events.db`; error CI diulang setelah 10 menit maksimal 3 kali; satu unit CI per PR+SHA [V] | `task.WorkerPool`: goroutine terbatas dengan antrean in-memory `chan Job`, **tanpa persistensi, lease, atau heartbeat** [V `worker_pool.go`]; `schedule.Service` hanya CRUD record cron [V]; `LoopDetector` ada tetapi hasilnya tidak sampai dashboard [S-lama; R-51]; scheduler cron Rust dinilai matang [S-lama]; kemungkinan cron pindah ke Go (R-14, G-32) belum dikerjakan [V] | Belum ada (hanya primitif) | MR-02, MR-05 |
| UC-04 | **Protocoler antar-agen**: spesifikasi alur kerja (peran, siklus tugas, serah-terima, format laporan, aturan memori) **dan** penegakannya | Aturan teks `RULES.md`, `TEMPLATES.md`, steering `board-coordination.md`; ditegakkan validator dan bridge [V] | Paket `protocol` adalah **Galleon Client Protocol** (WS JSON-RPC 2.0 untuk klien), **bukan** protokol antar-agen [V `ws_server.go`]; SOP engine Rust ada [S-lama]; tidak ada tiket protokol antar-runtime di roadmap [V] | Belum ada | MR-05, MR-06 |
| UC-05 | **Konsolidasi model Task** (kebersihan SSOT sebelum membangun UC-01/03) | — | Dua definisi `Task`: `engine/src/run/dto.go:108` (berlabel "Canonical DTO", status `pending, ready, assigned, running, waiting_for_input, completed, failed, cancelled`) dan `engine/src/task/dto.go:57` (tipe `TaskStatus`; nilainya tidak kubaca). Hubungan keduanya **tidak ditelusuri** [V]/[?] | Sebagian | AGENTS.md: sumber kebenaran tunggal |

### B. Antarmuka dan runtime

| ID | Komponen | Percobaan | Di Galleon hari ini | Status | Terkait |
|---|---|---|---|---|---|
| UC-06 | **Server MCP Galleon** (tool tugas, memori, skills; token sesi; state machine di server) | Tidak ada server MCP; board dibaca dan ditulis lewat berkas dan skrip [V] | Pencarian pola implementasi server di seluruh repo: kosong; semua `McpServer*` adalah klien/konfigurasi [V]. Q-2 di arsip dev-tasks menghapus klien MCP dari Go dan mengarahkan MCP ke Rust [V] | Belum ada | MR-06; D2; OQ1 |
| UC-07 | **Adapter runtime tingkat tugas dan RPC `SystemGateway`** (start, stream event, kirim input, izin, batal) | `board_agy_bridge.py::_run_agy`: agy headless, `--print-timeout 0`, pemakaian ulang `conversation_id` [V] | Provider CLI satu-giliran `gemini_cli.rs`, `kilocli.rs`, dan ACP `grok_cli.rs`; Galleon tetap memegang loop agen [V]. Adapter yang membiarkan CLI vendor memegang loop-nya: tidak ada | Sebagian (tingkat 2 saja) | MR-02, MR-04; D4 |
| UC-08 | **Onboarding runtime dan uji kepatuhan** (C1–C6, penetapan level L0/L1/L2) | Satu probe: kata sandi acak di `AGENTS.md` dan skill `zz-probe-skill`; agy menjawab benar (n=1) [V riset induk I4] | Tidak ada | Belum ada | MR-04, MR-08; D7 |
| UC-09 | **Proyeksi konteks per runtime** dari satu sumber ke berkas yang dibaca tiap CLI | 17 berkas, 95.115 byte, 3 format (`AGENTS.md`, `.gemini/*`, `.kiro/steering/*`) [V riset induk I8] | Pemuat `PERSONALITY_FILES` (mengonsumsi `AGENTS.md` dari workspace) [V]; **generator keluar** tidak ditemukan. Lokasi dan format steering kanonik belum ditetapkan [?] | Belum ada | MR-08; D6 |

### C. Eksekusi, isolasi, dan verifikasi

| ID | Komponen | Percobaan | Di Galleon hari ini | Status | Terkait |
|---|---|---|---|---|---|
| UC-10 | **Workspace per sesi, kurungan proses, dan penerbit** (worktree dari mirror, sandbox fail-closed, push/PR di luar sesi) | `dev-ci`: `sync_mirror`, worktree, kontainer dengan `--cap-drop=ALL` dan kawan-kawan [V riset induk E10] | `create_sandbox` dengan jalur `NoopSandbox` [V]; **backend Landlock ada beserta uji integrasi** (`crates/clawcrew-runtime/src/security/landlock.rs`; `crates/clawcrew-runtime/tests/landlock_workspace_boundary.rs`, `landlock_network_config_access.rs`, `landlock_spawn_failure.rs`, `landlock_contract.rs`) tetapi belum dijalankan di host ini [V keberadaan]; alat git Rust memahami *linked worktree* (otorisasi metadata worktree, `crates/clawcrew-tools/src/git_operations.rs:149,162,197,222`) dan `policy.rs` memperlakukan subcommand `worktree` secara khusus (tes `policy.rs:6138,6227`; efek `git worktree add` tidak dibaca) [V]; **pengelola siklus hidup worktree per sesi dan penerbit (push/PR) tidak ditemukan** [V pada pola yang dicoba] | Sebagian | MR-02, MR-05; D5 |
| UC-11 | **Gerbang verifikasi independen** sebagai kemampuan produk (penilaian hasil tugas yang tidak mempercayai klaim agen) | `~/Apps/dev-ci`: `ci-poller`, `gates.sh`, status `local/*`, baseline ratchet [V] | `galleon-eval` (replay deterministik; R-37) bukan gerbang penerimaan; `approval` untuk persetujuan manusia [I] | Belum ada | MR-05, MR-10 |
| UC-12 | **Governor kuota dan konkurensi**: batas sesi aktif, antrean, kuota vendor, resource gate | Antre satu build dengan kunci [V] | R-50…R-53 (resource gate sub-agent) belum dikerjakan, R-53 sengaja ditunda [V]; `treasury` hanya melaporkan biaya provider [V] | Belum ada | MR-09(c)(d); D5 sumber daya |

### D. Data dan audit

| ID | Komponen | Percobaan | Di Galleon hari ini | Status | Terkait |
|---|---|---|---|---|---|
| UC-13 | **Memori bersama dengan provenance wajib** (`author` = principal, runtime, sesi; `purpose`; `source_task`) | Skema memori KiroCrew punya `source`, `scope`, `confidence`, `valid_from`, `observed_at`, `revision`, `content_hash`; tidak ada `purpose` [V riset induk] | Memori Go bercakupan; `MemoryProposal` berstatus pending/approved/rejected/reverted, versi, dapat di-revert [V]. `Document.Metadata` bebas; `MemoryProposal` tanpa field pembuat atau tujuan [V] | Sebagian | MR-07; D8 |
| UC-14 | **Log event sesi dan audit trail** (append-only, `seq` per sesi, `args_digest`) | `bridge_events.db` [V keberadaan, isi tidak dibaca] | Paket `audit`: "TODO: Define audit domain interfaces" [V]; G-26 (audit trail) belum dikerjakan [V] | Belum ada | MR-05; D3 |

### E. Tata kelola, UI, dan proses

| ID | Komponen | Percobaan | Di Galleon hari ini | Status | Terkait |
|---|---|---|---|---|---|
| UC-15 | **Kebijakan kredensial dan gerbang aktivasi provider** (allowlist per runtime, suntikan API key dari vault, provider berisiko default nonaktif) | — | Vault dengan RPC `GetDecryptedSecret` [S-lama]; `openai_codex.rs` dan setup-token Anthropic aktif tidaknya default: **belum diperiksa** [?] | Sebagian | MR-03, MR-09 |
| UC-16 | **Permukaan status dan konsol UI** (runtime, level, hasil uji, sesi, tugas, event) | UI papan lewat `artifact-server.py`, tampilan Status [V] | Lane UI roadmap tanpa tiket terkait [V] | Belum ada | — |
| UC-17 | **Jalur model lokal** (endpoint OpenAI-compatible: Ollama, llama.cpp, vLLM) sebagai runtime tingkat 1 | — | Provider kompatibel OpenAI ada [I]; belum diverifikasi sebagai jalur lokal | Belum diketahui | tingkat 1 riset |
| UC-18 | **Tinjau-ulang legal berkala** (daftar ketentuan vendor dengan tanggal baca, dicek tiap rilis) | — | Proses, bukan kode | Belum ada | MR-09(h) |

## 4. Ketergantungan Kandidat (inferensi, bukan jadwal)

Hanya untuk membantu pemecahan backlog kelak [I]:

- **Prasyarat keputusan/kebersihan:** UC-05 (model Task kanonik), UC-15 (nonaktifkan atau tinjau provider berisiko), UC-18 (proses legal).
- **Fondasi data dan aturan:** UC-01, UC-02, UC-13, UC-14, UC-10 (kurungan).
- **Mesin:** UC-03, UC-06, UC-07, UC-09.
- **Di atasnya:** UC-08, UC-04 (menyatukan aturan dan penegakannya), UC-11, UC-12, UC-16.
- **Dapat berdiri sendiri:** UC-17.

Satu keterkaitan penting: UC-03 (reconciler) tidak masuk akal dibangun sebelum UC-05 menetapkan model Task kanonik dan persistensi ODR-05, dan UC-06 butuh keputusan lokasi server MCP (OQ1).

## 5. Hal dari Percobaan yang Tidak Boleh Dibawa ke Produk

1. **Ekstraksi, pembacaan, penyalinan, atau pooling token OAuth vendor.** Produk tidak boleh menyentuh berkas token runtime vendor; syarat staf Google menyatakan penggunaan sah bila "No OAuth tokens, cookies, or credentials are extracted, read, or passed" dan alur "not shared, pooled" [V]. Lihat MR-09 butir (b) dan (e). Login dimiliki pengguna; adapter hanya menjalankan binary resmi tanpa modifikasi.
2. **`--dangerously-skip-permissions` bersama `--add-dir` ke checkout utama** (celah isolasi yang sudah dicatat di riset induk).
3. **Pemicu berbasis polling pada host dengan identitas pengguna** tanpa kurungan proses.

## 6. Dari Inventaris ke Backlog

Aturan board (`RULES.md` §1): item backlog membutuhkan story induk yang ada (`source_story`). Karena papan backlog saat ini kosong dan keputusan Owner belum ada, langkahnya kelak:

1. Owner meratifikasi ODR (atau menolak/mengubahnya).
2. Tiap UC yang dipilih dibuatkan Story (`US-`), lalu Backlog (`BL-`) dengan DoD.
3. Di repo produk, tiket dibuat di lane roadmap yang sesuai dan di `PR-plan.md` (lihat `roadmap/CANDIDATES-multi-runtime-orchestration.md`).

## 7. Yang Belum Terverifikasi

Cakupan penelusuran kode terbatas pada paket dan pola yang disebut. Yang belum diperiksa: apakah ada pengelola siklus hidup worktree atau penerbit di luar pola yang dicoba (`git worktree`, `worktree add`, `"worktree"`); nilai `TaskStatus` di `task/dto.go` dan hubungannya dengan `run.Task`; apakah scheduler cron Rust benar-benar matang saat ini; apakah provider kompatibel OpenAI dapat menjadi jalur lokal tanpa perubahan.
