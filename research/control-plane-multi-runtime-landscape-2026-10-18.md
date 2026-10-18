---
title: Control Plane Multi-Runtime (KiroCrew, agy, runtime lain) — Verifikasi Kerangka, Kondisi Saat Ini, dan Lanskap Eksternal
status: research
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: capabilities-skills-lessons-steering-audit.md, agent-subagent-permission-scoping-survey.md, memory-data-governance-audit.md, plugin-mcp-architecture-audit.md
---

# Control Plane Multi-Runtime untuk Agent Harness

> **Status:** riset. Rekomendasi di dokumen ini **bukan keputusan**. Keputusan final hanya sah bila dicatat sebagai ODR di `standard-docs/decisions/owner-decisions/` (repo `galleon-fleet`).
>
> **Cara membaca bukti.** Klaim penting diberi tag:
> - **[V]** diverifikasi sendiri dengan perintah atau uji pada 2026-10-18 (UTC). Perintah dan hasilnya ada di §11-B.
> - **[S]** dilaporkan sumber luar dan **tidak** diverifikasi mandiri. Rujukannya ada di §11-A, dengan catatan seberapa banyak sumber itu benar-benar terbaca.
> - **[I]** inferensi atau penilaian penulis.
>
> Angka `[^n]` menunjuk catatan kaki di §12.
>
> **Permintaan asal (Achmad, 2026-10-18).** Membangun orkestrator antar runtime AI Agent Harness yang dipakai sekarang (KiroCrew sebagai perencana, Antigravity/agy sebagai tim eksekutor BE/FE/Design). Perlu protokol atau kesepakatan bersama agar runtime tunduk pada workflow, serta memori bersama (dengan author dan tujuan) agar lesson learned, skills, rules, dan steering dibangun bersama. Gambaran besarnya: model → agent → CLI headless → harness yang menampung banyak runtime → orchestrator runtime → terisolasi dalam satu server → orchestrator antar server. Pendekatan nyatanya seperti Kubernetes, tetapi cakupannya satu server, satu orchestrator. Diminta: pahami, cek kebenaran untuk saat ini, bandingkan dengan proyek serupa di luar.

---

## 1. Ringkasan Eksekutif

1. **Arah kerangkamu benar, dengan tiga koreksi tingkat/istilah [I].** (a) Di pemakaian industri, CLI itu sendiri (kiro-cli, agy, Claude Code, Codex) disebut *harness*; lapisan yang kamu bangun lebih tepat disebut *control plane per server*. (b) KiroCrew, agy, dan Manus bukan sejenis: agy adalah harness, KiroCrew adalah gateway di atas harness kiro-cli, Manus adalah layanan cloud yang dipanggil lewat REST. (c) Lapisan antar-server (A2A) belum perlu.
2. **Sebagian besar bentuk control plane sudah ada [V][I].** Board + bridge + `board_switch` + dev-ci setara versi kecil dari spesifikasi OpenAI Symphony (§4.3). Yang belum ada: workspace terisolasi per task, kontrak workflow tertulis yang dipakai semua komponen, antarmuka adapter runtime, dan memori bersama.
3. **Celah paling mendesak adalah isolasi agy [V].** Bridge menjalankan agy dengan `--dangerously-skip-permissions` dan `--add-dir` ke checkout utama `galleon-fleet` (§4.3, I1). Ini bukan masalah teoretis: preseden yang sama sudah terdokumentasi di riset lama (mode "Turbo" Antigravity).
4. **Tidak perlu menciptakan protokol baru [I].** Kebutuhanmu tertutup oleh standar yang sudah ada: MCP (tool), AGENTS.md + SKILL.md (aturan dan skill), stream-json atau ACP (menggerakkan harness), A2A (nanti, antar server). Pada uji perilaku, agy terbukti memuat `AGENTS.md` dan `SKILL.md` project [V][^21].
5. **"Tunduk dan patuh" ditegakkan control plane, bukan protokol [I].** Protokol hanya mendefinisikan bentuk pesan. Kepatuhan datang dari tiga hal: control plane memegang transisi status, runtime diberi hak akses minimum, dan hasil diverifikasi oleh gate independen (CI). Kondisi sekarang: verifikasi independen sudah kuat; kepemilikan transisi baru **konvensi** (agy punya akses tulis ke board, jadi tidak dicegah secara teknis); hak akses minimum **belum ada** (§6.2).
6. **Memori bersama adalah bagian tersulit dan paling berisiko [S].** Literatur 2026 mengidentifikasi empat mode gagal: kebocoran tanpa izin, informasi basi, kontradiksi yang bertahan, hilangnya provenance[^16]. Skema memori KiroCrew **sudah** punya sebagian field provenance (`source`, `scope`, `confidence`, `valid_from`, `revision`, `content_hash`) [V][^20]. Yang belum ada: `purpose`, identitas author lintas-runtime, bukti, dan alur persetujuan. Ini mengoreksi ringkasan chat sebelumnya (§10).
7. **Posisi pembangunan: control plane mandiri dulu, bukan di dalam engine Go galleon-fleet [I].** Galleon hari ini belum menampung runtime eksternal (engine Go: 0 pemanggilan `exec.Command` non-test) [V], dan roadmap-nya justru menghapus gateway A2A lama [V] (§4.4). Kontraknya dirancang agar engine Go bisa mengadopsi nanti.

---

## 2. Pertanyaan Riset dan Cakupan

| # | Pertanyaan | Dijawab di |
|---|---|---|
| Q1 | Apakah urutan lapisan yang diusulkan benar menurut praktik industri dan keadaan mesin ini? | §3 |
| Q2 | Apa yang sudah ada di KiroCrew, agy, board, dev-ci, dan galleon-fleet? | §4 |
| Q3 | Proyek dan standar eksternal apa yang menyelesaikan masalah serupa? | §5 |
| Q4 | Di mana analogi Kubernetes dan konsep "runtime patuh" benar, dan di mana patah? | §6 |
| Q5 | Bagaimana rancangan memori bersama dengan author dan tujuan? | §6.4 |
| Q6 | Bagaimana rules, skills, dan steering bisa dibangun bersama? | §6.5 |
| Q7 | Apa yang dibangun, diadopsi, atau ditunda, dan dalam urutan apa? | §7 |

**Di luar cakupan:** kinerja model, biaya langganan runtime, desain UI, penetapan harga Galleon (sudah ada di `product-research/`).

---

## 3. Verifikasi Kerangka Lapisan

| Lapisan menurut Achmad | Fakta | Penilaian |
|---|---|---|
| AI Model → Agent | Standar. | Tidak ada koreksi. |
| "Agent berjalan di atas runtime CLI headless" | agy 1.4.0 mendukung mode headless: `-p/--print`, `--output-format text\|json\|stream-json`, `--input-format stream-json`, `--json-schema`, `--conversation` [V, I2]. KiroCrew memakai provider ACP (`agent.provider = 'acp'`) [V, I5]; bahwa lawan bicaranya kiro-cli berasal dari catatan sesi sebelumnya [I] dan tidak diuji ulang hari ini. | Benar. |
| "AI Agent Harness yang menampung banyak runtime CLI" | Dalam pemakaian industri, CLI itu sendiri yang disebut harness [I]. ACP registry mendaftar Claude Code, Gemini CLI, Codex CLI, Copilot, Kiro, Goose, OpenCode sebagai "agen" yang dijalankan klien[^5]. | Istilah perlu dibedakan. Yang kamu maksud lebih tepat: **control plane yang menampung banyak harness**. |
| "Orchestrator runtime (Manus, KiroCrew, Antigravity)" | Tiga hal beda tingkat: **agy** = harness (CLI). **KiroCrew** = gateway multi-sesi di atas harness kiro-cli, sudah memiliki memori, skills, cron, subagent [V, I5, I7]. **Manus** = layanan cloud dengan REST API untuk membuat dan memantau task[^19] [S]. | Dikoreksi. Manus berbeda kelas kepercayaan (remote, async), bukan setara agy. |
| "Terisolasi dalam 1 server" | Spesifikasi Symphony memang berskala satu service per host dan menyatakan multi-tenant sebagai non-goal[^7] [S]. | Benar. |
| "Orchestrator antar AI server" | A2A v1.0 dirancang untuk delegasi antar agen opaque lintas organisasi[^1][^2] [S]. | Benar sebagai tujuan jauh. Tunda sampai ada server kedua [I]. |
| "Mirip Kubernetes" | §6.3. | Sebagian benar. |

**Urutan yang disarankan [I]:**

```
L0  Model
L1  Harness (CLI headless): kiro-cli, agy, claude, codex ... (milik vendor, tidak diubah)
L2  Control plane per server (yang dibangun): kontrak workflow, adapter runtime,
    workspace + isolasi, memori dan rules bersama, gate verifikasi, kebijakan akses
L3  Antar-server (nanti): A2A
```

---

## 4. Kondisi Saat Ini (As-Is)

### 4.1 KiroCrew

- Menjalankan harness lewat ACP: `agent.provider = 'acp'`, `member_acp_backend = 'kas'` (arti `kas` tidak diverifikasi), `mcp_gateway.max_backends = 64` [V, I5]. Bahwa harness di balik ACP itu kiro-cli adalah catatan sesi lama [I], tidak diuji ulang.
- Persistensi: `memory.db` 24.580.096 byte; 46 skill bawaan dan 16 skill kustom [V, I7]. Enam lapis memori, termasuk lessons, terdokumentasi di riset lama (`capabilities-skills-lessons-steering-audit.md` §2.1) bersumber dari dokumentasi kiro.dev [S, I11].
- Membaca `AGENTS.md` dan `.kiro/steering/*` sebagai konteks otomatis: sesi ini menerima keduanya [V, I10].
- **Skema memori (hanya skema; isi baris tidak dibaca)** [V, I6][^20]:

| Tabel | Kolom relevan |
|---|---|
| `semantic_memory` | `key, value_json, confidence, source, created_at, updated_at, is_deleted` |
| `episodic_memories` | `conversation_id, text, embedding, tags, importance, created_at, is_deleted` |
| `memory_record_meta` | `record_id, revision, subject, scope, valid_from, observed_at, content_hash` |
| `memory_revisions` | `revision, status, before_json, created_at` |
| `memory_events` | `event_type, memory_type, memory_key, old_value, new_value, source, created_at` |

### 4.2 agy (Antigravity CLI 1.4.0)

- Flag headless dan sesi: `-p`, `--output-format`, `--input-format stream-json`, `--json-schema`, `--conversation`, `--continue`, `--sandbox`, `--mode (accept-edits|auto|plan)`, `--add-dir`, `--dangerously-skip-permissions` [V, I2].
- Subcommand: `mcp` (add/remove/list/enable/disable, jadi **klien** MCP), `plugin`, `agent`, `remote-control`, `models`. **Tidak ada** flag atau subcommand ACP maupun mode server pada `--help` [V, I2].
- Binary memuat string `AGENTS.md` (54), `GEMINI.md` (49), `SKILL.md` (51), `.agents/skills` (8); `CLAUDE.md` (0) [V, I3].
- **Uji perilaku:** pada direktori sementara yang berisi `AGENTS.md` (kata sandi acak) dan `.agents/skills/zz-probe-skill/SKILL.md`, agy menjawab kata sandi yang benar dan menyebut nama skill yang benar [V, I4][^21].

### 4.3 Board + bridge + dev-ci (kontrol alur kerja saat ini)

Pemetaan ke komponen spesifikasi Symphony (§3.1 spesifikasi)[^7]:

| Komponen Symphony | Padanan di sini | Celah [I] |
|---|---|---|
| Workflow Loader (`WORKFLOW.md`) | `RULES.md` + `TEMPLATES.md` (prosa) + `validate.py` | Tidak ada kontrak mesin-terbaca yang dipakai bridge, `board_switch`, dan validator bersama |
| Config Layer | `ci.env`, unit systemd | Tersebar |
| Issue Tracker Adapter | File JSON/MD di `board/` | Sudah memadai |
| Orchestrator | `board_switch.py` (timer 5 menit) + bridge | Berupa polling timer, tanpa satu state otoritatif |
| Workspace Manager | **Tidak ada** | agy bekerja di checkout bersama |
| Agent Runner | `_run_agy()` | Terikat pada agy |
| Status Surface | Halaman board | Ada |
| Logging | `bridge.log`, journald, `bridge_events.db` | Ada |
| *(di luar Symphony)* Gate verifikasi | dev-ci: `local/*` commit status | Sudah memadai |

**Fakta isolasi [V, I1]:** `board_agy_bridge.py` baris 201-203 dan 213 menjalankan agy dengan `--dangerously-skip-permissions`, `--add-dir <board>`, `--add-dir <galleon-fleet>`, dan `cwd=<board>`. Artinya agy punya akses tulis penuh ke checkout utama yang juga dipakai manusia. Tidak ada worktree, sandbox, atau pembatasan kredensial per task.

**Yang sudah mendukung kepatuhan [V, I12]:** status task diubah oleh kode bridge, bukan oleh instruksi ke agy; bridge memverifikasi apakah agy benar-benar mengirim branch atau PR (`_verify_agy_delivered`); keputusan hijau/merah dibuat dev-ci, bukan agy; merge hanya oleh poller dan saat ini dimatikan.

**Batasnya [I, diturunkan dari I1]:** pemisahan "bridge yang mengubah status" adalah konvensi, bukan batas teknis. Dengan `--add-dir <board>` dan `--dangerously-skip-permissions`, agy mampu menyunting berkas task JSON secara langsung. Kemampuan itu belum diuji dan tidak ada bukti agy pernah melakukannya.

### 4.4 galleon-fleet (`origin/testing` @ 295d7a7065)

- Engine Go: **0** pemanggilan `exec.Command` non-test [V, I9][^23]. Engine tidak menjalankan CLI agen eksternal.
- Rust: wrapper satu-kali untuk CLI `claude`, `codex`, `gemini`, `opencode` (`crates/clawcrew-tools/src/*.rs`), tanpa kiro dan agy [V, I9].
- Klien ACP: `AcpProcess` (`acp.rs:422`) memulai subprocess. Pemanggil non-test tidak ditemukan dengan grep terarah; belum dibuktikan sebagai kode mati[^22].
- Skema engine: tabel `runs`, `run_events`, `tasks` (SQLite) dan `vector_documents(id, content, embedding, metadata, scope, created_at)` (Postgres). **Tidak ada kolom author atau purpose eksplisit** (`metadata` berupa teks bebas) [V, I9].
- Dokumen arah: memori persisten per scope Fleet/Ship/Squad/Crew/Run, "learning by consent", dan berbagi memori lintas-Ship diblokir default (`galleon-product-definition.md` baris 43-45) [V, I9]. Implementasi consent di engine **tidak diverifikasi**.
- Roadmap: G-33 (sub-agent/handoff/A2A sebagai Artifact reference) masih rencana P2; N-12, R-41, dan PR-62 **menghapus** REST/WS/A2A gateway lama [V, I9].

### 4.5 Aturan dan steering yang terduplikasi

17 file, 95.115 byte, tersebar di 3 format runtime (`AGENTS.md`; `.gemini/*` dan `~/.gemini/GEMINI.md`; `.kiro/steering/*`) [V, I8][^24]. Duplikasi terverifikasi hanya pada aturan `sccache` (6 file). Proporsi duplikasi keseluruhan tidak diukur. Tidak ada satu pun file aturan yang memuat author atau tujuan, dan lessons KiroCrew (di `memory.db`) tidak terbaca agy [I].

---

## 5. Lanskap Eksternal

### 5.1 Protokol dan standar

| Standar | Fungsi | Status menurut sumber | Relevansi untukmu [I] |
|---|---|---|---|
| **MCP** | Agen ↔ tool/data | Didonasikan ke Agentic AI Foundation (Linux Foundation) pada 9 Des 2025[^3] [S]. Angka adopsi dari artikel tidak dijadikan dasar[^4] | agy dan KiroCrew sama-sama klien MCP [V]. Satu server MCP untuk board dan memori memberi dua runtime satu permukaan koordinasi |
| **A2A** | Agen ↔ agen opaque, discovery lewat agent card | v1.0 stabil (Maret 2026 menurut sebagian sumber, April menurut yang lain[^1]); masuk AAIF 17 Agu 2026[^2] [S] | Skema task dan artifact yang baik dipinjam. Transport antar-agen terlalu berat untuk proses lokal satu mesin |
| **ACP** | Editor/klien ↔ agen coding (stdio JSON-RPC) | Dikembangkan Zed dan JetBrains; registry 50 agen per Juni 2026 termasuk Kiro[^5] [S]. Bukan agen↔agen[^6] | Cara standar menggerakkan harness secara programatik. KiroCrew sudah memakainya [V] |
| **AGENTS.md** | Instruksi project untuk agen coding | Disumbangkan OpenAI ke AAIF[^3] [S] | Terbukti dimuat agy [V, I4] dan oleh KiroCrew [V, I10] |
| **Agent Skills (SKILL.md)** | Paket instruksi on-demand | Dilaporkan dibaca 32+ sampai ~40 produk, termasuk Gemini CLI, Kiro, Goose[^18] [S] | Terbukti dimuat agy dari `.agents/skills/` [V, I4]. Dukungan KiroCrew untuk `.agents/skills/` belum diuji |

### 5.2 Orkestrator agen coding

| Proyek | Inti | Yang relevan | Catatan sumber |
|---|---|---|---|
| **OpenAI Symphony** | Spesifikasi layanan yang membaca tracker, membuat workspace terisolasi per issue, menjalankan sesi agen; policy di `WORKFLOW.md` dalam repo; pemulihan dari tracker dan filesystem tanpa database | Paling mirip board + bridge. Non-goals: UI kaya, multi-tenant, workflow engine umum | Spec dibaca sebagian (±8.000 karakter dari 89,9 KB)[^7]; tanggal rilis dan lisensi dari sumber sekunder[^8] |
| **Gas Town + Beads** | Hierarki Mayor/Rig/Crew/Polecat; state di hook berbasis git; Beads = issue tracker graf berbasis Dolt sebagai memori agen | Metafora organisasi mirip Quartermaster/Ship/Squad/Crew | MIT, 18,4k bintang; klaim skala "20-30 agen" adalah klaim proyek sendiri[^9][^10] |
| **Agent Orchestrator** (dulu Composio) | Worktree per sesi; CI gagal dan review comment dirutekan kembali ke sesi penghasilnya; 26 harness | Siklus "merah → kembali ke eksekutor" sama dengan alur kita | Dari artikel vendor pesaing[^11] |
| **Vibe Kanban, Claude Squad, Conductor, dll.** | Kanban/terminal untuk paralelisasi agen | Konsensus: git worktree sebagai primitif isolasi | Beberapa dihentikan (Vibe Kanban)[^12] |

### 5.3 Analogi Kubernetes

- **agent-sandbox (Kubernetes SIG Apps):** CRD `Sandbox` untuk satu pod stateful dengan identitas stabil dan storage persisten, plus `SandboxTemplate`, `SandboxClaim`, `SandboxWarmPool`[^13] [S]. Dokumen k8s menyatakan agen "biasanya workload terisolasi, stateful, singleton" berbeda dari service stateless.
- **kagent / agent-substrate (CNCF, Solo.io):** eksekusi pooled untuk agen ephemeral[^14] [S].
- Artikel CNCF "Why sandboxing your agent is not enough": hanya bagian pembuka terbaca; **tidak dijadikan dasar** argumen di dokumen ini[^15].

### 5.4 Memori bersama

- Mem0, Letta, Zep/Graphiti, Cognee, LangMem: layanan memori, awalnya untuk asisten personal [S].
- Riset 2026: empat mode gagal memori bersama multi-agen[^16]; benchmark GateMem untuk memori multi-principal[^16]; draf `memorywire` sebagai format kawat netral[^16]. **Belum ada standar dominan** [S].
- Keamanan: serangan injeksi memori dilaporkan berhasil >95% pada eksperimen yang dikutip vendor[^17] [S].

### 5.5 Manus

REST API untuk membuat dan mengambil hasil task[^19] [S]. Cocok sebagai runtime **remote asinkron** dengan adapter berbeda dari CLI lokal [I]. Tidak diuji.

---

## 6. Analisis

### 6.1 Apa yang benar dari kerangka dan apa yang tidak

Bagian yang benar: pemisahan runtime (vendor) dari lapisan koordinasi (milikmu), satu orchestrator per server, dan kebutuhan memori dan aturan bersama. Bagian yang perlu dikoreksi ada di §3. Intinya satu: **jangan membangun "harness lagi"**. Harness sudah disediakan vendor. Yang belum ada adalah kontrak antar-harness.

### 6.2 "Tunduk dan patuh" ditegakkan di mana

Protokol (MCP, A2A, ACP) mendefinisikan format pesan, bukan kepatuhan [I]. Tiga mekanisme penegak yang berlaku di semua orkestrator yang disurvei [I]:

| Mekanisme | Arti | Kondisi sekarang |
|---|---|---|
| **1. Kepemilikan transisi** | Hanya control plane yang boleh mengubah status akhir dan melakukan merge | **Konvensi, belum batas teknis** [V, I]: bridge yang mengubah status dan memverifikasi pengiriman, merge hanya oleh poller (sekarang off), tetapi agy punya akses tulis ke direktori board (§4.3) |
| **2. Hak akses minimum / isolasi** | Runtime hanya melihat workspace-nya, kredensial dipegang sisi host | **Tidak ada** untuk agy [V, I1]. Preseden: riset lama mendokumentasikan kasus Antigravity, termasuk mode "Turbo" yang mematikan sandbox dan celah *native tool* yang melewati gate (`agent-subagent-permission-scoping-survey.md` §2.4) [S, I11]. Symphony menyimpan kredensial tracker di sisi host dan tidak meneruskannya ke proses anak[^7] [S] |
| **3. Verifikasi independen** | Kebenaran hasil ditentukan gate di luar runtime | Ada [V]: dev-ci. Caveat: gate yang sudah merah di base "tidak dihitung" (baseline ratchet), sehingga hijau saat ini hanya menguji gate guard |

### 6.3 Analogi Kubernetes

| Konsep k8s | Berlaku di 1 server? | Catatan [I] |
|---|---|---|
| Desired state + loop rekonsiliasi | **Ya** | Inti Symphony. Gantikan timer polling dengan satu loop berbasis event |
| Identitas stabil + storage persisten per unit | **Ya** | Padanan: satu workspace (worktree) per task, bertahan antar run, dibersihkan saat task selesai |
| Sandbox/pod sebagai batas isolasi | **Ya, tanpa k8s** | Container atau worktree + `agy --sandbox`; konfigurasi `--sandbox` pada mode headless bridge **belum diuji** |
| Penjadwalan lintas node, service mesh, CRD/etcd | **Tidak** | Biaya operasional besar di i5 4-core yang sudah jenuh oleh dua build Rust |
| Determinisme | **Patah** | Controller k8s deterministik; agen LLM tidak. Rekonsiliasi harus mengasumsikan hasil bisa salah dan memverifikasinya |

### 6.4 Rancangan memori bersama dengan author dan tujuan

Dipetakan dari empat mode gagal[^16] ke field, dan dibandingkan dengan keadaan sekarang [V][^20]:

| Mode gagal / kebutuhan | Field | KiroCrew `memory.db` | Galleon `vector_documents` |
|---|---|---|---|
| Kebocoran lintas scope | `scope` + aturan akses | `memory_record_meta.scope` ada | `scope` ada |
| Hilangnya provenance: siapa | `author_runtime`, `author_agent` | `source` ada (arti nilai tidak diverifikasi); tidak ada identitas runtime | Tidak ada kolom |
| Provenance: mengapa | `purpose` | Tidak ada | Tidak ada |
| Provenance: bukti | `evidence` (task, PR, commit) | Tidak ada | Tidak ada |
| Kepercayaan | `confidence` | `semantic_memory.confidence` ada | Tidak ada |
| Informasi basi | `valid_from`, `observed_at`, `ttl` | `valid_from`, `observed_at` ada; TTL tidak terlihat | `created_at` saja |
| Kontradiksi bertahan | `supersedes`, `status` | `memory_revisions.status` (riwayat revisi) | Tidak ada |
| Integritas | `content_hash` | Ada | Tidak ada |
| Persetujuan sebelum berlaku | `status (proposed/approved/revoked)`, `approved_by` | Tidak ada (lesson dibuat langsung lewat `learn_add`) | Dokumen menyebut "learning by consent"; implementasi tidak diverifikasi |

**Rancangan minimal [I]:** satu tabel `memory_item` dengan field di atas, diakses lewat tool MCP `memory.propose`, `memory.search`, `memory.approve`. Mulai dengan FTS (tanpa embedding) karena embedding menambah beban dan klaim "vector" yang tidak terbukti sudah pernah menyesatkan di repo ini. Pelajaran yang disetujui mengalir `proposed → approved → dipromosikan ke AGENTS.md atau SKILL.md lewat PR`, sehingga git menjadi jejak audit. Aturan keras: **agen hanya boleh mengusulkan**, tidak menyetujui.

### 6.5 Rules, skills, steering bersama

- Fakta [V]: agy memuat `AGENTS.md` dan skill di `.agents/skills/`; KiroCrew memuat `AGENTS.md` dan `.kiro/steering/*`.
- **Rekomendasi [I]:** `AGENTS.md` sebagai satu sumber kanonik yang singkat (indeks dan aturan inti), dan detail dipindahkan ke `.agents/skills/` (dimuat on-demand). View khusus runtime (`.kiro/steering`, `.gemini/*`) hanya berisi delta yang tidak punya padanan standar.
- **Trade-off yang harus diperhatikan [I]:** `AGENTS.md` selalu dimuat, sehingga isinya membebani konteks di setiap runtime. Ini bertentangan dengan preferensi hemat token (steering ber-`inclusion: fileMatch` hanya dimuat saat relevan). Mitigasi: batasi `AGENTS.md` pada aturan yang benar-benar universal, taruh sisanya di skill.
- **Belum diuji:** apakah KiroCrew memuat `.agents/skills/`; prioritas bila `AGENTS.md` dan `GEMINI.md` bertentangan di agy.

### 6.6 Bangun, adopsi, atau tunda

| Kebutuhan | Putusan [I] | Alasan |
|---|---|---|
| Protokol baru | **Jangan bangun** | MCP + AGENTS.md + SKILL.md + stream-json/ACP sudah cukup |
| Kontrak workflow | **Bangun**, adopsi struktur Symphony | Belum ada yang mesin-terbaca |
| Adapter runtime | **Bangun** (agy via stream-json, kiro via ACP) | Bridge hard-code ke agy |
| Isolasi per task | **Bangun** (git worktree) | Konsensus industri[^11]; celah terverifikasi |
| Memori bersama | **Bangun tipis**, jangan adopsi layanan penuh dulu | Belum ada standar, dan risiko poisoning perlu kontrol penuh |
| Kubernetes | **Jangan** | §6.3 |
| A2A antar server | **Tunda** | Belum ada server kedua |
| Orkestrator jadi (Symphony, Agent Orchestrator, Gas Town) | **Evaluasi dulu** sebelum memutuskan membangun sendiri | Belum dijalankan; asumsi harness mereka Claude/Codex |

### 6.7 Posisi pembangunan: di dalam galleon-fleet atau mandiri

Rekomendasi **mandiri dulu** [I], dengan alasan:
1. Engine Go belum menjalankan CLI eksternal sama sekali [V] dan klien ACP Rust belum terbukti terpakai[^22].
2. Roadmap menghapus A2A lama dan baru merencanakan handoff sebagai G-33 (P2) [V].
3. `dev-task-2/3` dikerjakan tim lain dan tidak boleh disentuh tanpa konfirmasi (AGENTS.md).
4. Kebutuhan sekarang adalah alat pengembangan internal (KiroCrew + agy membangun Galleon). Galleon sebagai produk memiliki kelas kepercayaan dan roadmap sendiri.

Kontrak (status workflow, antarmuka `Runtime`, skema `memory_item`) dirancang netral agar engine Go dapat mengadopsinya kemudian.

---

## 7. Rekomendasi Bertahap dan Kriteria Penerimaan

| Fase | Isi | Kriteria penerimaan (dapat diuji) |
|---|---|---|
| **0** | (a) Worktree per task untuk agy, `--add-dir` ke checkout utama dihapus. (b) `AGENTS.md` kanonik + `.agents/skills/`; duplikasi aturan dihapus | (a) Dua task agy paralel berjalan dan `git -C ~/Apps/galleon-fleet status` tidak berubah. (b) Probe kata sandi memberi hasil sama di agy dan KiroCrew; aturan `sccache` hanya ada di 1 file |
| **1** | Kontrak workflow tertulis (status, pemicu, retry, handoff) yang dibaca bridge, `board_switch`, dan validator. Antarmuka `Runtime` dengan implementasi agy dan kiro. Board diekspos sebagai server MCP | Menambah runtime stub tidak mengubah logika transisi. Agen mengubah status lewat tool MCP, bukan edit JSON |
| **2** | `memory_item` + `propose/search/approve` | Satu pelajaran yang diusulkan kiro terlihat dari agy dengan author dan tujuan; yang belum disetujui tidak terlihat |
| **3** | Satu daemon berbasis event menggantikan timer | Tidak ada timer polling tersisa untuk transisi workflow |
| *(nanti)* | A2A | Hanya bila ada server kedua |

---

## 8. Risiko dan Yang Sengaja Tidak Dibangun

- **Memory poisoning dan basi** [S][^17]: wajib ada gerbang persetujuan manusia sebelum memori menjadi aturan.
- **Beban AGENTS.md** [I]: lihat §6.5.
- **Ketergantungan pada standar muda** [I]: A2A baru v1.0, ACP registry masih berkembang; bungkus di balik antarmuka `Runtime` sendiri.
- **Kompleksitas orkestrator jadi** [I]: Gas Town berhierarki berat; jangan ditiru utuh.
- **Tidak dibangun:** protokol baru, k8s, layanan memori penuh, UI umum, orkestrasi antar-server.

---

## 9. Pertanyaan Terbuka untuk Owner

1. Control plane dibangun mandiri (rekomendasi) atau di dalam engine Go galleon-fleet?
2. Apakah runtime remote seperti Manus masuk v1? (rekomendasi: tidak)
3. Siapa yang menyetujui promosi memori menjadi aturan: Owner saja, atau Lead juga?
4. Setelah worktree, apakah `--dangerously-skip-permissions` diganti `--sandbox` + addir terbatas? (`--sandbox` pada mode headless belum diuji)
5. Ambang minimal agar baseline ratchet tidak lagi menyembunyikan gate merah (Lint, Check, Security) sebelum auto-merge dinyalakan?

---

## 10. Log Koreksi atas Ringkasan Chat (2026-10-18)

| # | Ringkasan chat berkata | Setelah verifikasi |
|---|---|---|
| 1 | "Tidak ada satu pun [file aturan/memori] yang punya author atau tujuan" | Untuk file aturan: benar. Untuk **memori KiroCrew: keliru sebagian**: ada `source`, `scope`, `confidence`, `valid_from`, `observed_at`, `revision`, `content_hash` [V]. Yang tidak ada: `purpose`, identitas runtime, bukti, persetujuan |
| 2 | "±95 KB di sekitar 15 file" | 17 file, 95.115 byte [V][^24] |
| 3 | "agy membaca AGENTS.md/SKILL.md" (sebatas string di binary) | Sekarang terbukti perilaku, n=1 [V][^21]; tetap belum diuji: prioritas bila bertentangan |
| 4 | "A2A v1.0 Mar 2026" | Sumber berbeda: Maret vs April 2026[^1] |

---

## 11. Rujukan dan Bukti

### A. Sumber eksternal

Tingkat baca: **PENUH** = halaman dibaca penuh; **SEBAGIAN** = `web_fetch` terpotong 8.000 karakter pertama; **CUPLIKAN** = hanya cuplikan hasil pencarian. Jenis: P = primer (pemilik standar/proyek), K = komunitas/sekunder, V = vendor dengan kepentingan.

| ID | Sumber | URL | Jenis | Tingkat baca | Dipakai untuk |
|---|---|---|---|---|---|
| S1 | Linux Foundation, rilis pers A2A 1 tahun | https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year | P | CUPLIKAN | A2A v1.0, 150+ organisasi |
| S2 | Forbes, 19 Agu 2026, "Agent2Agent Joins The Agentic AI Foundation Alongside MCP" | https://www.forbes.com/sites/janakirammsv/2026/08/19/agent2agent-joins-the-agentic-ai-foundation-alongside-mcp/ | K | CUPLIKAN | A2A masuk AAIF 17 Agu; v1.0 Maret 2026; fitur v1.0 |
| S3 | note.com, analisis spesifikasi A2A | https://note.com/snake_dragon/n/n21e343579a34?hl=en | K | CUPLIKAN | Menyebut v1.0 April 2026 (berbeda dari S2) |
| S4 | Ultralytics Glossary, A2A | https://www.ultralytics.com/glossary/agent2agent-protocol | K | CUPLIKAN | v1.0 Maret 2026 |
| S5 | rywalker.com, Google A2A | https://rywalker.com/research/google-a2a | K | CUPLIKAN | v1.0 stabil Maret 2026 |
| S6 | Blog MCP, "MCP joins the Agentic AI Foundation" (URL bertanggal 2025-12-09) | http://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/ | P | CUPLIKAN | Donasi MCP ke AAIF |
| S7 | Linux Foundation, pembentukan AAIF | https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation | P | CUPLIKAN | AAIF menaungi MCP, goose, AGENTS.md |
| S8 | arXiv 2603.13417, Design Patterns for Deploying AI Agents with MCP | https://arxiv.org/html/2603.13417v1 | K | CUPLIKAN | Angka adopsi MCP (tidak dijadikan dasar) |
| S9 | JetBrains, "ACP Agent Registry Is Live" | https://blog.jetbrains.com/ai/2026/01/acp-agent-registry/ | P | CUPLIKAN | ACP seperti LSP untuk agen; registry |
| S10 | DEV, "Agent Client Protocol (ACP): Connect Any AI Agent to Any Editor" (Jun 2026) | https://dev.to/dmaxdev/agent-client-protocol-acp-connect-any-ai-agent-to-any-editor-2p0m | K | SEBAGIAN | Registry 50 agen, daftar termasuk Kiro; ACP vs MCP |
| S11 | rywalker.com, Agent Client Protocol (Zed) | https://rywalker.com/research/zed-agent-client-protocol | K | CUPLIKAN | "Agent-to-client, not agent-to-agent" |
| S12 | OpenAI, Symphony SPEC.md | https://github.com/openai/symphony/blob/main/SPEC.md | P | SEBAGIAN (±8.000 dari 89,9 KB) | Komponen, goals, non-goals, pemulihan tanpa DB |
| S13 | OpenAI, "An open-source spec for Codex orchestration: Symphony" | https://openai.com/index/open-source-codex-orchestration-symphony | P | CUPLIKAN | Tracker sebagai control plane |
| S14 | Verdent, "What Is Symphony Open Source?" | https://www.verdent.ai/fr/guides/what-is-symphony-open-source | K | CUPLIKAN | Tanggal rilis 27 Apr 2026, Apache 2.0, referensi Elixir |
| S15 | Repo Gas Town | https://github.com/gastownhall/gastown | P | SEBAGIAN | Arsitektur, MIT, bintang, klaim skala |
| S16 | Wiki Beads | https://github.com/gastownhall/beads/wiki | P | CUPLIKAN | Graf issue berbasis Dolt |
| S17 | Wiki Learn AI, Beads | https://ai.miraheze.org/wiki/Beads | K | CUPLIKAN | Rilis Oktober 2025 |
| S18 | Augment Code, "9 Open-Source Agent Orchestrators for AI Coding (2026)" | https://www.augmentcode.com/tools/open-source-agent-orchestrators | V | SEBAGIAN | Agent Orchestrator; konsensus worktree; keterbatasan koordinasi |
| S19 | easy-vibe-kanban (README fork) | https://github.com/toby1123yjh/easy-vibe-kanban | K | CUPLIKAN | Vibe Kanban dihentikan BloopAI |
| S20 | kubernetes.io, "Running Agents on Kubernetes with Agent Sandbox" (20 Mar 2026) | https://v1-36.docs.kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/ | P | CUPLIKAN | Karakter agen: terisolasi, stateful, singleton |
| S21 | Dokumentasi agent-sandbox | https://agent-sandbox.sigs.k8s.io/docs/ | P | CUPLIKAN | CRD Sandbox, Template, Claim, WarmPool |
| S22 | Hashnode, playbook Agent Sandbox 2026 | https://ecorpit.hashnode.dev/stateful-ai-agents-on-kubernetes-the-2026-agent-sandbox-and-gpu-scheduling-playbook | K | CUPLIKAN | GA di GKE 20 Mei 2026 (tidak diverifikasi) |
| S23 | CNCF, "Is a Pod the right deployment unit for an AI agent?" (14 Jul 2026) | https://www.cncf.io/blog/2026/07/14/is-a-pod-the-right-deployment-unit-for-an-ai-agent/ | P | CUPLIKAN | kagent dan agent-substrate |
| S24 | CNCF, "Why sandboxing your agent is not enough" (7 Jul 2026) | https://www.cncf.io/blog/2026/07/07/why-sandboxing-your-agent-is-not-enough/ | P | SEBAGIAN (hanya pembuka) | **Tidak dijadikan dasar** |
| S25 | arXiv 2606.24535, Governed Shared Memory for Multi-Agent LLM Systems | https://arxiv.org/abs/2606.24535 | K | CUPLIKAN | Empat mode gagal memori bersama |
| S26 | arXiv 2606.18829, GateMem | https://arxiv.org/pdf/2606.18829.pdf | K | CUPLIKAN | Benchmark memori multi-principal |
| S27 | arXiv 2606.01138, memorywire | https://arxiv.org/html/2606.01138 | K | CUPLIKAN | Format kawat netral untuk operasi memori (draf) |
| S28 | Mem0, "AI memory security best practices" | https://mem0.ai/blog/ai-memory-security-best-practices | V | CUPLIKAN | Angka MINJA dari Dong et al. 2025 (paper asli tidak dibaca) |
| S29 | SSOJet, "15 SKILL.md Playbooks..." | https://ssojet.com/blog/skill-md-playbooks | K | CUPLIKAN | 32+ tool membaca SKILL.md |
| S30 | DevToolLab, Agent Skills Explained (2026) | https://devtoollab.com/blog/agent-skills-open-standard-guide | K | CUPLIKAN | ~40 produk, termasuk Gemini CLI, Junie, Kiro, Goose |
| S31 | Manus, dokumentasi API | https://manus.im/docs/integrations/manus-api | P | CUPLIKAN | REST API untuk task |

### B. Bukti internal (dapat diulang)

Versi: `agy 1.4.0`, `kirocrew 0.9.0`; `galleon-fleet origin/testing = 295d7a7065` (2026-10-18); `board HEAD = c094ef865e`; `dev-ci HEAD = 3dbceecbf4`.

| ID | Bukti | Cara mengulang |
|---|---|---|
| I1 | Peluncuran agy oleh bridge | `grep -nE '"--dangerously-skip-permissions"\|"--add-dir"\|cwd=str\(BOARD\)' ~/Apps/board/tools/agy-bridge/board_agy_bridge.py` → baris 201, 202, 203, 213 |
| I2 | Flag dan subcommand agy | `agy --help`; `agy mcp --help` |
| I3 | String di binary agy | `grep -a -o -F "<string>" "$(readlink -f ~/.local/bin/agy)" \| wc -l` → AGENTS.md 54, GEMINI.md 49, CLAUDE.md 0, SKILL.md 51, `.agents/skills` 8, `.agent/skills` 0, `.gemini/skills` 0 |
| I4 | Uji perilaku agy | Direktori sementara `git init` berisi `AGENTS.md` ("kata sandi proyek adalah PELICAN-7421") dan `.agents/skills/zz-probe-skill/SKILL.md`; `agy -p "<dua baris: kata sandi proyek, nama skill berawalan zz->" --print-timeout 120s` → keluaran `PELICAN-7421` dan `zz-probe-skill` |
| I5 | Konfigurasi KiroCrew | Baca `~/.kiro/crew/config.json`: `agent.provider='acp'`, `agent.acp_backend=''`, `agent.member_acp_backend='kas'`, `mcp_gateway.max_backends=64` |
| I6 | Skema memori KiroCrew | `sqlite3` mode read-only terhadap `~/.kiro/crew/memory.db`, hanya `sqlite_master`; 7 tabel tanpa tabel FTS/indeks |
| I7 | Skill dan ukuran memori | `ls ~/.kiro/skills \| wc -l` = 16; `ls ~/.kiro/crew/skills \| wc -l` = 46; `stat -c %s ~/.kiro/crew/memory.db` = 24580096 |
| I8 | File aturan | `wc -c` pada `AGENTS.md`, `.gemini/steering.md`, `.gemini/rules/*.md`, `.kiro/steering/*.md`, `~/.kiro/steering/*.md`, `~/.gemini/GEMINI.md` → 17 file, 95.115 byte; `grep -l sccache` → 6 file |
| I9 | galleon-fleet | `grep -rnE "exec\.Command(Context)?\(" engine --include=*.go \| grep -v _test.go \| wc -l` → 0; skema di `engine/pkg/store/sqlite/schema.go:15,27,40` dan `engine/pkg/store/postgres/store.go:61`; `crates/clawcrew-tools/src/{claude_code:191,codex_cli:173,gemini_cli:153,opencode_cli:153}.rs`; `crates/clawcrew-runtime/src/rpc/acp.rs:422,435`; `standard-docs/product/galleon-product-definition.md:43-45`; `standard-docs/roadmap/G-go-engine.md:43`; `R-rust.md:22,51`; `N-rename-and-legacy-cleanup.md:23` |
| I10 | KiroCrew memuat AGENTS.md dan steering | Konteks sesi ini memuat `AGENTS.md` repo dan `.kiro/steering/*.md` otomatis |
| I11 | Riset lama yang berhubungan | `research/capabilities-skills-lessons-steering-audit.md` §2.1; `research/agent-subagent-permission-scoping-survey.md` §2.4 dan §3; `research/memory-data-governance-audit.md` |
| I12 | Verifikasi pengiriman dan kepemilikan transisi | `board_agy_bridge.py` (`_verify_agy_delivered`, penetapan `review`/`done`); `board_switch.py`; dev-ci `bin/ci-poller` |

### C. Metode pencarian

Alat: `web_search` (cuplikan hasil) dan `web_fetch` (mode selektif, terpotong 8.000 karakter). Halaman yang dibuka dengan `web_fetch`: S10, S12, S15, S18, S24 (S24 dan S10 hanya sebagian). Selain itu semua sumber hanya dibaca dari cuplikan hasil pencarian. Kueri yang dipakai:

1. `Agent2Agent A2A protocol Linux Foundation 2026 version adoption status`
2. `Model Context Protocol Agentic AI Foundation Linux Foundation AGENTS.md MCP donated 2026`
3. `Agent Client Protocol ACP Zed JetBrains coding agents standard 2026 agents supported`
4. `orchestrate multiple coding agent CLIs Claude Code Codex Gemini parallel git worktrees kanban vibe-kanban Gas Town`
5. `kagent CNCF Kubernetes agents CRD vs kubernetes-sigs agent-sandbox isolated stateful agent runtime 2026`
6. `shared memory multiple AI agents provenance author scope Mem0 Letta Zep Graphiti memory poisoning 2026`
7. `Agent Skills SKILL.md open standard agentskills.io supported Claude Code Codex Gemini CLI Kiro Antigravity`
8. `OpenAI Symphony SPEC.md orchestrator Linear tickets workspace per issue Codex app-server`
9. `Beads Steve Yegge git-backed issue tracker for AI coding agents memory dependency graph`
10. `Antigravity CLI agy AGENTS.md GEMINI.md skills MCP headless print mode stream-json documentation`
11. `Manus AI agent API headless integration CLI developers 2026`

---

## 12. Catatan Kaki

[^1]: Tanggal rilis A2A v1.0 tidak konsisten antar sumber: Forbes (S2), Ultralytics (S4), dan rywalker (S5) menyebut **Maret 2026**; note.com (S3) menyebut **April 2026**. Rilis pers LF (S1) membahas v1.0 pada peringatan satu tahun tanpa tanggal rinci di cuplikan. Konflik tidak diselesaikan; rujuk spesifikasi resmi untuk tanggal pasti.
[^2]: Forbes (S2) menyebut AAIF mengumumkan pemindahan A2A pada 17 Agustus 2026 dan menekankan bahwa yang berubah adalah foundation yang menaungi, bukan siapa yang mengendalikan; Google telah menyerahkan A2A ke Linux Foundation sejak Juni 2025. Fitur v1.0 yang disebut: multi-protocol binding, negosiasi versi, multi-tenancy, agent card bertanda tangan.
[^3]: MCP didonasikan ke AAIF (directed fund Linux Foundation) pada 9 Des 2025 (tanggal dari URL S6). Judul rilis pers pembentukan AAIF (S7) menyebut MCP, goose, dan AGENTS.md sebagai kontribusi pendiri; kepemilikan asli masing-masing (Anthropic, Block, OpenAI) berasal dari artikel sekunder yang tidak dicantumkan.
[^4]: Angka "10.000+ server MCP" dan "97 juta unduhan SDK per bulan" muncul di S8 dan satu artikel hashnode. Ini angka makro dari sumber sekunder yang tidak diverifikasi; tidak dipakai sebagai dasar keputusan desain.
[^5]: S10 (artikel DEV, terbaca sebagian): ACP dibuat Zed pada Agustus 2025, JetBrains bergabung, registry diluncurkan bersama Januari 2026 (S9), 50 agen per Juni 2026; tabel artikel mencantumkan Claude Agent, Gemini CLI, Codex CLI, GitHub Copilot, Cursor, Goose, Kiro, Junie, OpenCode, dan lainnya. Antigravity tidak tampil di bagian yang terbaca; tidak ditarik kesimpulan.
[^6]: S11: ACP adalah "agent-to-client, not agent-to-agent". S10 membedakan ACP (editor ↔ agen) dari MCP (agen ↔ tool).
[^7]: S12 dibaca sebagian: bagian 1 sampai awal 4.1 dari spesifikasi 2.312 baris. Yang dikutip: komponen §3.1 (Workflow Loader, Config Layer, Issue Tracker Adapter, Orchestrator, Workspace Manager, Agent Runner, Status Surface, Logging), goals/non-goals §2, kredensial tracker sisi host (§1 dan §3.3), pemulihan tanpa database (§2.1). Bagian tentang mesin status, retry/backoff, dan rekonsiliasi **tidak terbaca**; klaim tentang detailnya hanya berdasar daftar goals.
[^8]: S14 (sekunder) menyebut rilis 27 April 2026 oleh tiga insinyur OpenAI, lisensi Apache 2.0, referensi implementasi Elixir/BEAM. Lisensi dan tanggal tidak diverifikasi dari repo.
[^9]: S15: 18,4k bintang, 1,7k fork, lisensi MIT, 7.770 commit pada saat dibaca. Klaim "scale comfortably to 20-30 agents" adalah klaim proyek sendiri, tidak diuji.
[^10]: S16: "distributed graph issue tracker for AI agents, powered by Dolt". S17 (sekunder): dirilis Oktober 2025 oleh Steve Yegge.
[^11]: S18 adalah artikel vendor (Augment Code menjual produk pesaing, Cosmos). Klaim "git worktree menjadi primitif isolasi konsensus" dan "kebanyakan alat menyerahkan keputusan merge ke manusia" dipakai sebagai indikasi, bukan fakta netral. Detail Agent Orchestrator (Apache-2.0, 26 harness, worktree per sesi) dari hasil uji penulis artikel pada satu monorepo TypeScript.
[^12]: S19 (README fork, sekunder): "Vibe Kanban (sunset by BloopAI)".
[^13]: S20 mengutip: agen "typically isolated, stateful, singleton workloads" yang butuh "persistent identity and a secure scratchpad". S21: CRD `Sandbox` plus `SandboxTemplate`, `SandboxClaim`, `SandboxWarmPool`. Klaim GA di GKE 20 Mei 2026 hanya dari S22 (sekunder).
[^14]: S23: agent-substrate (kagent/Solo.io) untuk eksekusi pooled agen ephemeral; agent-sandbox untuk agen singleton stateful.
[^15]: S24 terpotong di bagian pembuka. Judulnya menyatakan sandbox saja tidak cukup, tetapi argumen lengkapnya tidak terbaca, jadi argumen "sandbox tidak sama dengan kepatuhan" di dokumen ini adalah inferensi penulis [I] yang ditopang bukti lokal (I1) dan riset lama (I11).
[^16]: S25 (cuplikan abstrak): empat mode gagal: *unauthorized leakage, stale propagation, contradiction persistence, provenance collapse*. S26: benchmark GateMem untuk memori multi-principal dengan kontrol akses dan penghapusan aktif. S27: `memorywire`, draf Juni 2026, sebelumnya bernama "Agent Memory Protocol". Ketiganya preprint arXiv; tidak ditinjau sejawat sepengetahuan penulis.
[^17]: S28 (blog vendor) mengutip Dong et al. (2025) tentang serangan MINJA: injeksi >95% dan keberhasilan serangan 70% tanpa hak khusus. Makalah aslinya tidak dibaca.
[^18]: S29 menyebut 32+ tool membaca SKILL.md (tanggal verifikasi sumber 2026-06-07); S30 menyebut sekitar 40 produk di showcase agentskills.io per Juni 2026, termasuk Gemini CLI, Junie, Kiro, Goose. Situs agentskills.io tidak dibuka langsung.
[^19]: S31: "RESTful API ... trigger tasks, manage files, and receive results programmatically". Tidak diuji; tidak diketahui apakah ada mode CLI resmi.
[^20]: Dibaca dari `sqlite_master` dengan koneksi read-only; isi baris tidak dibaca. Makna nilai kolom `source` tidak diverifikasi. Tabel FTS dan indeks diabaikan dalam daftar.
[^21]: Uji n=1 pada 2026-10-18, direktori sementara. Tidak menguji prioritas saat `AGENTS.md` dan `GEMINI.md` bertentangan, tidak menguji bersama `--sandbox`, dan tidak menguji kestabilan antar run. Direktori uji dihapus setelahnya.
[^22]: Pencarian `AcpProcess::|AcpClient::|AcpProcess {` pada `crates/` dan `apps/`, mengecualikan berkas uji dan `acp.rs` sendiri, tidak menemukan pemanggil. Pemakaian lewat `AcpAdapter` atau trait dapat luput. Belum dibuktikan sebagai kode mati.
[^23]: Graphify tidak terpasang pada host ini (`graphify-out/` tidak ada), padahal `AGENTS.md` mengharuskannya didahulukan. Pencarian internal memakai `grep` terarah; hubungan tak langsung mungkin terlewat.
[^24]: Rincian ukuran: `AGENTS.md` 6.407; `.gemini/steering.md` 17.246; `.gemini/rules/*` 16.022 (2 file); `.kiro/steering/*` repo 22.770 (7 file); `~/.kiro/steering/*` 24.176 (5 file); `~/.gemini/GEMINI.md` 8.494. Tidak semua runtime memuat semua file; `AGENTS.md` dan `GEMINI.md` dapat tumpang tindih sebagian.
