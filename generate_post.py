import os
import datetime
import re
import random
import time
from google import genai
from google.genai.types import HttpOptions

# 1. Menggunakan API Versi v1 Stabil dan model Pro yang tangguh
client = genai.Client(http_options=HttpOptions(api_version="v1"))

# 2. Bank Ide: 20 Topik Masalah Konversi Google AI Studio ke Versi Produksi
DAFTAR_TOPIK = [
    "Cara Integrasi API Gemini ke Android Studio Kotlin untuk Pemula",
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

# 3. Prompt Khusus SEO + Agitasi Masalah Jasa Fastwork
prompt = f"""
Anda adalah Penulis Konten Tech SEO Senior dan Pakar DevOps Android.
Tulis sebuah artikel tutorial/edukasi blog berformat Markdown (.md) yang mendalam dan sangat membantu pembaca tentang: "{TOPIK_HARI_INI}".

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
- Agitasi Masalah: Di bagian menjelang akhir artikel, jelaskan secara halus bahwa mengonfigurasi proyek dari Google AI Studio hingga menjadi versi produksi sangat rumit bagi pemula.

Catatan: Jangan tuliskan link CTA Fastwork secara manual di teks ini.
"""

# 4. Sistem Anti-Sibuk Server Google
maksimal_coba = 3
konten_markdown = ""

for percobaan in range(maksimal_coba):
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        konten_markdown = response.text
        if konten_markdown:
            break
    except Exception as e:
        print(f"Server Google sibuk. Mencoba lagi dalam 10 detik... (Percobaan {percobaan + 1}/{maksimal_coba})")
        time.sleep(10)

if not konten_markdown:
    raise Exception("Gagal mendapatkan respons dari Gemini.")

# 5. Membuat nama file slug tanpa tanggal
slug_raw = TOPIK_HARI_INI.lower()
slug_clean = re.sub(r'[^a-z0-9\s-]', '', slug_raw)
slug = re.sub(r'[\s-]+', '-', slug_clean).strip('-')
nama_file = f"posts/{slug}.md"

# 6. Simpan file markdown artikel
os.makedirs("posts", exist_ok=True)
with open(nama_file, "w", encoding="utf-8") as f:
    f.write(konten_markdown)
print(f"Sukses! Artikel ramah SEO berhasil disimpan di: {nama_file}")

# =====================================================================
# 7. FITUR SITEMAP XML (KUNCI TOTAL DOMAIN ASLI KAMU TANPA BAGI VARIABEL)
# =====================================================================
SITEMAP_PATH = "sitemap.xml"

# Menggunakan cetakan teks murni yang mengunci domain milikmu secara permanen
xml_header = '<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://sitemaps.org">\n'
xml_beranda = f'  <url>\n    <loc>https://aistudiocheat.github.io/</loc>\n    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'

xml_item_artikel = ""
if os.path.exists("posts"):
    for file_name in os.listdir("posts"):
        if file_name.endswith(".md"):
            clean_slug_artikel = file_name.replace(".md", "")
            
            # Membentuk string URL secara utuh dan saklek ke domain aistudiocheat
            xml_item_artikel += '  <url>\n'
            xml_item_artikel += f'    <loc>https://aistudiocheat.github.io/#article/{clean_slug_artikel}</loc>\n'
            xml_item_artikel += f'    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n'
            xml_item_artikel += '    <changefreq>weekly</changefreq>\n'
            xml_item_artikel += '    <priority>0.8</priority>\n'
            xml_item_artikel += '  </url>\n'

xml_final = xml_header + xml_beranda + xml_item_artikel + '</urlset>'

# Simpan perubahan final sitemap ke root folder
with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
    f.write(xml_final)

print("Sukses! File sitemap.xml dengan domain asli aistudiocheat berhasil diperbarui otomatis.")
