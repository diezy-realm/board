---
title: Desain Refactor board/ + dev-ci/ ke Go — Pola Terinspirasi Symphony, Orchestrator Multi-Runtime Universal
status: research
date: 2026-10-18
author: kirocrew (lead-squad), diskusi dengan Achmad
depends_on: control-plane-multi-runtime-landscape-2026-10-18.md; multi-runtime-orchestration-feasibility-2026-10-18.md; multi-runtime-unbuilt-components-inventory-2026-10-18.md
informs: galleon-fleet (riset internal, BUKAN ODR — keputusan produk hanya sah lewat ODR galleon-fleet/standard-docs/decisions/owner-decisions/)
---

# Desain Refactor board/ + dev-ci/ — Go, Terinspirasi Symphony, Orchestrator Multi-Runtime

> **Status: riset/desain draft.** Dokumen ini adalah hasil diskusi arsitektur, bukan keputusan final.
> Ini riset INTERNAL tentang sistem KiroCrew+agy+dev-ci sendiri — BUKAN dokumen produk galleon-fleet.
> Keputusan Owner (2026-10-18): refactor total `board/`+`dev-ci/` dari MVP Python ke Go untuk
> kebutuhan jangka panjang/production-grade. Python hanya dipakai bila genuinely tidak bisa
> dikerjakan di Go.
>
> **Posisi Symphony (OpenAI, dibaca penuh dari SPEC.md 2312 baris + blog post resmi, 2026-10-18):**
> HANYA referensi metodologi (tracker-as-control-plane, workspace isolation, satu orchestrator
> state authoritative). BUKAN blueprint untuk disalin. Gap kunci: Symphony dirancang untuk SATU
> jenis agent (Codex app-server, protokol JSON-RPC seragam, satu tracker Linear). Galleon butuh
> adapter UNIVERSAL lintas CLI headless (agy, codex cli, claude cli, qwen cli, ollama/local, dst)
> yang masing-masing punya state/format output/mekanisme izin BERBEDA, semua dipaksa menulis balik
> ke format board yang SERAGAM — bukan menulis ke tracker eksternal seperti Linear.

---

## 1. Mengapa Refactor (Ringkasan Temuan Audit)

Hasil audit bug nyata (dieksekusi, bukan asumsi) pada `board/` saat ini:

| # | Severity | Temuan | File:baris |
|---|---|---|---|
| 1 | CRITICAL | Race condition `_next_report_id()` — scan ulang SEMUA `RPT-*.md` tiap panggilan, 2 proses overlap bisa dapat ID sama | `board_agy_bridge.py` fungsi `_next_report_id` |
| 2 | HIGH | `_ref_exists()` pakai `rglob(f"{value}*{ext}")` — glob prefix match salah (cocok `RPT-001` DAN `RPT-0010`) | `validate.py:57-62` |
| 3 | HIGH | Field `notes`/`carried_from`/`report` tidak divalidasi sama sekali | `validate.py` (STAGES req list) |
| 4 | HIGH | Isolasi agy: `--dangerously-skip-permissions` + `cwd=BOARD` + `--add-dir GALLEON` — bukan workspace terisolasi, agy punya akses tulis penuh ke checkout produksi | `board_agy_bridge.py:201-213` (dikonfirmasi ulang [V] hari ini, konsisten dgn riset tgl 18) |
| 5 | MEDIUM | Orchestrator **terpecah 2 proses tak-atomik**: `board_agy_bridge.py` (dispatch) dan `board_switch.py` (unblock/review) jalan sebagai timer systemd TERPISAH, saling baca/tulis file JSON yang sama tanpa lock terpusat | arsitektur, bukan 1 file |
| 6 | MEDIUM | State task bisa stuck di `in-progress` tanpa recovery/timeout bila proses crash di tengah | `board_agy_bridge.py` (claim sebelum run, tidak ada heartbeat) |
| 7 | LOW | Parsing front-matter YAML naif (regex split `:` pertama) — rawan rusak kalau value punya karakter `:` | `validate.py:parse_frontmatter` |

**Kesimpulan:** ini bukan bug kosmetik yang bisa ditambal satu-satu. Akar masalahnya ARSITEKTURAL — tidak ada SATU otoritas state (Symphony Section 7: "The orchestrator is the only component that mutates scheduling state"). `board/` sekarang punya 2+ penulis state independen tanpa koordinasi. Tambal bug #1 saja (flock di counter) tidak memperbaiki #4/#5/#6 yang levelnya desain.

## 2. Pola Symphony yang Diadopsi (dengan Gap Eksplisit)

### 2.1 Yang Diadopsi Langsung (cocok 1:1)

| Pola Symphony | Alasan cocok untuk kita |
|---|---|
| **Satu Orchestrator = satu otoritas state** (Section 7) | Langsung memperbaiki bug #1/#5/#6 — state task HANYA diubah oleh satu proses/goroutine, bukan 2 script Python independen |
| **Workspace per-task, isolasi fail-closed** (Section 9.5, 3 invariant) | Langsung memperbaiki bug #4 — agy (dan runtime lain) wajib `cwd == workspace_path`, workspace **MUST** di dalam `workspace_root`, nama disanitasi |
| **Reconciliation SEBELUM dispatch tiap tick** (Section 8.1) | Mengganti 2 timer independen (`board_switch.py` unblock+review, `board_agy_bridge.py` dispatch) jadi 1 tick loop yang urut: reconcile dulu, baru dispatch |
| **Retry dengan backoff eksponensial dari config** (Section 8.4: `min(10000*2^(attempt-1), max_backoff)`) | Board sekarang sudah ada retry (`MAX_AUTO_RETRY=3`, `RETRY_BACKOFF_MIN=[10,30,90]`) tapi hardcoded — selaraskan ke formula + config dinamis |
| **Config contract dalam-repo, hot-reload** (`WORKFLOW.md` front-matter) | Board sekarang: `RULES.md` prosa tidak machine-readable. Ganti dengan 1 file config YAML yang dibaca SEMUA proses (orchestrator, validator) |
| **Dua operasi read minimal untuk tracker adapter** (`fetch_issues_by_states`, `fetch_issues_by_ids`) | Board adapter (baca `tasks/*.json`) jadi sekecil ini — cegah scope creep "generic CRUD" yang Symphony eksplisit larang (Section 11, "Do not add generic comment/state/attachment CRUD") |

### 2.2 Gap — Yang TIDAK Bisa Disalin Langsung

| Aspek Symphony | Realita Galleon/board | Implikasi desain |
|---|---|---|
| **1 jenis agent** (Codex app-server, protokol JSON-RPC seragam, `thread/start`+`turn/start` terstandar) | **N jenis CLI headless** (agy, codex cli, claude cli, qwen cli, ollama/local), masing-masing beda protokol, format output, mekanisme izin — dikonfirmasi [V] riset tgl 18 §6 (tabel matrix: agy tanpa callback izin, Claude Code punya `canUseTool`, Kiro beda lagi) | **Butuh layer adapter tambahan** yang Symphony tidak punya — `Runtime` interface dengan `Capabilities()` eksplisit per vendor, bukan asumsi protokol seragam |
| **1 tracker eksternal** (Linear, ditulis balik oleh agent via tool native tracker) | **Board internal milik kita** — bukan SaaS eksternal, format front-matter sudah kita desain sendiri (Story/Backlog/PRD/Spec/Task/Report) | Tidak perlu "Issue Tracker Adapter" multi-provider seperti Symphony (yang antisipasi Jira/GitHub/dst) — cukup SATU adapter baca/tulis file board, tapi **validasi ketat** harus pindah dari Python script terpisah ke bagian dari Orchestrator itu sendiri (hindari drift validator vs penulis) |
| **Approval policy implementation-defined per Codex** (`approval_policy`, `thread_sandbox` pass-through ke Codex) | Tidak semua CLI punya setara — agy tidak punya callback izin terprogram, hanya flag biner (`--dangerously-skip-permissions` vs mode normal) | Policy TIDAK bisa seragam per-aksi; harus jatuh ke **isolasi workspace sebagai jaring pengaman utama** (bukan bergantung pada vendor izin granular yang tidak semua CLI punya) |
| **Agent menulis state tracker langsung via tool native** (Symphony tidak perlu tracker-write API) | Agent kita (agy, dst) TIDAK semuanya punya tool native untuk nulis file board dengan validasi skema | **Orchestrator-lah yang menulis board** (bukan agent langsung) berdasarkan `RuntimeEvent` ternormalisasi — lebih dekat ke pola lama kita (bridge yang verifikasi `_verify_agy_delivered`) daripada Symphony murni |

## 3. Arsitektur yang Diusulkan (Go)

### 3.1 Komponen (dipetakan dari Symphony Section 3.1, disesuaikan)

```
┌─────────────────────────────────────────────────────────────┐
│                     board-orchestrator (Go, 1 binary)         │
│  ┌───────────┐  ┌────────────┐  ┌──────────────┐             │
│  │  Config    │  │ Board       │  │  Workspace    │             │
│  │  Loader    │  │ Adapter     │  │  Manager      │             │
│  │ (board.yml)│  │ (read/write │  │ (git worktree │             │
│  │ hot-reload │  │  task JSON) │  │  per task)    │             │
│  └───────────┘  └────────────┘  └──────────────┘             │
│         │              │                 │                     │
│         └──────────────┼─────────────────┘                     │
│                    ┌────▼─────┐                                │
│                    │Orchestrator│  <- SATU-SATUNYA otoritas state │
│                    │(tick loop) │     (goroutine + channel,       │
│                    └────┬─────┘      bukan 2 proses independen) │
│                         │                                       │
│              ┌──────────┼──────────┐                           │
│              ▼          ▼          ▼                           │
│         ┌────────┐ ┌────────┐ ┌────────┐                       │
│         │Runtime │ │Runtime │ │Runtime │  <- interface, N impl  │
│         │ agy    │ │ codex  │ │ claude │     (§4)               │
│         └────────┘ └────────┘ └────────┘                       │
│                         │                                       │
│                    ┌────▼─────┐                                │
│                    │  CI Gate  │  <- panggil dev-ci (Go juga,   │
│                    │  Adapter  │     lihat §5)                  │
│                    └──────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 State Machine (diselaraskan dari Symphony Section 7.1, bukan disalin verbatim)

Status klaim orchestrator (BUKAN status tampilan board — ini internal, mencegah dispatch ganda):

```
Unclaimed → Claimed → Running → {Succeeded | Failed | Stalled} → RetryQueued atau Released
```

Status board (yang terlihat user, SUDAH ADA, dipertahankan — jangan ubah vocab yang sudah dipakai):
`todo → in-progress → blocked → review → done`

Pemetaan: `Claimed+Running` orchestrator → board `in-progress`; `Succeeded` + PR terbuka → board `review`; `Failed` berulang kali → board `blocked`. Ini sudah persis logika `board_agy_bridge.py`+`board_switch.py` SEKARANG — bedanya di refactor, SATU goroutine orchestrator yang memutuskan transisi ini, bukan 2 script yang race.

### 3.3 Reconciliation Tick (langsung dari Symphony Section 8.1, cocok 1:1)

```go
func (o *Orchestrator) Tick(ctx context.Context) {
    o.reconcileRunning(ctx)      // 1. stall detection + runtime state refresh (dulu: board_switch.py review/unblock)
    if err := o.validateConfig(); err != nil {
        o.logValidationError(err) // 2. skip dispatch tick ini, reconcile tetap jalan
        return
    }
    tasks := o.boardAdapter.FetchCandidates(ctx)        // 3. baca tasks/*.json status=todo
    for _, t := range sortByPriority(tasks) {
        if !o.hasAvailableSlot() { break }               // 4. concurrency limit dari config
        o.dispatch(ctx, t)                               // 5. workspace + runtime launch
    }
    o.notifyObservers()                                  // 6. log/status surface
}
```

## 4. Runtime Adapter — Interface Universal Lintas CLI Headless

Ini bagian yang **tidak ada** di Symphony (Symphony cuma 1 agent) dan **inti permintaan Anda**: galleon harus bisa orkestrasi agy/codex/claude/qwen/ollama apapun formatnya.

```go
// Satu-satunya kontrak yang Orchestrator kenal. Orchestrator TIDAK PERNAH
// tahu flag/protokol spesifik vendor — itu tanggung jawab tiap implementasi.
type Runtime interface {
    Launch(ctx context.Context, task Task, ws Workspace) (RunHandle, error)
    Stream(handle RunHandle) (<-chan RuntimeEvent, error)
    Capabilities() RuntimeCapabilities
}

type RuntimeCapabilities struct {
    SupportsResume        bool // agy: --conversation; ollama: tidak ada
    SupportsPermissionCB  bool // Claude Code: canUseTool; agy/Codex/Kiro: tidak [V, riset tgl18 §6]
    SupportsStreamingJSON bool
    MaxTurnsPerSession    int
}

// Event ternormalisasi — SATU bentuk, apapun sumber vendornya (JSON-RPC,
// line-delimited JSON, atau plain stdout yang di-parse heuristik).
type RuntimeEvent struct {
    Kind      string          // "turn_started"|"turn_completed"|"turn_failed"|"progress"|"needs_input"
    Timestamp time.Time
    Raw       json.RawMessage // payload asli vendor, disimpan utuh untuk debug
}
```

**Prinsip governance (menjawab permintaan "ikut rules dan shared memory, update progress di board"):**
1. Orchestrator menulis state board HANYA dari `RuntimeEvent` ternormalisasi — tidak pernah dari asumsi format vendor mentah.
2. Report akhir (`RPT-*.md`) tetap WAJIB lolos skema validasi board yang SAMA, apapun runtime yang mengerjakan — validasi jadi bagian Orchestrator (fungsi Go, bukan script Python terpisah yang bisa drift dari penulis).
3. Kapabilitas yang tidak seragam (izin per-aksi) TIDAK dipaksa seragam — fallback aman universal adalah **isolasi workspace** (git worktree + path containment, Symphony Invariant 1-3), karena itu satu-satunya kontrol yang berlaku untuk SEMUA runtime tanpa kecuali, baik yang punya callback izin maupun yang tidak.

### 4.1 Implementasi Pertama (realistis, bukan utopis)

| Runtime | Mekanisme Launch | Mekanisme Stream | Status |
|---|---|---|---|
| `agy` | `exec.Command` dengan `--output-format stream-json`, `cwd=workspace` (BUKAN board), tanpa `--dangerously-skip-permissions` global — scope ke `--add-dir workspace` saja | Parse line-delimited JSON dari stdout | Prioritas 1 — sudah dipakai |
| `codex` (CLI, bukan app-server penuh) | `exec.Command codex exec --json`, `cwd=workspace` | Parse JSONL | Prioritas 2 |
| `claude` (Claude Code) | `exec.Command claude -p --output-format stream-json` | Parse stream-json; **punya callback izin** (`canUseTool`) — manfaatkan kalau ada | Prioritas 3 (gap legal — lihat riset tgl 18 §5.1, jalur 2 OK selama tidak extract token) |
| `qwen` | Warisan Gemini CLI, serupa agy | Mirip agy | Belakangan |
| `ollama`/local | HTTP endpoint OpenAI-compatible, BUKAN subprocess CLI sama sekali | Streaming HTTP response, bukan event CLI | Beda kelas — adapter terpisah, bukan `exec.Command` |

## 5. dev-ci: Tetap Python atau Pindah Go?

Jawaban jujur dari riset Python-vs-Go sebelumnya (angka startup Python ~25ms vs Go ~0.4ms **tidak relevan** — bottleneck nyata adalah compile Rust 30-120s + docker 5-10s + git fetch 30-60s) **masih valid secara teknis**, TAPI keputusan Owner sekarang eksplisit: refactor total ke Go untuk alasan **jangka panjang/maintainability**, bukan murni kecepatan runtime. Dua alasan itu konsisten dipakai bersama:
- Performa: ganti bahasa TIDAK mempercepat CI (benar, tidak berubah).
- Maintainability jangka panjang: Go memberi **concurrency primitive native** (goroutine+channel) yang jauh lebih pas untuk orchestrator SATU-OTORITAS-STATE yang disebut di §3 — ini alasan Symphony sendiri pakai Elixir (bukan soal speed, soal primitif konkurensi/supervisi).

**Keputusan**: `dev-ci/bin/ci-poller` di-port ke Go SEBAGAI BAGIAN dari `board-orchestrator` yang sama (bukan proses terpisah lagi) — CI Gate Adapter dipanggil langsung dari Orchestrator tick, bukan `systemd-run` ke proses Python terpisah. Ini menghilangkan satu lagi sumber "2 proses tak terkoordinasi" (sekarang: bridge Python panggil `systemd-run` ke poller Python lain).

## 6. Yang BELUM Diputuskan (perlu input Anda sebelum coding dimulai)

1. **Workspace isolation mechanism**: git worktree (ringan, konsisten dgn `board/cron-wt/` yang sudah ada sebagai eksperimen tak terpakai) vs container Docker (lebih berat tapi isolasi lebih kuat, konsisten dgn `dev-ci` yang sudah pakai Docker). Riset tgl 18 menyarankan git worktree untuk agent runtime (ringan), Docker untuk CI gate (sudah ada). Usul: **keduanya**, beda layer.
2. **`board/cron-wt/`** — worktree terpisah yang saya temukan tidak dipakai bridge sama sekali. Apakah ini mau dijadikan basis Workspace Manager yang baru, atau dihapus karena basi?
3. **Lingkup migrasi**: refactor total sekaligus (big-bang) atau bertahap (orchestrator Go baru jalan paralel dulu, board lama tetap jalan sampai teruji)?
4. **`board-server` (artifact-server.py, Python juga)** — apakah ini termasuk scope refactor Go, atau tetap Python karena cuma render HTML read-only (risiko rendah)?

## 7. Referensi

- Symphony SPEC.md (OpenAI/GitHub), dibaca penuh 2312 baris, 2026-10-18: https://github.com/openai/symphony/blob/main/SPEC.md
- Symphony blog post resmi, dibaca penuh, 2026-10-18: https://openai.com/index/open-source-codex-orchestration-symphony/
- `control-plane-multi-runtime-landscape-2026-10-18.md` — kerangka lapisan L0-L3, tabel pemetaan Symphony→board komponen
- `multi-runtime-orchestration-feasibility-2026-10-18.md` — matrix kapabilitas CLI (§6), batasan vendor
- Audit bug board (sub-agent QA, 2026-10-18, dieksekusi bukan asumsi) — §1 dokumen ini
