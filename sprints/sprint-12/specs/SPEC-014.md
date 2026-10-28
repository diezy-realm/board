---
id: SPEC-014
type: spec
spec_kind: api
title: Cutover Web, Desktop (Tauri), Nginx ke gateway Rust dengan alur pairing
status: approved
source_prd: PRD-002
author: kirocrew
created: 2026-10-29
---
> Peran penyusun: Senior Lead Engineer. Fakta: RES baseline F-02, F-15, F-16, F-17; SPEC-012 (rute pairing), SPEC-013 (rute fleet).

## Pernyataan Masalah (Problem Statement)
1. Web dev proxy `/api` → `process.env.ENGINE_URL || 'http://127.0.0.1:9090'` (`web/vite.config.ts:22–24`); Nginx upstream `127.0.0.1:9090` (`nginx/galleon.conf:10–11`); Tauri `GALLEON_ENGINE_URL` default `:9090` (`apps/tauri/src/main.rs:13–14`) dan CSP `connect-src ... :9090` (`apps/tauri/tauri.conf.json:32`).
2. Web tidak punya alur auth (F-15): 20 `fetch('/api/...')` mentah, hanya terminal yang mengirim Bearer, tidak ada yang menyimpan `galleon_auth_token`. Gateway Rust mewajibkan pairing (`require_pairing` default true).
3. Web memanggil `invokeTauri('get_api'|'post_api')` (`apiClient.ts:431,446`) yang **tidak ada** di Tauri; Tauri justru punya 14 command proxy per-fitur ke Go tanpa header auth (`main.rs:44–136`). Gateway Rust tidak memasang CORS (`rg -n 'CorsLayer|Access-Control' crates/galleon-gateway/src` kosong), jadi webview Tauri tidak bisa `fetch` lintas origin ke gateway.
4. Web memakai path pairing Go (`/api/pairing/{initiate,devices,revoke}`, `ConnectedDevicesView.tsx:33,53,71`) yang berbeda dari API Rust (`/api/pairing/initiate`, `/api/devices`, `DELETE /api/devices/{id}`).
5. UI memanggil endpoint yang tidak di-port (SPEC-013): learning proposals, remedy, tool-executions; dan beberapa fallback teks karangan di UI (mis. `EngineRoomView.tsx:988` `'4h 12m'`).

## Solusi yang Diusulkan (Proposed Solution)
1. **TASK-082 — Satu pintu request di web.** Di `web/src/utils/apiClient.ts`:
   - `const TOKEN_KEY = 'galleon_auth_token'`; `getToken()/setToken()/clearToken()`.
   - `async function request<T>(method, path, body?)`: bila `isTauri()` → `invokeTauri('api_request', {method, path, body, token})`; selain itu `fetch(path, {headers: {Authorization: Bearer, Content-Type}})` (relatif, lewat proxy Vite/Nginx). Status 401 → `clearToken()` + event `galleon:unauthorized`.
   - Semua method (`getCollection`, `saveCollection`, `getSnapshots`, …, `executeTerminalCommand`, `get`, `post`) memakai `request`. Cabang `invokeTauri('<per-fitur>')` dihapus. `getHealth` (tidak dipakai) dihapus.
   - `web/vite.config.ts`: target `process.env.GALLEON_GATEWAY_URL || 'http://127.0.0.1:42617'` (port default `galleon-config/src/schema.rs:7743–7745`); proxy juga untuk `/pair` (prefix `/pair`, bukan `/pairing`).
2. **TASK-083 — Layar pairing.** Komponen `PairingGate` membungkus `App`: bila tidak ada token atau menerima `galleon:unauthorized` → form kode pairing. Saat mount, coba `GET /pair/code` (mengisi otomatis kode bila gateway belum pernah dipasangkan, perilaku sama dengan ACP bridge `src/bin/clawcrew-acp-bridge.rs:287`). Submit → `POST /pair` dengan header `X-Pairing-Code` → simpan token. Teks bantuan: "Jalankan `galleon gateway get-paircode`". Tanpa auto-pair localhost (default Q5 PRD).
3. **TASK-084 — Penyesuaian fitur web.**
   - `ConnectedDevicesView.tsx`: `GET /api/devices`, `DELETE /api/devices/{id}`, `POST /api/pairing/initiate` (bentuk respons mengikuti `api_pairing.rs`).
   - Sembunyikan UI learning proposals (default Q1) dan tombol remedy; `fleetStore.handleApproval` berhenti memanggil `approveToolExecution` (method dihapus) — status approval tetap disimpan di koleksi `approvals`.
   - Tipe TS: field yang kini `null` (SPEC-013 §Model Data) → `number | null` / `string | null`; render `—` bila null. Hapus fallback karangan di panel yang memakai endpoint ini (`rg -n "\|\| '[0-9]" web/src/components/features` sebagai daftar awal; hanya yang terkait endpoint yang dimigrasi).
   - `hydrateFleet` membaca kunci camelCase (sudah) — kini terisi 15/15 (F-16).
4. **TASK-085 — Tauri.** Ganti 14 command proxy dengan satu `api_request(method, path, body, token)`: `path` wajib diawali `/api/` atau sama dengan `/pair` / `/pair/code`; base URL `GALLEON_GATEWAY_URL` default `http://127.0.0.1:42617`; meneruskan `Authorization: Bearer <token>` bila ada; timeout 30 s; mengembalikan `{status, body}` agar web dapat menangani 401. `get_sidecar_status`, tray, `try_spawn_sidecar` tetap. CSP `connect-src 'self' ipc: http://ipc.localhost` (hapus `:9090`; request HTTP lewat Rust Tauri, bukan webview). Perbarui `apps/tauri/AGENTS.md` dan komentar `apps/tauri/Cargo.toml:20`.
5. **TASK-086 — Nginx.** `upstream galleon_backend { server 127.0.0.1:42617; }`; tambah `location = /pair` dan `location = /pair/code`; hapus lokasi yang tidak punya rute Rust (`api/v1/stream`, `api/v1/events`, `api/terminal/ws`, `api/v1/ws` — dicek terhadap `consumer-inventory.md`); `/ws` tetap dengan header Upgrade. Komentar baris 3 diperbarui.
6. **TASK-087 — Smoke E2E.** `scripts/e2e/smoke_dashboard.sh`: start `galleon daemon` dengan `GALLEON_CONFIG_DIR` sementara, ambil kode via `galleon gateway get-paircode`, `POST /pair`, lalu panggil setiap rute di `consumer-inventory.md` berstatus `port`/`restore` dengan token (harus 2xx/expected) dan tanpa token (harus 401). Tidak ada proses Go yang berjalan (`pgrep -f agent-engine` kosong).

## Model Data (Data Model)
- `localStorage['galleon_auth_token']`: string token pairing. Tidak ada data lain di localStorage.
- Tauri `api_request` respons: `{"status": u16, "body": serde_json::Value}`.

## Desain API (API Design)
Tidak ada endpoint gateway baru. Kontrak Tauri command baru:

| Command | Argumen | Hasil | Error |
|---|---|---|---|
| `api_request` | `method: "GET"\|"POST"\|"PUT"\|"PATCH"\|"DELETE"`, `path: string`, `body?: Value`, `token?: string` | `{status, body}` | `Err("path not allowed")` bila path di luar prefix; `Err("gateway unreachable: ...")` |

Pemetaan path web lama → baru:

| Lama (Go) | Baru (Rust) |
|---|---|
| `GET /api/pairing/devices` | `GET /api/devices` |
| `POST /api/pairing/revoke {device_id}` | `DELETE /api/devices/{id}` |
| `POST /api/pairing/initiate` | `POST /api/pairing/initiate` |
| `POST /api/v1/tool-executions/{id}/{action}` | dihapus |
| `/api/v1/learning/proposals*` | dihapus (UI disembunyikan) |
| `POST /api/diagnostics/remedy` | dihapus |

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- CORS di gateway untuk origin Tauri → ditolak: menambah permukaan serangan cross-origin pada gateway yang bind localhost; proxy Tauri cukup dan web sudah mengharapkan command generik.
- Mempertahankan 14 command per-fitur dan menambah token → ditolak: duplikasi kontrak (masalah awal program ini).
- Auto-pair untuk request dari localhost → ditolak: setiap proses lokal (termasuk halaman web berbahaya via DNS rebinding) akan mendapat token.
- Menyimpan token di cookie HttpOnly → ditolak untuk sprint ini: gateway memakai Bearer di seluruh API; mengubah model auth di luar lingkup. Risiko XSS dicatat di bawah.

## Pertimbangan Keamanan (Security Considerations)
- OWASP Top 10:2025 A01/A07; ASVS 5.0 V3 (Web Frontend Security) & V9 (token). Token di `localStorage` terekspos bila ada XSS; mitigasi yang ada: CSP Tauri `script-src 'self'`; untuk web/Nginx tambahkan header CSP yang sama di `nginx/galleon.conf` (TASK-086). Dicatat sebagai risiko diterima di RPT.
- `api_request` membatasi prefix path (mencegah Tauri dipakai sebagai proxy SSRF ke host lain: base URL tetap, path tidak boleh berisi `://` atau `..`).
- 401 membersihkan token (tidak ada retry diam-diam).

## Rencana Pengujian (Testing Plan)
- Web: `npm run typecheck`, `npm run build`. **Fakta:** script `test` adalah `node --test` (`web/package.json:14`) sedangkan test berada di `web/src/__tests__/*.test.tsx` tanpa vitest/jest di `package.json` — kemungkinan test TSX tidak pernah dieksekusi. TASK-082 mencatat output `npm test` apa adanya di RPT; menambah framework test **tidak** termasuk lingkup (perlu story terpisah bila Owner menginginkannya). Logika `request` ditulis sebagai fungsi murni kecil agar bisa diuji `node --test` bila memungkinkan.
- Tauri: `cargo check --manifest-path apps/tauri/Cargo.toml` + unit test validasi path `api_request` (`/api/x` ok; `http://evil`, `/../`, `/admin/shutdown` ditolak).
- Nginx: `nginx -t -c nginx/galleon.conf` (di container `nginx:stable` bila nginx tidak terpasang).
- E2E: TASK-087 output disalin ke RPT.
- Cek statis: `rg -n ':9090|ENGINE_URL' web apps/tauri nginx` kosong; `rg -n "fetch\(" web/src -g '!**/__tests__/**'` hanya di `request`.

## Rollout / Migrasi
082 → 083 → 084 → 085 → 086 → 087. Setelah TASK-082 merged, dashboard dev butuh token (TASK-083 menyusul di sprint yang sama; sementara itu developer mengisi `localStorage` manual — dicatat di RPT TASK-082). Rollback: revert PR; Go masih ada sampai Sprint 13.
