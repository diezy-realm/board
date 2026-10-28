# Paket Migrasi Galleon Fleet: Go → Rust Bahasa Tunggal

Disusun 2026-10-29 oleh KiroCrew (peran: Senior Product Manager untuk dokumen produk, Senior Lead Engineer untuk dokumen teknis).

## Baseline fakta
| Repo | Branch | Commit |
|---|---|---|
| `diezy-realm/galleon-fleet` | `testing` | `3f3a7298cc0b22a145c5799befc0ee9e7c46b297` |
| `diezy-realm/board` | `master` lokal = `import-main` remote | `f4e2ddecd2cb9b4a872ac9b93f1db583ea0d60d7` (paket asli di-baseline ke `de99aff`, 19 commit lebih lama) |

Keduanya dicek sama dengan `origin` pada 2026-10-29. Bila sudah bergerak, jalankan ulang audit (TASK-051) sebelum Sprint 09 diaktifkan.

**Keterbatasan (jujur):** semua temuan berasal dari audit statis (membaca file, `rg`, `git log/show`). Tidak ada `cargo`, `go`, atau `npm` yang dijalankan karena toolchain tidak tersedia. Perintah verifikasi di setiap task belum pernah dijalankan oleh penyusun; agent pelaksana wajib menyalin output asli ke RPT. Validasi yang **sudah** dijalankan: `python3 validate.py <file>` untuk setiap artefak baru (semua ✓; `--all` tetap 10 error lama yang sudah ada sebelumnya), serta fungsi bridge `_is_sprint_active` (sprint baru = `False`) dan `_expected_branch` (semua task terbaca `feat/...`).

## Isi paket
```
board/                                   → salin ke root repo board
  RULES-amendment-2026-10-29.md          aturan baru (Rust-only, task ≤ 1 jam, status planning, bukti RPT)
  TEMPLATES-amendment-2026-10-29.md      template SPRINT.md, isi wajib task, bukti RPT, template ODR/ADR
  research/RES-…-baseline.md             fakta F-01..F-18 dengan file:line
  research/RES-…-rust-engineering-standards.md   OWASP 2025, API Top 10, ASVS 5.0, Sonar Rust, Clippy, idiom, modularitas
  research/RES-…-go-reference-inventory.txt
  product-backlog/stories/US-009.md
  product-backlog/prd/PRD-002.md          (in-review; menunggu approve Owner)
  product-backlog/backlog/BL-086..BL-092.md
  sprints/sprint-09..15/                 SPRINT.md (status: planning), specs/, tasks/, reports/
galleon-fleet/standard-docs/             → diterapkan ke repo galleon-fleet oleh TASK-052 (PR)
  decisions/owner-decisions/ODR-2026-10-29-rust-single-language.md   ODR-26..ODR-33
  decisions/0018-rust-single-language-architecture.md                ADR-0018
  decisions/SUPERSESSION-INDEX-2026-10-29.md                         dokumen lama yang diganti/diberi banner
  tech-standart/architecture/01-boundary-policy.md                   v2, 3-tier
  tech-standart/tech-stack/rust-conventions-amendment-2026-10-29.md
  templates/template-odr.md, templates/template-adr.md               Tier Go dihapus
```

## Peta sprint
| Sprint | Backlog / Spec | Task | Hasil |
|---|---|---|---|
| 09 | BL-086 / SPEC-011 | 049–057 | Keputusan & aturan masuk repo, steering agent bebas Go, terminal Go ditutup (bind loopback + Bearer fail-closed), guard `check_no_go.sh` |
| 10 | BL-087 / SPEC-012 | 058–065 | Inventaris konsumen API, layer keamanan + ConnectInfo, rute pairing/admin/webhook dipulihkan, `tests.rs` yatim aktif lagi, test tabel rute 401, fixture kontrak dari Go |
| 11 | BL-088 / SPEC-013 | 066–081 | Crate `galleon-fleet-core` + adapter `api_fleet` di gateway, nilai jujur (`null`, bukan konstanta), terminal lewat `SecurityPolicy` |
| 12 | BL-089 / SPEC-014 | 082–087 | Web satu pintu `request()` + pairing, Tauri satu command `api_request`, Nginx ke 42617, smoke E2E tanpa Go |
| 13 | BL-090 / SPEC-015 | 088–092 | Hapus `engine/`, proto, strangler, gRPC, tonic; CI Go dihapus; guard penuh |
| 14 | BL-091 / SPEC-016 | 093–101 | `[lints] workspace = true` di semua crate dengan ratchet, doctest, sccache kondisional, drift ClawCrew, Sonar kondisional |
| 15 | BL-092 / SPEC-017 | 102–105 | Pulihkan TLS/mTLS, peringatan public bind, `path_prefix`, tunnel; ekstraksi `crates/galleon-tunnel` |

Total 57 task (55 paket asli + 2 hotfix build TASK-049/050). TASK-051 (audit) `done` dengan RPT-108; TASK-057 untuk KiroCrew; sisanya `agy`, masing-masing ≤ 1 jam, satu branch `feat/...`, satu PR ke `testing`.

## Renumber ke board live (2026-10-29)
Paket asli memakai ID yang sudah terpakai di board (TASK-043..048, BL-084/085, US-004, SPEC-010, RPT-076). Semua ID dipetakan ulang dalam satu pass, termasuk rujukan silang di ODR/ADR/RES:

| Jenis | Paket asli | Sekarang |
|---|---|---|
| TASK | 043–097 | 051–105 (049 dan 050 = hotfix build baru) |
| BL | 084–090 | 086–092 |
| SPEC | 010–016 | 011–017 |
| US | 004 | 009 |
| RPT | 076 | 108 |
| PRD | 002 | 002 (tetap; PRD-001 dipakai sebagai contoh di TEMPLATES.md) |

ODR-26..33 dan ADR-0018 tidak bentrok dengan ODR-01..25 / ADR-0001..0003 di `standard-docs`.

## Cara menerapkan
1. Board sudah di-push ke `import-main` (`f4e2dde`). Semua 48 task lama berstatus `done` dan `validate.py --all` = ALL VALID; tidak ada task lama yang perlu ditutup.
2. Berkas paket sudah berada di board (sprint-09..15 `status: planning`, `product-backlog/`, `research/`, amandemen RULES/TEMPLATES). Bridge hanya membaca sprint `active` (`_active_task_files`), jadi belum ada yang berjalan.
3. Dokumen `standard-docs` untuk TASK-052 berada di `research/rust-single-language/package/galleon-fleet/standard-docs/` (path absolut dipakai di deskripsi task).
4. Owner meng-approve PRD-002 dan menjawab/menerima default Q1–Q9; Lead meng-approve SPEC-011.
5. Aktifkan Sprint 09 (`status: active`, isi `start`/`end`) mengikuti checklist `RULES-amendment` §A3. TASK-049 (hotfix build) berjalan lebih dulu dan tidak bergantung pada TASK-051..057.
6. Setelah TASK-056 merged: tambahkan `bash scripts/ci/check_no_go.sh diff` ke `~/Apps/dev-ci/repos/galleon-fleet/gates.sh`.

## Pertanyaan terbuka (default dipakai bila tidak dijawab)
| # | Pertanyaan | Default |
|---|---|---|
| Q1 | Learning proposals (UI sudah 404 hari ini) | Sembunyikan UI, tidak di-port |
| Q2 | Snapshot | Port sebagai snapshot nyata |
| Q3 | Intent "objective" Quartermaster | Chat biasa via agent Rust, tanpa klaim draft |
| Q4 | Ada instance Sonar? | Konfigurasi siap, job hanya bila `SONAR_TOKEN` ada |
| Q5 | Pairing web manual dari CLI | Ya, tanpa auto-pair localhost |
| Q6 | Sumber seed | `engine/data` |
| Q7 | `target_release` | (belum ada) |
| Q8 | Pulihkan TLS/`path_prefix`/tunnel | Ya; boleh aktifkan Sprint 15 tepat setelah Sprint 10 |
| Q9 | mDNS advertisement | Tidak dipulihkan sampai ada konsumen |

## Temuan yang perlu perhatian Owner
- **F-18 (keamanan, ada hari ini):** sejak `db18a3745`, gateway tidak memanggil `tls::build_tls_acceptor`; `[gateway.tls] enabled = true` diabaikan dan gateway melayani HTTP polos. `path_prefix`, start tunnel, dan peringatan public bind juga hilang.
- **F-14:** `crates/galleon-gateway/src/tests.rs` (7.596 baris) tidak dideklarasikan sebagai modul — test-nya tidak pernah jalan; handler admin yang dipanggil CLI sudah dihapus.
- **Body limit:** Go tidak membatasi body `PUT /api/collections`; batas global Rust 64 KB akan meregresi koleksi besar → router fleet memakai batas 1 MiB sendiri (SPEC-012/013).
- **Bridge:** auto-unblock hanya mengenali branch `feat/...` dan prasyarat di sprint aktif yang sama; `board_switch.py` meng-import `board_audit` yang tidak ada di repo board.
- **Web test:** script `test` = `node --test`, sedangkan test berupa `.test.tsx` tanpa vitest/jest — kemungkinan tidak pernah tereksekusi (dicatat, tidak diperbaiki; YAGNI).
