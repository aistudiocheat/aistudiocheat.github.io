import os
import datetime
import re
import random
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom
from google import genai
from google.genai.types import HttpOptions

# 1. Gunakan API Versi v1 Stabil
client = genai.Client(http_options=HttpOptions(api_version="v1"))

# 2. Bank Ide: 20 Topik Masalah Konversi Google AI Studio ke Versi Produksi
DAFTAR_TOPIK = [
    "Cara Integrasi API Gemini 3.5 Flash ke Android Studio Kotlin untuk Pemula",
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

# =====================================================================
# 4. SISTEM ANTI-SIBUK (RETRY LOGIC DENGAN 3 KALI KESEMPATAN COBA LAGI)
# =====================================================================
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
        print(f"Server Google sibuk (Eror: {e}). Mencoba lagi dalam 10 detik... (Percobaan {percobaan + 1}/{maksimal_coba})")
        time.sleep(10)

if not konten_markdown:
    raise Exception("Gagal mendapatkan respons dari Gemini setelah dicoba 3 kali karena server Google sibuk.")

# 5. Membuat nama file slug tanpa tanggal
slug = TOPIK_HARI_INI.lower()
slug = re.sub(r'[^a-z0-9\s-]', '', slug)
slug = re.sub(r'[\s-]+', '-', slug).strip('-')
nama_file = f"posts/{slug}.md"

# 6. Simpan file markdown artikel
os.makedirs("posts", exist_ok=True)
with open(nama_file, "w", encoding="utf-8") as f:
    f.write(konten_markdown)
print(f"Sukses! Artikel ramah SEO berhasil disimpan di: {nama_file}")

# =====================================================================
# 7. FITUR OTOMATIS GENERATE/UPDATE SITEMAP.XML UNTUK GOOGLE SEO
# =====================================================================
SITEMAP_PATH = "sitemap.xml"

# Kita buat kerangka XML menggunakan format teks langsung agar domain tidak terpotong library Python
xml_konten = '<?xml version="1.0" encoding="utf-8"?>\n'
xml_konten += '<urlset xmlns="http://sitemaps.org">\n'

# Masukkan Halaman Utama (Beranda) dengan domain yang sudah dikunci
xml_konten += '  <url>\n'
xml_konten += '    <loc>https://github.io</loc>\n'
xml_konten += f'    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n'
xml_konten += '    <changefreq>daily</changefreq>\n'
xml_konten += '    <priority>1.0</priority>\n'
xml_konten += '  </url>\n'

# Deteksi otomatis semua artikel .md yang sudah ada di folder posts/
if os.path.exists("posts"):
    for file in os.listdir("posts"):
        if file.endswith(".md"):
            clean_slug = file.replace(".md", "")
            # Menyusun tautan artikel murni menggunakan nama domain Anda secara utuh
            url_article_path = f"https://github.io#article/{clean_slug}"
            
            xml_konten += '  <url>\n'
            xml_konten += f'    <loc>{url_article_path}</loc>\n'
            xml_konten += f'    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n'
            xml_konten += '    <changefreq>weekly</changefreq>\n'
            xml_konten += '    <priority>0.8</priority>\n'
            xml_konten += '  </url>\n'

xml_konten += '</urlset>'

# Simpan/Overwrite file sitemap.xml di root folder repositori
with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
    f.write(xml_konten)

print("Sukses! File sitemap.xml dengan domain asli berhasil diperbarui otomatis.")
