import os
import datetime
import re
import random
from google import genai
from google.genai.types import HttpOptions

# 1. Gunakan API Versi v1 Stabil agar tidak terjadi bentrok model
client = genai.Client(http_options=HttpOptions(api_version="v1"))

# 2. Bank Ide: 20 Topik Masalah Konversi dari Google AI Studio ke Versi Produksi (Siap Play Store)
DAFTAR_TOPIK = [
    "Cara Integrasi API Gemini 2.5 Flash ke Android Studio Kotlin untuk Pemula",
    "Kenapa Aplikasi Android Buatan Google AI Studio Tidak Bisa Langsung di-Upload ke Play Store?",
    "Panduan Membuat Aplikasi Chatbot Android Menggunakan Template Google AI Studio",
    "Cara Mengatasi Error API Key Bocor saat Export Project dari Google AI Studio ke Android Studio",
    "Mengenal Keystore dan SHA-256: Langkah Wajib Sebelum Merilis Aplikasi Android AI ke Publik",
    "Tips Vibe Coding: Bikin Prototype Aplikasi Android Cepat Lewat Google AI Studio",
    "Cara Cepat Mengubah File Zip dari Google AI Studio Menjadi Project Android Studio yang Siap Dicoding",
    "Cara Mengatur Layout UI Android agar Rapi Saat Menggunakan Elemen AI dari Google AI Studio",
    "Menghubungkan Database Room dengan Hasil Output Text dari Gemini API di Android Studio",
    "Cara Mengamankan Gemini API Key Menggunakan Firebase Vertex AI di Android",
    "Mengatasi Kendala Layout Thrashing saat Streaming Respons Gemini API di Jetpack Compose",
    "Cara Membangun Backend Proxy Node.js agar API Key Google AI Studio Tidak Ditanam di Aplikasi Android",
    "Panduan Konfigurasi ProGuard dan R8 untuk Mengamankan Kode Aplikasi Android Berbasis Gemini AI",
    "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro",
    "Arsitektur MVVM yang Benar untuk Mengelola State Output Google AI Studio di Android Studio",
    "Cara Membuat Pipeline CI/CD GitHub Actions untuk Otomatisasi Build APK Aplikasi Android AI Anda",
    "Mengatasi Error Ketergantungan Dependency Gradle saat Memasukkan SDK Google AI Terbaru ke Android Studio",
    "Strategi Caching Menggunakan DataStore untuk Menghemat Kuota Token API Gemini di Android",
    "Cara Handle Error Connection Timeout dan Internet Terputus saat Aplikasi Memanggil Google AI Studio",
    "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
]

TOPIK_HARI_INI = random.choice(DAFTAR_TOPIK)
print(f"Agen AI sedang menulis artikel konversi tentang: {TOPIK_HARI_INI}...")

# 3. Prompt Khusus SEO + Agitasi Masalah untuk Konversi Jasa Fastwork
prompt = f"""
Anda adalah Penulis Konten Tech SEO Senior dan Pakar DevOps Android.
Tulis sebuah artikel tutorial/edukasi blog berformat Markdown (.md) yang mendalam, berbobot, dan sangat membantu pembaca tentang: "{TOPIK_HARI_INI}".

Struktur Artikel Wajib:
1. Front Matter di bagian paling atas:
---
title: "{TOPIK_HARI_INI}"
date: "{datetime.date.today().isoformat()}"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

2. Bagian Isi Artikel:
- Berikan langkah-langkah tutorial yang benar-benar solutif dengan heading (##) dan blok kode.
- Agitasi Masalah: Di bagian menjelang akhir artikel, jelaskan secara halus bahwa mengonfigurasi proyek dari Google AI Studio hingga menjadi versi produksi (seperti setup backend proxy, Firebase, arsitektur kode bersih MVVM, keamanan ProGuard, keystore, hingga DevOps CI/CD) sangat rumit bagi pemula atau pemilik bisnis. Berikan penekanan bahwa menggunakan jasa ahli akan menghemat waktu mereka dan menjamin keamanan aplikasi.

Catatan: Jangan tuliskan link CTA Fastwork secara manual di teks ini.
"""

# 4. Panggil model Gemini 3.5 Flash
response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=prompt,
)

konten_markdown = response.text

# 5. Membuat nama file murni kata kunci (Slug Tanpa Angka Tanggal)
slug = TOPIK_HARI_INI.lower()
slug = re.sub(r'[^a-z0-9\s-]', '', slug)
slug = re.sub(r'[\s-]+', '-', slug).strip('-')

nama_file = f"posts/{slug}.md"

# 6. Simpan file
os.makedirs("posts", exist_ok=True)
with open(nama_file, "w", encoding="utf-8") as f:
    f.write(konten_markdown)

print(f"Sukses! Artikel ramah SEO berhasil disimpan di: {nama_file}")
