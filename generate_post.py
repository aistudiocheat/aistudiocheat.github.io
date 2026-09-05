import os
import datetime
import re
import random
from google import genai

# 1. Inisialisasi Gemini API menggunakan SDK terbaru
client = genai.Client()

# 2. Bank Ide Topik - Tempat Agen AI memilih masalah yang sering dihadapi developer pemula
DAFTAR_TOPIK = [
    "Cara Integrasi API Gemini 2.5 Flash ke Android Studio Kotlin untuk Pemula",
    "Kenapa Aplikasi Android Buatan Google AI Studio Tidak Bisa Langsung di-Upload ke Play Store?",
    "Panduan Membuat Aplikasi Chatbot Android Menggunakan Template Google AI Studio",
    "Cara Mengatasi Error API Key Bocor saat Export Project dari Google AI Studio ke Android Studio",
    "Mengenal Keystore dan SHA-256: Langkah Wajib Sebelum Merilis Aplikasi Android AI ke Publik",
    "Tips Vibe Coding: Bikin Prototype Aplikasi Android Cepat Lewat Google AI Studio",
    "Cara Cepat Mengubah File Zip dari Google AI Studio Menjadi Project Android Studio yang Siap Dicoding",
    "Cara Mengatur Layout UI Android agar Rapi Saat Menggunakan Elemen AI dari Google AI Studio",
    "Menghubungkan Database Room dengan Hasil Output Text dari Gemini API di Android Studio"
]

# Agen memilih 1 topik secara acak setiap harinya
TOPIK_HARI_INI = random.choice(DAFTAR_TOPIK)

print(f"Agen AI sedang menulis artikel konversi tentang: {TOPIK_HARI_INI}...")

# 3. Prompt Khusus SEO + Strategi Konversi Jasa Fastwork (Problem-Agitation)
prompt = f"""
Anda adalah Penulis Konten Tech SEO Senior dan Pakar DevOps Android.
Tulis sebuah artikel tutorial/edukasi blog berformat Markdown (.md) yang mendalam, berbobot, dan sangat membantu pembaca tentang: "{TOPIK_HARI_INI}".

Struktur Artikel Wajib:
1. Front Matter di bagian paling atas (tulis persis format ini):
---
title: "{TOPIK_HARI_INI}"
date: "{datetime.date.today().isoformat()}"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

2. Bagian Isi Artikel:
- Berikan langkah-langkah tutorial atau penjelasan teknis yang benar-benar solutif.
- Gunakan format Markdown yang rapi dengan heading (##), list, dan blok kode (`kotlin`, `xml`, atau `bash` jika ada contoh kodenya).
- **Agitasi Masalah (Penting untuk Konversi):** Di bagian menjelang akhir artikel, jelaskan secara halus bahwa mengonfigurasi proyek dari Google AI Studio menjadi aplikasi produksi yang siap rilis (seperti setup Gradle, keystore, arsitektur kode yang bersih, atau otomasi CI/CD) sering kali rumit, memakan waktu, dan rawan error bagi pemula atau pemilik bisnis. Berikan penekanan bahwa bantuan dari seorang ahli akan menghemat waktu mereka.

Catatan: Jangan tuliskan link CTA Fastwork secara manual di teks ini, karena sistem HTML Anda sudah menampilkannya otomatis di bawah file markdown.
"""

# 4. Memanggil model Gemini 2.5 Flash yang cerdas dan efisien
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
)

konten_markdown = response.text

# 5. Membuat nama file (slug) yang ramah SEO dari judul topik
slug = TOPIK_HARI_INI.lower()
slug = re.sub(r'[^a-z0-9\s-]', '', slug) # Hapus karakter aneh
slug = re.sub(r'[\s-]+', '-', slug).strip('-') # Ubah spasi jadi tanda minus

tanggal = datetime.date.today().isoformat()
nama_file = f"posts/{tanggal}-{slug}.md"

# 6. Memastikan folder posts/ ada dan menyimpan file markdown artikel
os.makedirs("posts", exist_ok=True)
with open(nama_file, "w", encoding="utf-8") as f:
    f.write(konten_markdown)

print(f"Sukses! Artikel berhasil dibuat dan disimpan di: {nama_file}")
