---
id: SPEC-005
type: spec
spec_kind: tech
title: Arsitektur End-to-End Testing Galleon Fleet dengan Data Real & Socket Nyata
status: approved
source_prd:
author: kirocrew
created: 2026-10-22
---
## Pernyataan Masalah (Problem Statement)
Setelah dekomposisi modular gateway pada Sprint 03 (`api_config/`, `ws/`, `api_sections/`) dan decouplement dari `clawcrew-runtime` (T3-02), sistem memerlukan pembuktian empiris komprehensif bahwa seluruh subsistem bekerja secara harmonis dalam kondisi operasional nyata.

Sebelumnya, sejumlah integrasi mengandalkan objek mock (seperti `MockModelProvider` atau dummy transport) yang berisiko menutupi cacat pada lapisan serialisasi data, race condition pada socket TCP, kegagalan migrasi SQLite fisik, atau bypass permission pada outbound egress. Diperlukan suite pengujian **End-to-End (E2E)** berbasis **Zero-Mockup Data** di mana seluruh interaksi menggunakan protokol dan storage aktual.

## Solusi yang Diusulkan (Proposed Solution)
Membangun dan menyusun harness E2E yang beroperasi secara deterministik tanpa mockup:

### 1. Gateway REST & WebSocket Protocol E2E (TASK-030)
- **Komponen**: `clawcrew-gateway` + `axum` + `tokio-tungstenite` + `reqwest`.
- **Mekanisme**:
  - Inisialisasi router Axum penuh dan bind ke port ephemeral dinamis `127.0.0.1:0`.
  - Mengambil port aktual dari listener dan membuat client HTTP/WebSocket asli.
  - Melakukan handshake WebSocket, streaming chat frames, pengiriman perintah, dan validasi response body real JSON.
  - Memverifikasi health (`/health`), readiness (`/ready`), dan rute per-section (`/api/sections/*`).

### 2. Config Atomic Persistence & Drift Detection E2E (TASK-031)
- **Komponen**: `clawcrew-config` + `clawcrew-gateway/api_config` + disk filesystem.
- **Mekanisme**:
  - Menyiapkan direktori isolasi nyata via `tempfile::tempdir()`.
  - Menulis berkas konfigurasi awal `config.toml` dengan schema baku default.
  - Mengirimkan operasi `PATCH /api/config` dengan operasi JSON Patch valid (RFC 6902) untuk memperbarui field operasional.
  - Memverifikasi penulisan atomik ke disk (`persist_and_swap`) dan konsistensi file.
  - Melakukan mutasi eksternal langsung pada berkas disk, memanggil deteksi drift (`try_compute_drift`), dan memverifikasi diff pergeseran state tanpa mock store.

### 3. Channel Ingress Webhook & Outbound Egress Enforcement E2E (TASK-032)
- **Komponen**: `clawcrew-channels` + `galleon-channel-*` + network sandbox.
- **Mekanisme**:
  - Mengirimkan payload webhook HTTP riil dengan header signature kriptografi HMAC SHA-256 yang valid.
  - Memverifikasi penolakan (HTTP 401/403) pada signature cacat, dan penerimaan (HTTP 200) pada signature sah.
  - Menjalankan TCP listener lokal untuk memvalidasi kebijakan keamanan outbound egress (pembatasan koneksi ke host/port yang diizinkan saja).

### 4. Multi-Agent Session & SQLite Memory Continuity E2E (TASK-033)
- **Komponen**: `clawcrew-memory` + `clawcrew-runtime` + disk SQLite.
- **Mekanisme**:
  - Membuat berkas basis data SQLite nyata pada disk (`test_memory.db`) dan menjalankan migrasi schema asli (`001_initial.sql`).
  - Menjalankan session multi-turn dengan tool execution riil (bukan mock tool).
  - Menghentikan instans runtime (drop), membuat instans baru yang terhubung ke SQLite file yang sama, dan memvalidasi riwayat percakapan, memory recall, dan ledger audit token/biaya utuh 100%.

## Model Data (Data Model)
- **Konfigurasi Riil**: Struct `clawcrew_config::schema::Config` dengan serialisasi TOML/JSON asli.
- **Database Schema**: Tabel SQLite nyata (`sessions`, `turns`, `memory_facts`, `cost_audit_log`).
- **Protokol Wire**: Format frame WebSocket biner dan teks standar RFC 6455.

## Alternatif yang Dipertimbangkan (Alternatives Considered)
- *Menggunakan MockModelProvider untuk seluruh pengujian*: Ditolak, karena mandat Owner mewajibkan verifikasi data nyata guna mencegah celah integrasi.
- *Menjalankan server eksternal di cloud*: Ditolak, karena pengujian harus sepenuhnya mandiri, deterministik, dan dapat dijalankan pada CI lokal (`dev-ci`) tanpa ketergantungan internet publik.

## Pertimbangan Keamanan (Security Considerations)
- Pengujian menggunakan port loopback lokal `127.0.0.1` tanpa memapar port ke antarmuka publik `0.0.0.0`.
- Kunci API dan rahasia enkripsi pada pengujian menggunakan kunci ephemeral uji coba yang dihasilkan secara dinamis, mencegah false-positive pada credential scanner Principle Gate.

## Rencana Pengujian (Testing Plan)
- Menjalankan seluruh test case E2E via `cargo nextest run --locked` dengan filter target pengujian yang relevan.
- Validasi kepatuhan kode via `cargo check --tests` dan `cargo fmt --check`.

## Rollout / Migrasi
Dikelompokkan ke dalam 4 task sekuensial (TASK-030 s.d. TASK-033) pada Sprint 04. Setiap task harus selesai dan terverifikasi sebelum task dependen dieksekusi.
