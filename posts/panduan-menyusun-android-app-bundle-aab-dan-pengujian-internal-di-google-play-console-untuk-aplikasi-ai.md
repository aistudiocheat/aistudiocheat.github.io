---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-09-05"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Artificial Intelligence (AI) ke dalam aplikasi Android—seperti menggunakan Gemini API melalui Google AI Studio—membuka peluang inovasi yang luar biasa. Namun, menjembatani fase *development* lokal di Android Studio hingga aplikasi siap diuji oleh tim internal melalui Google Play Console memerlukan pemahaman DevOps Android yang matang. 

Format **Android App Bundle (AAB)** kini menjadi standar wajib rilis di Google Play Store menggantikan APK konvensional karena efisiensi ukuran unduhan (Dynamic Delivery). Bagi aplikasi berbasis AI, proses penyusunan (bundling) ini menuntut perhatian ekstra, terutama terkait keamanan API Key, optimasi library AI, dan konfigurasi ProGuard agar kode tidak rusak saat diobfuskasi.

Artikel ini akan memandu Anda secara mendalam langkah demi langkah untuk menyusun AAB yang aman dan melakukan distribusi pengujian internal di Google Play Console.

---

## Langkah 1: Mengamankan API Key Gemini pada Level Gradle

Kesalahan fatal developer pemula adalah melakukan *hardcoding* API Key Google AI Studio langsung di dalam kelas Kotlin/Java. Hal ini membuat API Key Anda sangat rentan didekompilasi melalui teknik *reverse engineering*.

Cara terbaik untuk mengamankannya adalah menggunakan **Secrets Gradle Plugin untuk Android**.

### 1. Tambahkan Plugin ke Proyek Anda
Buka file `build.gradle.kts` (Project level) dan tambahkan dependensi berikut:

```kotlin
plugins {
    // ...
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

Kemudian, buka `build.gradle.kts` (Module:app level) dan terapkan plugin tersebut:

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}
```

### 2. Simpan API Key di `local.properties`
Buka file `local.properties` di root direktori proyek Anda (pastikan file ini sudah masuk dalam `.gitignore`) dan tambahkan baris berikut:

```properties
GEMINI_API_KEY=AIzaSyD-YourActualGeminiApiKeyHere...
```

### 3. Panggil API Key dalam Kode Kotlin
Plugin secara otomatis akan menghasilkan variabel di kelas `BuildConfig` yang bisa Anda panggil dengan aman:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel

val generativeModel = GenerativeModel(
    modelName = "gemini-1.5-pro",
    apiKey = BuildConfig.GEMINI_API_KEY
)
```

---

## Langkah 2: Optimasi ProGuard / R8 untuk SDK Google AI

Saat Anda melakukan build rilis dengan format AAB, kompiler R8 akan melakukan ciutkan kode (shrinking) dan obfuskasi untuk memperkecil ukuran file. Namun, SDK Google AI seringkali menggunakan refleksi (reflection) atau serialisasi JSON yang dapat rusak jika nama kelasnya diubah secara acak oleh R8.

Untuk mencegah crash pada aplikasi rilis Anda, tambahkan aturan berikut pada file `proguard-rules.pro`:

```proguard
# Menjaga kelas SDK Google AI dari obfuskasi yang merusak serialisasi data
-keep class com.google.ai.client.generativeai.** { *; }
-keep interface com.google.ai.client.generativeai.** { *; }

# Jika Anda menggunakan Kotlin Serialization atau Gson untuk parsing data AI
-keepattributes Signature, *Annotation*, EnclosingMethod, InnerClasses
-dontwarn kotlinx.serialization.json.**
```

---

## Langkah 3: Menghasilkan (Build) Android App Bundle (AAB)

Setelah konfigurasi build aman dan optimasi R8 selesai, saatnya membuat file `.aab`.

### 1. Membuat Keystore Baru (Jika Belum Ada)
Di Android Studio, klik **Build > Generate Signed Bundle / APK...**
1. Pilih **Android App Bundle** lalu klik *Next*.
2. Pada *Key store path*, klik **Create new...** jika Anda belum memiliki kunci rilis.
3. Isi informasi yang diperlukan (pastikan Anda menyimpan file `.jks` ini dan mengingat password-nya dengan baik demi masa depan update aplikasi Anda).

### 2. Melakukan Build Release via CLI (Rekomendasi DevOps)
Untuk konsistensi dan integrasi CI/CD di masa depan, Anda bisa melakukan build menggunakan Gradle Wrapper melalui terminal:

```bash
./gradlew bundleRelease
```

Setelah proses selesai, file AAB yang telah ditandatangani akan berada di direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## Langkah 4: Konfigurasi Pengujian Internal di Google Play Console

Pengujian Internal (Internal Testing) adalah cara tercepat untuk mendistribusikan aplikasi AI Anda kepada maksimal 100 tester terpilih tanpa perlu menunggu proses review Google Play Store yang memakan waktu berhari-hari.

### 1. Membuat Rilis Internal Baru
1. Masuk ke [Google Play Console](https://play.google.com/console/).
2. Pilih aplikasi Anda, lalu navigasikan ke menu **Testing > Internal testing** di sidebar kiri.
3. Klik tombol **Create new release** di pojok kanan atas.

### 2. Mengunggah File AAB
1. Tarik dan lepas (drag & drop) file `app-release.aab` yang telah Anda hasilkan ke area unggah.
2. Isi **Release name** (misal: `1.0.0 (1) - Gemini Integration Beta`).
3. Tulis catatan rilis singkat di kolom **Release notes** untuk memberi tahu tester fitur AI apa saja yang perlu diuji.
4. Klik **Save as draft**, lalu klik **Next** dan **Save**.

### 3. Mengelola Daftar Tester (Email List)
1. Pindah ke tab **Testers** di bagian atas halaman Internal Testing.
2. Di bawah bagian *Email lists*, klik **Create email list**.
3. Buat daftar baru (misal: "Tim QA Internal"), masukkan alamat email tester (akun Google mereka), lalu klik **Save**.
4. Centang daftar email yang baru saja dibuat untuk mengaitkannya dengan rilis ini.
5. Salin **Join on the web** atau **Join on Android** link yang disediakan di bagian bawah halaman. Bagikan link ini kepada tester Anda agar mereka dapat memberikan persetujuan (opt-in) untuk mengunduh aplikasi langsung dari Google Play Store mereka.

---

## Menjembatani Celah: Dari Prototipe AI ke Produk Siap Pasar

Meskipun panduan di atas memberikan langkah-langkah teknis mendasar untuk melakukan *compile* dan distribusi AAB, realitas dalam membangun aplikasi AI kelas industri jauh lebih kompleks. Mengubah prototipe sederhana dari Google AI Studio menjadi aplikasi produksi yang sukses sering kali membentur tembok tinggi terkait infrastruktur DevOps dan arsitektur perangkat lunak.

Beberapa tantangan berat yang akan Anda hadapi meliputi:

*   **Keamanan API Tingkat Lanjut:** Menyimpan API Key di Android (bahkan menggunakan ProGuard dan Secrets Plugin) tetap memiliki celah kebocoran jika perangkat di-*root*. Solusi ideal membutuhkan arsitektur **Backend Proxy/BFF (Backend-for-Frontend)** agar API Key Gemini tetap berada di server aman Anda, bukan di sisi klien.
*   **Arsitektur Kode Bersih (Clean Architecture):** Mengintegrasikan *stream response* dari model AI tanpa membuat UI aplikasi *freeze* menuntut implementasi pola MVVM/MVI, Kotlin Coroutines, dan StateFlow yang sangat matang.
*   **Otomatisasi DevOps (CI/CD):** Menyiapkan pipa otomatisasi (seperti GitHub Actions atau GitLab CI) yang dapat melakukan *build* otomatis, menjalankan pengujian unit, memperbarui nomor versi, dan langsung mengunggah AAB ke Google Play Console setiap kali ada perubahan kode.
*   **Pengamanan Keystore:** Mengelola kredensial penandatanganan aplikasi secara aman di cloud tanpa mengeksposnya ke publik.

Bagi para *founder* startup, pemilik bisnis, atau bahkan tim developer yang kekurangan sumber daya spesifik di bidang mobile DevOps, mencoba menyelesaikan semua kompleksitas ini sendiri sering kali berujung pada penundaan rilis berminggu-minggu, kebocoran kuota API yang mahal, atau aplikasi yang ditolak oleh Google Play Store karena masalah kebijakan keamanan data.

Menggunakan jasa ahli DevOps Android dan Pengembang Arsitektur Aplikasi profesional adalah langkah investasi strategis terbaik. Dengan menyerahkan konfigurasi teknis tingkat lanjut, manajemen *pipeline* CI/CD, hingga audit keamanan kode kepada ahlinya, Anda dapat menghemat ratusan jam kerja yang berharga. Fokuskan energi Anda pada apa yang paling penting: menyempurnakan fitur AI yang unik, merancang retensi pengguna, dan mengembangkan bisnis Anda ke tingkat berikutnya.