---
title: Catatan Verifikasi dan Keputusan untuk Owner — Orkestrasi Multi-Runtime (Tindak Lanjut)
status: research
date: 2026-10-18
author: kirocrew (default), diskusi dengan Achmad
depends_on: multi-runtime-orchestration-feasibility-2026-10-18.md; adr-control-plane-interface-2026-10-18.md (revisi 2); multi-runtime-unbuilt-components-inventory-2026-10-18.md
informs: standard-docs/decisions/owner-decisions/ODR-2026-10-18-multi-runtime-orchestration.md (Proposed)
---

# Catatan Verifikasi dan Keputusan untuk Owner

> **Tujuan.** Menyimpan hal-hal yang **perlu Owner verifikasi atau putuskan** sebelum atau sesudah ODR multi-runtime diratifikasi, agar dapat ditindaklanjuti kelak. Ini daftar kerja, bukan keputusan.
>
> **Cara memakai.** Tiap butir punya ID tetap (`V-xx` untuk verifikasi, `K-xx` untuk keputusan). Ubah kolom *Status* menjadi `selesai` dengan tanggal dan bukti saat dikerjakan; jangan menghapus butir. Prosedur bertanda **(prosedur, belum dijalankan)** adalah rancangan langkah, bukan hasil.
>
> **Tag.** **[V]** diverifikasi langsung oleh penulis; **[A]** hanya dilaporkan sub-agen; **[S]** sekunder; **[I]** inferensi; **[?]** tidak terverifikasi. Ketentuan vendor adalah pembacaan teks publik, **bukan nasihat hukum**.

---

## 1. Prioritas Tinggi — risiko akun dan rilis

| ID | Apa | Kenapa penting | Cara memverifikasi | Status |
|---|---|---|---|---|
| **V-02** | **Provider Galleon yang memakai jalur token**: `openai_codex.rs` (token OAuth ChatGPT ke `chatgpt.com/backend-api/codex/responses`, header `originator: pi`) dan jalur setup-token Anthropic (`sk-ant-oat01-…` sebagai Bearer) [V]. **Apakah keduanya aktif secara default untuk pengguna rilis: belum diperiksa** [?]. | Anthropic melarang pengembang pihak ketiga merutekan permintaan lewat kredensial paket dan mengumpulkan atau menyimpan token [V]. OpenAI melarang "programmatically extract" dan melewati "protective measures" [V]. Ini terjadi pada produk yang akan dirilis. | (1) `grep -rn "openai_codex\|OpenAiCodex" crates/clawcrew-providers/src/factory.rs crates/clawcrew-config/src/schema.rs` untuk melihat apakah ada konfigurasi/default yang memilihnya. (2) `grep -rn "setup-token\|setup_token" crates --include=*.rs -l` untuk menemukan perintah `auth setup-token`. (3) Telusuri alur onboarding/UI yang menawarkan "login dengan ChatGPT" atau menempel token. Hasil yang dicari: dapatkah pengguna biasa mengaktifkannya tanpa mengubah kode. | open |
| **V-03** | **Provider CLI satu-giliran** (`gemini_cli.rs`, `kilocli.rs`, `grok_cli.rs`): (a) argumen proses yang dijalankan; (b) apakah CLI vendor dibatasi agar tidak menjalankan tool internalnya sendiri; (c) legalitas Kilo CLI dan Grok Build (belum diteliti). | Bila CLI menjalankan tool-nya sendiri, `PolicyEngine` dan payment-lockout Galleon tidak berlaku atas aksinya [I]. `gemini_cli.rs` menarget Gemini CLI yang diganti Antigravity CLI sejak 18 Juni 2026 untuk tier gratis dan Google One [V]. | Baca `Command::new(...)` dan `.arg(...)` di ketiga berkas; cari flag mode persetujuan (`--yolo`, `--approval-mode`, `--trust-all-tools`). Untuk (c) baca ketentuan penggunaan Kilo dan xAI. | open |

---

## 2. Verifikasi Legal

| ID | Apa | Cara memverifikasi | Status |
|---|---|---|---|
| **V-04** | **Baca langsung teks primer yang hanya dilaporkan sub-agen [A]:** Antigravity Additional Terms §6 (https://antigravity.google/terms); Anthropic Consumer Terms §3(7) dan Commercial Terms; OpenAI Business Terms (penggunaan API); Alibaba Model Studio terms (halaman kosong saat diambil); AWS Customer Agreement dan Service Terms terkait Kiro (https://kiro.dev/license/); GitHub Copilot setelah GA. Catat kutipan ≤25 kata beserta tanggal baca. | Buka URL, simpan kutipan di dokumen bertanggal. | open |
| **V-05** | **Tanyakan ke vendor hal yang ambigu** dan simpan jawabannya (tautan atau surel): (a) Anthropic: apakah orkestrator lokal yang hanya menjalankan `claude -p` tanpa menyentuh token termasuk "intermediate"? (b) Google: apakah memasang direktori login `agy` secara hanya-baca ke sandbox, agar `agy` itu sendiri memakainya, dianggap "passed"? (c) OpenAI: sikap terhadap harness yang menjalankan `codex exec` dengan "Sign in with ChatGPT". | Kanal: Anthropic "contact sales" (disebut di halaman legal), forum Google AI Developers, dukungan OpenAI. | open |
| **V-06** | **Hubungan dengan tier dan lisensi Galleon**: apakah mengirim adapter yang menjalankan CLI vendor sesuai dengan tangga tier (Community/Team/Dockyard) dan provenance lisensi yang sudah diputuskan. | Baca `tier-pricing-and-entitlement-final.md` dan `license-provenance-attribution-research.md`; diskusikan dengan penasihat. | open |
| **V-07** | **Lisensi bobot model per checkpoint** (Qwen, Llama, Gemma, Mistral) bila Galleon merekomendasikan atau menyertakan model default. | Baca berkas LICENSE tiap checkpoint di Hugging Face/ModelScope. Klaim saat ini hanya dari sumber sekunder [S]. | open |
| **V-08** | **Tinjauan penasihat hukum sebelum rilis.** Semua ringkasan ketentuan vendor di dokumen ini adalah pembacaan penulis, bukan nasihat hukum. | Jadwalkan sebelum rilis; ulangi tiap rilis karena ketentuan berubah (Feb, Apr, Jun 2026). | open |

---

## 3. Verifikasi Teknis

| ID | Apa | Cara memverifikasi | Status |
|---|---|---|---|
| **V-09** | **Landlock berfungsi di host?** Kode dan uji integrasi sudah ada (`crates/clawcrew-runtime/tests/landlock_workspace_boundary.rs`, `landlock_network_config_access.rs`, `landlock_spawn_failure.rs`, `landlock_contract.rs`) [V keberadaan]. `bwrap` terpasang tetapi `unshare -Ur` ditolak [V]; Landlock ada di daftar LSM [V]. | **(prosedur, belum dijalankan)** Jalankan keempat berkas uji itu dengan `cargo test -p clawcrew-runtime --test <nama>` di worktree terpisah; periksa apakah ada yang `ignored`/dilewati. Catat hasil per uji. | open |
| **V-10** | **Apakah `stream-json` agy memancarkan permintaan izin?** Menentukan apakah agy dapat naik ke L2. | **(prosedur, belum dijalankan)** Di direktori sementara hasil `git init`, jalankan `agy -p "<perintah yang menulis berkas>" --mode <mode non-bypass> --output-format stream-json`, amati apakah ada event permintaan izin atau proses berhenti menunggu. Jangan memakai `--dangerously-skip-permissions`. | open |
| **V-11** | **Apakah `kiro-cli acp` mengirim `session/request_permission`?** `--auth-method` hanya soal token [V]; klaim callback izin Kiro ditolak. | **(prosedur, belum dijalankan)** Klien ACP minimal (JSON-RPC lewat stdio) ke `kiro-cli acp`, minta aksi tulis, amati pesan. `acp/server.rs` Galleon menyebut `request_permission` sekali [V]; itu sisi server Galleon. | open |
| **V-12** | **Konfigurasi MCP per sesi** tanpa mengubah konfigurasi global pengguna, untuk tiap CLI. `agy mcp add` "menambah atau memperbarui konfigurasi server MCP" [V]; cakupan penyimpanannya tidak diperiksa. | Baca `agy mcp add --help` sampai habis dan telusuri lokasi berkas konfigurasi yang diubah; ulangi untuk `kiro-cli`, Claude Code, Codex. | open |
| **V-13** | **Berkas konteks yang dibaca tiap runtime** (`CLAUDE.md`, `GEMINI.md`, `.kiro/steering/*`, `AGENTS.md`, `.agents/skills`) dan prioritas bila bertentangan. Hanya `AGENTS.md` dan `.agents/skills` pada agy yang terbukti (n=1) [V]. | Ulangi uji kata sandi acak (probe) per runtime seperti pada riset induk (bukti I4). | open |
| **V-14** | **Bagaimana `model_provider` per agen sampai ke Go** (config → `ExecuteTurnRequest.model` → resolusi provider di Rust). Hanya `model` yang terlihat di proto [V]. | Telusuri dari `schema.rs:4084` ke pemanggil `ExecuteTurn` di `engine/src/{crew,fleet,orchestrator}/services.go` dan ke `grpc_system_gateway.rs`. | open |
| **V-15** | **Lokasi dan format steering kanonik Galleon** untuk dijadikan sumber proyeksi konteks. | Baca `archive/dev-task-2-standalone-docs/steering-end-user-design-spec.md` (belum dibaca) dan `.kiro/steering/galleon-product-fundamentals.md` bila ada. | open |
| **V-16** | **Penempatan server MCP**: baca `tech-standart/architecture/01-boundary-policy.md` sampai habis (belum dibaca penuh), konteks Q-2 (`archive/dev-tasks/08-carryover-from-finalize.md:40`), dan apakah ada jalur Rust → Go. | Baca dokumen; catat apakah server MCP di Go dilarang atau diizinkan. | open |
| **V-17** | **`TaskStatus` di `task/dto.go` dan hubungannya dengan `run.Task`** (dua definisi `Task`); mana yang dipakai `WorkerPool`. | Baca `engine/src/task/dto.go`, `run/dto.go`, dan pemanggil `NewWorkerPool`. | open |
| **V-18** | **R-60 (sandbox MCP stdio)** mungkin sudah terpenuhi oleh commit `f2af74175`; kriteria "akses di luar workspace ditolak OS-level" belum diverifikasi. | Jalankan uji batas workspace yang ada; periksa apakah tiket R-60 perlu dicentang atau dikoreksi. | open |
| **V-19** | **Klaim teknis sub-agen [A]** tentang CLI lain (Claude Code `canUseTool`, Codex `--output-schema`/`resume`, Copilot flag, OpenCode `serve`/`acp`, Qwen). | Untuk CLI yang terpasang jalankan `--help`; untuk lainnya baca dokumentasi resmi. Jangan memakai tabel teknis untuk keputusan desain sebelum diuji. | open |
| **V-20** | **Jalur provider kompatibel OpenAI sebagai jalur model lokal** (Ollama/llama.cpp/vLLM) tanpa perubahan kode. | Konfigurasikan alias provider ke `http://127.0.0.1:11434/v1` dan jalankan satu giliran. | open |

---

## 4. Proses dan Penomoran

| ID | Apa | Cara memverifikasi | Status |
|---|---|---|---|
| **V-21** | **Reservasi ODR-26**: `archive/product-research-superseded/tier-enforcement-method-d-c-deep-dive.md:141` mengusulkan berkas `ODR-2026-10-05-community-tier-and-license-provenance.md` dengan "ID mulai ODR-26" (belum ada berkasnya). Draf ODR ini memakai label sementara `MR-01`…`MR-10`. | Putuskan urutan ratifikasi dan penomoran; periksa `ls standard-docs/decisions/owner-decisions` sebelum memberi nomor. | open |
| **V-22** | **Gate dokumen tidak mencakup `standard-docs/`**: `docs_quality_gate.sh` dan `docs_links_gate.sh` hanya memeriksa `docs/book/src/*.md` [V]. Dokumen ODR/riset hanya diperiksa manual. | Putuskan apakah perlu gerbang lint/tautan untuk `standard-docs/`. | open |
| **V-23** | **Baseline CI `testing`**: gerbang Lint, Check, dan Security merah di `testing` dan dikecualikan baseline ratchet; Repository Structure butuh submodule `docs/book/po` dipulihkan atau dihapus; Test perlu dijalankan penuh setelah prefetch firmware diperbaiki (catatan dari pekerjaan CI sebelumnya). | Jalankan ulang gerbang di `~/Apps/dev-ci`; putuskan perbaikan baseline sebelum menyalakan auto-merge. | open |
| **V-24** | **Cabang dokumen belum di-push**: `docs/odr-draft-multi-runtime` (commit lokal; lihat riwayat cabang). | Tinjau diff terhadap `origin/testing`, lalu push dan buka PR sesuai `AGENTS.md`. | open |

---

## 5. Sisa dari Pekerjaan Sebelumnya (di luar topik multi-runtime)

Dicatat dari sesi CI lokal; **status penyelesaiannya tidak kuketahui**, jadi tiap butir perlu dicek.

| ID | Apa | Perintah/tindakan | Status |
|---|---|---|---|
| **V-25** | Badan PR #55 dan #56 belum diperbarui di GitHub (diblokir policy host pada sesi itu). | Jalankan `gh pr edit 55 --body-file ~/Apps/dev-ci/state/pr-bodies/pr55.md` dan `gh pr edit 56 --body-file ~/Apps/dev-ci/state/pr-bodies/pr56.md` dengan judul yang diberikan sebelumnya. | open |
| **V-26** | Kata sandi 1Panel masih default (diberitahukan, tidak dikonfirmasi diubah). | `sudo 1pctl update password` | open |
| **V-27** | Aturan `ufw` yang dibuka 1Panel: 80/tcp, 443/tcp, 443/udp ke Anywhere (diberitahukan hapus, tidak dikonfirmasi). | `sudo ufw status numbered`, lalu hapus aturan yang tidak diperlukan. | open |
| **V-28** | Rahasia repo `KIRO_WEBHOOK_URL`, `KIRO_WEBHOOK_TOKEN`, `DISCORD_WEBHOOK_URL` belum dicabut. | Cabut/rotasi di pengaturan repositori GitHub. | open |

---

## 6. Keputusan yang Menunggu Owner

| ID | Keputusan | Pilihan / catatan | Terkait |
|---|---|---|---|
| **K-01** | Ratifikasi, ubah, atau tolak draf ODR (MR-01…MR-10). | Tinjau butir demi butir; hanya ODR `Ratified` yang final. | ODR draf |
| **K-03** | Disposisi `openai_codex.rs` dan setup-token Anthropic (V-02). | Nonaktifkan default, hapus, atau aktifkan eksplisit dengan peringatan. | MR-09(g) |
| **K-04** | Kebijakan kredensial default. | Langganan untuk interaktif/volume rendah, API key untuk loop otomatis (usulan) — murah vs risiko akun. | MR-09 |
| **K-05** | Lokasi server MCP. | Go, atau front tipis di Rust; ada preseden Q-2. | V-16 |
| **K-06** | Primitif kurungan proses. | Landlock (kode ada, belum diuji di host) atau Docker (terbukti di `dev-ci`). | V-09 |
| **K-07** | Runtime v1 untuk spike. | Usulan agy dan Kiro; Claude Code, Codex, Qwen menyusul setelah tinjauan legal. | MR-10 |
| **K-08** | Kapan membuat Story/Backlog dan tiket roadmap. | Setelah ratifikasi (aturan board dan ODR). | inventaris §6 |
| **K-09** | Push cabang dokumen dan buka PR. | Setelah tinjauan ODR (V-24). | V-24 |

---

## 7. Ringkasan Cakupan Dokumen Ini

Verifikasi: 27 butir (V-02…V-28). Keputusan: 8 butir (K-01, K-03…K-09). Butir V-02 dan V-03 serta K-03 berpotensi memengaruhi rilis dan sebaiknya ditinjau lebih dulu.
