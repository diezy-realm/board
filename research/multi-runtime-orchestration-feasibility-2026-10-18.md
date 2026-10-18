---
title: Orkestrasi Multi-Runtime CLI Headless di Galleon — Kelayakan, Ketentuan Vendor, dan Tantangan
status: research
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: control-plane-multi-runtime-landscape-2026-10-18.md
informs: adr-control-plane-interface-2026-10-18.md (revisi 2); standard-docs/decisions/owner-decisions/ODR-2026-10-18-multi-runtime-orchestration.md (Proposed)
---

# Orkestrasi Multi-Runtime CLI Headless di Galleon

> **Status: riset.** Rekomendasi di sini bukan keputusan. Keputusan hanya final bila Owner meratifikasi ODR (draf: `standard-docs/decisions/owner-decisions/ODR-2026-10-18-multi-runtime-orchestration.md`, status `Proposed`).
>
> **Cara membaca bukti.**
> - **[V]** dibaca atau dijalankan langsung oleh penulis pada 2026-10-18 (UTC).
> - **[A]** dilaporkan oleh sub-agen riset yang mengambil sumbernya; penulis **tidak** membaca ulang sumbernya.
> - **[S]** sumber sekunder (media, komunitas, forum).
> - **[I]** inferensi atau penilaian penulis.
> - **[?]** tidak dapat diverifikasi.
>
> Ini pembacaan teks publik, **bukan nasihat hukum**. Ketentuan vendor berubah cepat; semua tanggal "fetched" adalah 2026-10-18.

---

## 1. Pertanyaan

Achmad meminta analisis konkret, internal dan eksternal, tentang memperluas lingkup **Galleon Fleet** (produk, belum rilis) agar menjadi orkestrator multi-runtime: tiap crew/agent dapat memakai runtime CLI headless berbeda (agy, Codex CLI, Claude Code, Qwen Code, model lokal, dst.), termasuk tantangannya dan legalitas tiap produk. Lalu: bila ada hambatan aturan vendor, apakah pendekatan "orkestrator menjalankan tugas dari board, skills, dan steering, dengan CLI headless yang tunduk pada aturan kita" menyelesaikannya.

Pembatasan: board, `agy-bridge`, dan `dev-ci` adalah **percobaan di luar produk**. Yang dibahas di sini adalah produk Galleon.

---

## 2. Ringkasan Temuan

1. **Fondasi internal lebih siap dari dugaan awal**, tetapi ada tiga celah nyata: tidak ada server MCP milik Galleon, tidak ada adapter runtime pada tingkat tugas, dan provenance penulis/tujuan bukan field wajib pada memori (§4).
2. **Ketentuan vendor membagi akses menjadi tiga jalur** (§5): API key (bersih), menjalankan binary resmi dengan login pengguna sendiri (umumnya dibolehkan dengan syarat), dan mengambil atau memproksi token (dilarang atau berisiko).
3. **Dua provider Galleon saat ini memakai jalur ketiga**: `openai_codex.rs` dan jalur setup-token Anthropic (§4.3). Ini temuan paling mendesak.
4. **Gagasan "orkestrator menyuntik aturan ke CLI headless" sah**, tetapi bukan pintu keluar dari aturan vendor: ia hanyalah jalur kedua yang memang dibolehkan. Batasan kuota "pemakaian individu wajar" tetap berlaku (§5.3).
5. **Prompt tidak dapat menegakkan kepatuhan.** Runtime vendor memakai tool internalnya sendiri sehingga `PolicyEngine` dan payment-lockout Galleon tidak mencakupnya. Penegakan nyata ada di kontrak tugas, gerbang independen, isolasi, dan log (§7).
6. **Tantangan teknis terberat**: izin per aksi tidak seragam (hanya sebagian CLI punya callback), resume sesi tertutup, hang tanpa TTY, format output berbeda, dan kredensial berbeda (§6).
7. **Risiko lingkup besar.** Bukti yang ada baru satu runtime eksekutor (agy) berjalan berurutan di luar produk. Belum ada bukti dua runtime eksekutor berbeda mengerjakan tugas yang sama (§8).

---

## 3. Yang Salah di Analisis Sebelumnya (log koreksi)

| # | Pernyataan sebelumnya | Setelah verifikasi |
|---|---|---|
| 1 | Chat: "`prompt.rs` memuat `AGENTS.md` ke prompt agen" | **Salah.** Di `prompt.rs` `AGENTS.md` hanya muncul di blok uji (baris 821, 860; `#[cfg(test)]` mulai baris 590). Pemuatan produksi ada di `personality.rs:10-19` (`PERSONALITY_FILES`: SOUL, IDENTITY, USER, AGENTS, TOOLS, HEARTBEAT, BOOTSTRAP, MEMORY) [V, E21]. |
| 2 | Chat: board dan `agy-bridge` adalah "yang sudah ada" untuk Galleon | **Salah bingkai.** Itu percobaan di luar produk. Untuk Galleon yang ada adalah provider CLI satu-giliran, bukan adapter tingkat tugas [V, E16]. |
| 3 | Sub-agen 4: Kiro punya callback izin terprogram lewat `--auth-method client` | **Ditolak.** Teks help: opsi itu menentukan siapa yang menjawab permintaan *access-token* engine v3, bukan izin per aksi [V, E23]. OQ izin L2 untuk Kiro tetap terbuka. |
| 4 | Sub-agen 1: forum Google bertanggal "2026-10 sampai 2026-11" | **Salah ketik.** Postingan staf yang kubaca bertanggal 7 Oktober 2026 [V, X3]. |
| 5 | ADR v1: "versi `agy` 1.4.0" | `agy --version` = **1.4.2** [V, E23]. Flag yang diverifikasi tidak berubah; `--help` tidak menyebut ACP (0 baris) [V]. |
| 6 | Analisis awal menyebut prinsip "tanpa multi-agent spawning generik" dan "empat prinsip lain" yang berbenturan | **Tidak ditemukan ulang** dengan pencarian pola di `standard-docs/`. Dicabut dari argumen. Yang tetap dirujuk hanya ODR-03, ODR-07, ODR-11, ODR-22, dan ADR 0001 [V]. |
| 7 | Chat: Anthropic tidak mengizinkan login langganan untuk program pihak ketiga | **Lebih bernuansa.** Teks resmi: tidak boleh menawarkan login claude.ai di aplikasi sendiri, merutekan permintaan lewat kredensial paket, atau mengumpulkan/menyimpan token; tetapi *tidak* melarang pengguna masuk ke binary Claude Code yang tidak dimodifikasi dengan langganannya sendiri, **termasuk bila platform menghostingnya** [V, X1]. |

---

## 4. Temuan Internal (kode Galleon)

### 4.1 Yang sudah ada

| Area | Fakta | Bukti |
|---|---|---|
| Binding provider per agen | `AliasedAgentConfig.model_provider: ModelProviderRef`; contoh config `[agents.default] model_provider = "grok_cli.default"` | [V] E19 |
| Provider CLI | `gemini_cli.rs` dan `kilocli.rs` menjalankan binary sebagai subprocess, satu proses per permintaan, timeout 120 detik, tanpa kontrol sampling. `grok_cli.rs` memakai ACP (`grok agent stdio`), prompt lewat stdin JSON-RPC, login cache CLI sebagai default | [V] E16 |
| Memori Go | `Document{ID, Content, Embedding, Metadata, Scope}` dengan filter cakupan; `MemoryProposal` berstatus pending/approved/rejected/reverted, bersifat versi dan dapat di-revert; ada uji isolasi cakupan | [V] E20 |
| Konteks | `AGENTS.md` dimuat sebagai file kepribadian dari root workspace; skills `SKILL.md` dengan frontmatter agentskills.io | [V] E21 |
| Sesi/ACP | `galleon-acp-bridge` dipertahankan (ODR-24, R-42); Galleon Client Protocol WS JSON-RPC di Go direncanakan (ODR-23, G-36; PR-51, PR-58) | [V] E22 |

### 4.2 Celah

| Celah | Fakta | Bukti |
|---|---|---|
| Server MCP milik Galleon | Pencarian pola implementasi server (`impl ServerHandler`, `serve(`, `"tools/list" =>`, `handle_tools_list`, `fn serve_stdio`) di seluruh repo: **kosong**. Semua referensi `McpServer*` adalah klien/konfigurasi. Keterbatasan: hanya pola yang dicoba | [V] E15 |
| Go ke MCP | Hanya 4 berkas Go non-test menyebut MCP; tidak ada registrasi tool `mcp:*` | [V] ADR E1 |
| Adapter tingkat tugas | Provider yang ada berskala satu giliran: Galleon tetap memegang loop agen, CLI hanya menjadi pengganti LLM | [V] E16; [I] |
| Provenance memori | `Document.Metadata` hanya `map[string]string` bebas; `MemoryProposal` tidak punya field `author`/`runtime`/`purpose` (hanya `Feedback.Author`) | [V] E20 |
| Konteks kanonik | Lokasi/format steering kanonik Galleon untuk dihasilkan ke tiap runtime belum ditetapkan. Ada desain di `archive/dev-task-2-standalone-docs/steering-end-user-design-spec.md` yang **belum kubaca** | [?] |
| Penerusan binding ke Go | Pencarian `ProviderID|ModelRef|provider_id` di `engine/src` hanya menemukan pemanggilan `ExecuteTurn(`; `ExecuteTurnRequest` memuat `model`. Cara binding dari config sampai ke Go **tidak ditelusuri** | [V] E19; [?] |

### 4.3 Dua provider yang memakai jalur berisiko

- **`openai_codex.rs`**: tidak menjalankan CLI Codex. Ia memanggil `https://chatgpt.com/backend-api/codex/responses` memakai token OAuth ChatGPT, dengan header `originator: pi` (bukan identitas Galleon; maksudnya belum diselidiki). Pemilihan jalur: "OAuth subscription auth → Codex responses protocol" di `factory.rs:1260` [V, E17].
- **Provider Anthropic**: menerima setup-token langganan (`sk-ant-oat01-…`) sebagai Bearer dengan header beta OAuth [V, E18]. Ini pola yang secara tertulis dilarang Anthropic bagi pengembang pihak ketiga (§5.1).
- **`gemini_cli.rs`** menjalankan binary resmi, sesuai pola yang dibolehkan staf Google (§5.2), tetapi untuk pengguna tier gratis dan Google One, Gemini CLI sudah digantikan Antigravity CLI sejak 18 Juni 2026 [V, X5]. Provider ini perlu dinilai ulang terhadap `agy`.
- **Tidak diperiksa:** apakah jalur-jalur ini aktif secara default dalam build rilis; legalitas `kilocli.rs` dan `grok_cli.rs`.

---

## 5. Temuan Eksternal: Ketentuan Vendor

### 5.1 Anthropic — Claude Code [V, X1; fetched 2026-10-18]

- Developer yang membangun produk di atas kapabilitas Claude, termasuk lewat Agent SDK, "*should use API key authentication*".
- "*Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, or Max plan credentials on behalf of their users.*" Pengembang "*may not collect, store, or intermediate Claude.ai credentials or session tokens*".
- Tidak dilarang: pengguna masuk ke "*the unmodified Claude Code binary with their own Claude subscription, including where a platform hosts Claude Code*".
- Mem-preinstall atau menjalankan Claude Code di produk memerlukan Commercial Terms; binary tidak boleh dimodifikasi; "*Customers may not pay for, resell, or intermediate Claude usage on their end users' behalf*"; nama dan logo hanya boleh disebut sebagai teks biasa.
- Batas Pro dan Max "*assume ordinary, individual usage of Claude Code and the Agent SDK*".
- Enforcement 2026: perubahan ketentuan Februari 2026 dilaporkan media [S, X8]; pemblokiran otomatis token langganan pada harness pihak ketiga dilaporkan sekitar April 2026 [S]; tanggal persisnya [?].
- Consumer Terms §3(7) melarang akses otomatis "*bot, script, or otherwise*" kecuali lewat API key [A, X7].

### 5.2 Google — Antigravity CLI (`agy`) dan Gemini CLI

- Gemini CLI: "*Directly accessing the services powering Gemini CLI … using third-party software, tools, or services (for example, using OpenClaw with Gemini CLI OAuth) is a violation of applicable terms and policies.*" Metode yang didukung: login akun Google, API key Gemini Developer API, API key Vertex AI [V, X2].
- Gemini CLI digantikan Antigravity CLI pada 18 Juni 2026 untuk pengguna tier gratis dan Google One [V, X5].
- **Staf Google (forum resmi, 7 Oktober 2026) [V, X3]**: menjalankan binary `agy` resmi yang tidak dimodifikasi secara lokal, headless, dengan langganan pribadi sendiri untuk pekerjaan individu, "*permitted*". Syarat: seluruh akses layanan hanya lewat binary resmi atau Python SDK resmi; "*No OAuth tokens, cookies, or credentials are extracted, read, or passed to the external tool*"; alur "*strictly for your own personal, single-user workflow and not shared, pooled, or exposed as a multi-user service*". Run headless memakai kuota yang sama dengan sesi interaktif; banyak proses paralel atau loop tanpa pengawasan frekuensi tinggi dapat menghabiskan kuota atau memicu perlindungan abuse; untuk pipeline kontinu bervolume tinggi disarankan API key AI Studio atau Gemini Enterprise. Ini **penjelasan staf, bukan teks ToS**.
- Antigravity Additional Terms §6 (melarang memakai alat pihak ketiga untuk mengakses layanan, contoh OpenClaw dengan OAuth Antigravity) [A, X6]; suspensi akun massal Februari 2026 [S].

### 5.3 OpenAI — Codex CLI

- Terms of Use (efektif 1 Januari 2026) [V, X4]: "*You may not share your account credentials or make your account available to anyone else*"; tidak boleh "*Automatically or programmatically extract data or Output*"; tidak boleh "*circumvent any rate limits or restrictions or bypass any protective measures or safety mitigations*"; tidak boleh "*Use Output to develop models that compete with OpenAI*". Penggunaan API diatur Business Terms (disebut di halaman yang sama). Teks **tidak menyebut harness atau CLI pihak ketiga** secara eksplisit.
- Codex CLI berlisensi Apache-2.0; `codex exec` berjalan dengan API key atau "Sign in with ChatGPT" [A, X9].
- Sikap 2026: OpenAI terlaporkan memperluas akses Codex ke paket berbayar, dan mendeteksi penyalahgunaan "sub2api" (pengemasan ulang langganan untuk lalu lintas API) [S, X9]. Tidak ada larangan harness tertulis yang kutemukan [?].

### 5.4 Lainnya (hanya laporan sub-agen [A])

| Runtime | Ringkasan | Sumber |
|---|---|---|
| Qwen Code | Apache-2.0 (fork Gemini CLI). Login OAuth gratis dihentikan 2026-04-15; sisa jalur: API key atau paket penyedia. Ketentuan Alibaba Model Studio **tidak terbaca** (halaman kosong) | X10 [A], [?] |
| Kiro CLI (AWS) | Dilisensikan sebagai "AWS Content" di bawah AWS Customer Agreement. Headless resmi lewat API key (paket berbayar tertentu); ada subcommand `acp`. Hak redistribusi biner tidak eksplisit | X11 [A] |
| GitHub Copilot CLI | Masih preview; Pre-release Terms membatasi pemakaian produksi, penyediaan sebagai penawaran mandiri, dan pengalihan ke pihak ketiga. Berubah saat GA | X12 [A] |
| Runtime lokal | Ollama, llama.cpp, LocalAI: MIT; vLLM: Apache-2.0. **LM Studio**: EULA proprietari, membatasi integrasi di luar antarmuka resmi dan distribusi/SaaS | X13 [A] |
| Bobot model | Llama 4: lisensi komunitas (ambang 700 juta MAU, atribusi, AUP). Gemma: syarat distribusi dan kebijakan larangan pemakaian diteruskan. Mistral, Qwen, DeepSeek, gpt-oss: bervariasi per model, sumber sekunder, **cek per checkpoint** | X13 [A/S] |
| Orkestrator yang hanya memanggil endpoint lokal dan tidak mengirim bobot | Hampir tanpa kewajiban lisensi model; kewajiban AUP/atribusi muncul bila produk mendistribusikan bobot atau menghostingnya untuk orang lain | X13 [A], [I] |

### 5.5 Matriks tiga jalur

| Jalur | Anthropic | Google | OpenAI | Catatan |
|---|---|---|---|---|
| **1. API key** | Jalur yang diwajibkan untuk produk [V] | Didukung [V] | Diizinkan [A] | Bersih secara legal; biaya per token |
| **2. Binary resmi tidak dimodifikasi, login pengguna sendiri, lokal** | Tidak dilarang tertulis [V]; "ordinary, individual usage" | Diizinkan menurut staf, bersyarat [V] | Abu-abu [V/I] | Syarat serupa di semua vendor: jangan sentuh token, satu pengguna, tanpa pooling |
| **3. Mengambil atau memproksi token, memanggil backend vendor** | Dilarang tertulis [V] | Pelanggaran [V] | Berisiko [V/I] | Pola `openai_codex.rs` dan setup-token Anthropic |
| Layanan hosted/bersama/pooling | Bersyarat: platform boleh menghosting binary bila pengguna masuk sendiri [V] | Dilarang menurut staf [V] | Dilarang (berbagi kredensial) [V] | Ambil yang terketat sebagai invarian |

### 5.6 Implikasi untuk gagasan "suntik aturan ke CLI headless"

Menyuntik board, skills, dan steering lewat file konteks adalah pemakaian normal semua CLI ini, dan itu jalur 2. Ia **tidak** menghapus batasan kuota ("individual usage", konkurensi, loop kontinu), dan untuk Claude pengembang produk tetap diarahkan ke API key. Bingkai "mengakali" tidak tepat: yang dibolehkan adalah memakai jalur yang memang dibuka; menyamarkan klien, memodifikasi binary, atau memutar/mem-pool akun adalah pelanggaran dan berisiko suspensi.

---

## 6. Temuan Eksternal: Teknis (antarmuka headless)

Semua sel adalah laporan sub-agen [A] kecuali bertanda [V].

| CLI | Non-interaktif dan output | Resume | Izin | Sandbox | ACP |
|---|---|---|---|---|---|
| Claude Code | `-p`; `json`/`stream-json` | `--resume`, `--continue` | **Callback terprogram** (`canUseTool`, `--permission-prompt-tool`) | ya | adapter `claude-agent-acp` v0.37.0 [S] |
| Codex CLI | `codex exec`; `--json` (JSONL); `--output-schema` | `exec resume` | flag saja (`--sandbox`, approval); tanpa callback | `workspace-write` default | adapter `codex-acp` (Zed) [S] |
| agy | `-p`; `json`/`stream-json`; input `stream-json` | `--continue`, `--conversation` | biner (`--mode`, `--sandbox`, `--dangerously-skip-permissions`); tanpa callback di `--help` [V] | `--sandbox` | **tidak ada** di `--help` [V] |
| Qwen Code | `-p`; `json`/`stream-json` | session id [S] | mode persetujuan | warisan Gemini [?] | kemungkinan `--experimental-acp` [?] |
| Kiro CLI | `chat --no-interactive`; `-f json` | `--resume`, `--resume-id` | `--trust-all-tools`, `--trust-tools <nama>` [V]; ACP `--auth-method` hanya soal token [V] | tidak ada di chat | subcommand `acp` [V] |
| Copilot CLI | `-p`, `--output-format json` | `--resume`, `--session-id` | `--allow-tool`/`--deny-tool` berfilter, `--no-ask-user` | sandbox lokal [S] | di registry ACP [S] |
| OpenCode | `run`, `serve` (HTTP + SDK) | `-c`, `-s`, `--fork` | izin per agen | tool-level | `opencode acp` |
| Model lokal | bukan agen; endpoint OpenAI-compatible | tanpa status | tanpa | tanpa | tanpa |

**Lima tantangan teknis, urut tingkat kesulitan** (peringkat dari sub-agen, dengan koreksi §3):

1. **Izin per aksi tidak seragam.** Callback terprogram hanya terbukti pada Claude Code (klaim sub-agen, belum diverifikasi langsung). Codex dan agy tidak punya callback; klaim untuk Kiro ditolak. Konsekuensi: banyak runtime hanya bisa dipagari oleh sandbox, bukan persetujuan per aksi.
2. **Resume sesi berbeda di tiap CLI** dan formatnya tertutup bagi host.
3. **Hang tanpa TTY** (prompt yang menunggu input) menuntut flag non-interaktif per adapter ditambah pembunuhan batas waktu.
4. **Format output tidak seragam**; adapter butuh parser sendiri dan ragam laporan penggunaan token.
5. **Refresh dan kebocoran kredensial berbeda** per CLI; satu kebijakan suntikan kredensial tidak cukup.

Penambahan dari analisis internal [I]: **tool internal CLI vendor melewati kebijakan Galleon** (PolicyEngine mengembalikan `REQUIRE_APPROVAL` untuk tier tulis dan eksekusi hanya untuk tool Galleon, `engine/src/tool/policy.go:52`), jadi penegakan atas runtime eksternal bergantung pada isolasi dan, bila ada, callback izin L2.

---

## 7. Analisis Opsi Perluasan Lingkup

| Tingkat | Bentuk | Legal | Teknis | Putusan usulan |
|---|---|---|---|---|
| 1 | API key per agen + model lokal lewat endpoint OpenAI-compatible | Bersih | Sebagian besar sudah ada | Dalam lingkup |
| 2 | CLI sebagai provider satu giliran (yang ada) | Jalur 2; tergantung vendor | Tool internal CLI bisa melewati kebijakan Galleon; apakah provider yang ada membatasi tool bawaan CLI **tidak diperiksa** | Dalam lingkup, dengan syarat |
| 3 | CLI sebagai agen otonom penuh (adapter tingkat tugas) | Jalur 2 dengan invarian | Adapter, MCP, onboarding, isolasi, memori | Dalam lingkup setelah gerbang bukti |
| 4 | Mengambil atau memproksi token vendor | Dilarang atau berisiko | — | Default nonaktif; perlu keputusan Owner |

**Kepatuhan di luar prompt.** Karena aturan yang disuntik hanyalah saran, kepatuhan ditegakkan oleh: (1) kontrak tugas dengan kriteria penerimaan dan laporan berbukti, (2) gerbang verifikasi independen, (3) isolasi fail-closed, (4) log event. Server MCP Galleon menegakkan state machine tugas di sisi server sehingga tugas tidak dapat ditutup tanpa laporan berbukti.

**Onboarding runtime baru.** Galleon menghasilkan berkas konteks runtime secara deterministik dari satu sumber; agen menjalani uji kepatuhan (konteks termuat, MCP terjangkau, batas dihormati, laporan sesuai skema, event terminal, tidak ada kredensial bocor); agen boleh mengusulkan, bukan menulis, aturan kanonik. Pola ini sejalan dengan *learning by consent* yang sudah ada di memori Go.

**Memori bersama.** Mengandalkan agen vendor untuk "ingat menulis" tidak dapat dipaksa. Pola yang bekerja: Galleon menyuntik konteks relevan ke tugas, dan penutupan tugas mensyaratkan laporan lewat MCP; identitas penulis diambil dari token sesi.

---

## 8. Tantangan Perluasan Lingkup (ringkas, urut dampak)

1. **Lingkup.** Galleon belum rilis dan baseline CI `testing` masih merah di beberapa gerbang. Ini hampir produk kedua di atas empat tier. Mitigasi: gerbang bukti dua runtime sebelum implementasi penuh.
2. **ODR dan ADR yang tersentuh.** ODR-03, ODR-07, ODR-11, ODR-22, ADR 0001; sah hanya lewat ODR baru. Penempatan yang selaras: Go memutuskan, Rust men-spawn dan mengurung.
3. **Legal.** Invarian vendor (MR-09) dan tinjauan dua provider bermasalah sebelum rilis. Tinjau ulang tiap rilis karena ketentuan berubah cepat.
4. **Isolasi di host pengembangan.** `bwrap` terpasang tetapi `unshare -Ur` ditolak (EPERM) dan `apparmor_restrict_unprivileged_userns=1`; Landlock ada di daftar LSM (kernel 7.0.0-38) tetapi belum diuji [V, ADR E9].
5. **Konteks per runtime.** Tiap CLI membaca berkas berbeda (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.kiro/steering`); hanya pemuatan `AGENTS.md`/`SKILL.md` oleh agy yang pernah diuji (riset induk), runtime lain **belum**.
6. **Kebijakan tidak mencakup tool internal vendor** (§6), termasuk tool pembayaran: runtime eksternal tidak boleh ditugaskan pekerjaan commerce.
7. **Server MCP di Go atau Rust** perlu diperiksa terhadap `01-boundary-policy.md` (belum kubaca penuh), dan terhadap Q-2 di arsip dev-tasks yang menghapus klien MCP dari Go dan mengarahkan MCP ke Rust (centang rekomendasi, bukan ODR) [V, ADR E25].

---

## 9. Rekomendasi

Dituangkan di draf ODR `ODR-2026-10-18-multi-runtime-orchestration.md` (MR-01…MR-10) dan ADR revisi 2: Galleon sebagai orkestrator multi-runtime dengan Go memutuskan dan Rust men-spawn; adapter L0/L1/L2 berbasis uji kepatuhan; satu server MCP Galleon; memori bersama dengan provenance dan consent; konteks dihasilkan deterministik; invarian legal; dan gerbang bukti dua runtime. Semuanya **usulan** sampai Owner meratifikasi.

---

## 10. Yang Tidak Terverifikasi

- **Belum terverifikasi** dan butir tindak lanjut Owner: lihat `multi-runtime-owner-verification-checklist-2026-10-18.md` (V-02…V-28, K-01, K-03…K-09). Komponen yang belum dibangun: `multi-runtime-unbuilt-components-inventory-2026-10-18.md`.
- Ketentuan Alibaba Model Studio; Kiro/AWS secara penuh; Copilot setelah GA; lisensi bobot model per checkpoint.
- Isi Antigravity Additional Terms §6 dan Consumer Terms §3(7) (hanya lewat sub-agen).
- Tanggal dan skala enforcement 2026 (media dan komunitas).
- Apakah menyalin direktori kredensial pengguna ke dalam kontainer sesi dianggap "mengekstrak token".
- Perilaku izin `stream-json` agy; perilaku adapter L1/L2 apa pun; kemampuan Landlock di host.
- Apakah provider `openai_codex` dan setup-token Anthropic aktif default; legalitas `kilocli`/`grok_cli`.
- Cara binding `model_provider` dari config sampai ke Go; lokasi dan format steering kanonik Galleon.

---

## 11. Sumber

| ID | Sumber | URL | Dibaca |
|---|---|---|---|
| X1 | Anthropic, Claude Code Legal and compliance | https://code.claude.com/docs/en/legal-and-compliance | [V] (8.000 karakter pertama memuat seluruh bagian relevan) |
| X2 | Gemini CLI: License, Terms of Service, Privacy | https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/tos-privacy.md | [V] |
| X3 | Forum Google AI Developers, staf, 7 Okt 2026 | https://discuss.ai.google.dev/t/can-a-local-ai-coordinator-launch-the-official-antigravity-cli-with-subscription-sign-in/186246/2 | [V] |
| X4 | OpenAI Terms of Use (efektif 1 Jan 2026) | https://openai.com/policies/terms-of-use/ | [V] (8.000 karakter pertama) |
| X5 | Gemini CLI headless mode (banner penggantian) | https://geminicli.com/docs/cli/headless/ | [V] |
| X6 | Google Antigravity Additional Terms | https://antigravity.google/terms | [A] |
| X7 | Anthropic Consumer Terms | https://www.anthropic.com/legal/consumer-terms | [A] |
| X8 | The Register, 2026-02-20 | https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/ | [S][A] |
| X9 | OpenAI Codex auth dan noninteractive; MindStudio; KuCoin | https://developers.openai.com/codex/auth/ ; https://developers.openai.com/codex/noninteractive | [A][S] |
| X10 | Qwen Code auth docs | https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/ | [A] |
| X11 | Kiro license dan headless docs | https://kiro.dev/license/ ; https://kiro.dev/docs/cli/headless/ ; https://kiro.dev/docs/cli/acp/ | [A] |
| X12 | GitHub Copilot Pre-release License Terms | https://docs.github.com/en/site-policy/github-terms/github-copilot-pre-release-license-terms | [A] |
| X13 | LM Studio terms; Llama 4 license; Gemma terms | https://lmstudio.ai/terms ; https://www.llama.com/llama4/license/ ; https://ai.google.dev/gemma/terms | [A] |
| X14 | Adapter ACP: claude-agent-acp, codex-acp | https://github.com/zed-industries/claude-code-acp ; https://zed.dev/blog/codex-is-live-in-zed | [A][S] |

Bukti internal diberi ID E15–E25 pada ADR `adr-control-plane-interface-2026-10-18.md` §10-B (E1–E14 dari revisi 1 dipertahankan).
