---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-10-06"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Artificial Intelligence (AI) ke dalam aplikasi mobile kini bukan lagi sekadar tren, melainkan kebutuhan fungsional. Menggunakan model LLM seperti Gemini melalui **Google AI Studio** memungkinkan developer menghadirkan fitur pintar langsung di genggaman pengguna. Namun, tantangan terbesar bukanlah saat menulis kode integrasi AI di lokal, melainkan saat Anda harus memaketkan aplikasi tersebut ke dalam format **Android App Bundle (AAB)** dan mendistribusikannya secara aman melalui **Google Play Console**.

Aplikasi AI memiliki karakteristik unik: ketergantungan SDK yang sensitif, kebutuhan *latency* yang rendah, dan yang paling krusial adalah keamanan **API Key**. 

Artikel ini akan membahas langkah demi langkah secara mendalam untuk menyusun AAB yang optimal, mengamankan API Key Gemini, hingga melakukan pengujian lewat jalur *Internal Testing* di Google Play Console.

---

## 1. Mengamankan API Key Gemini (Google AI Studio) untuk Produksi

Kesalahan fatal yang sering dilakukan developer pemula adalah melakukan *hardcode* API Key langsung di dalam file `MainActivity.kt` atau menyimpannya di file kontrol versi (`Git`). Untuk aplikasi AI tingkat produksi, API Key harus disembunyikan menggunakan **Secrets Gradle Plugin for Android**.

### Langkah 1: Instalasi Plugin Secrets
Tambahkan plugin ke file `build.gradle.kts` tingkat proyek (project-level):

```kotlin
// build.gradle.kts (Project)
plugins {
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

Terapkan plugin di file `build.gradle.kts` tingkat modul (app-level):

```kotlin
// build.gradle.kts (Module: app)
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}
```

### Langkah 2: Menyimpan API Key di `local.properties`
Tambahkan API Key Anda yang didapatkan dari Google AI Studio ke dalam file `local.properties` di direktori root proyek Anda (pastikan file ini masuk dalam `.gitignore`):

```properties
GEMINI_API_KEY=AIzaSyD-YourActualGeminiApiKeyHere...
```

### Langkah 3: Mengakses API Key di Kode Kotlin
Plugin secara otomatis akan menghasilkan variabel di dalam kelas `BuildConfig`. Anda dapat memanggilnya dengan aman tanpa takut bocor ke repositori publik:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel

class AiRepository {
    fun getGeminiModel(): GenerativeModel {
        // Mengambil API Key dari BuildConfig yang aman
        val apiKey = BuildConfig.GEMINI_API_KEY
        
        return GenerativeModel(
            modelName = "gemini-1.5-pro",
            apiKey = apiKey
        )
    }
}
```

---

## 2. Mengonfigurasi Build Variant dan Menyusun Android App Bundle (AAB)

Android App Bundle (AAB) adalah format rilis resmi Google Play yang menawarkan *Dynamic Delivery*. Dengan AAB, Google Play akan membuat APK yang dioptimalkan sesuai dengan konfigurasi perangkat pengguna, sehingga ukuran unduhan menjadi jauh lebih kecil.

### Langkah 1: Optimasi R8/ProGuard untuk SDK AI
Karena SDK Google AI menggunakan refleksi dan serialisasi data, Anda harus memastikan proses obfuskasi kode (R8) tidak merusak dependensi AI. Tambahkan aturan berikut pada file `proguard-rules.pro`:

```pro
# Mempertahankan kelas SDK Google AI Studio
-keep class com.google.ai.client.generativeai.** { *; }
-keep interface com.google.ai.client.generativeai.** { *; }

# Jika Anda menggunakan Kotlin Serialization atau Gson untuk parsing response AI
-keepattributes Signature, InnerClasses, EnclosingMethod
```

### Langkah 2: Konfigurasi Signing Configs di `build.gradle.kts`
Pastikan rilis Anda ditandatangani dengan kunci rilis (*Keystore*) yang aman.

```kotlin
// build.gradle.kts (Module: app)
android {
    ...
    defaultConfig {
        applicationId = "com.devops.aiapp"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("KEYSTORE_PATH") ?: "release.keystore")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = System.getenv("KEY_ALIAS")
            keyPassword = System.getenv("KEY_PASSWORD")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

### Langkah 3: Menghasilkan File AAB (Bundle)
Jalankan perintah Gradle berikut melalui terminal Android Studio untuk mengompilasi proyek menjadi format `.aab`:

```bash
./gradlew bundleRelease
```
Setelah proses selesai, file AAB Anda akan berada di direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## 3. Setup Google Play Console & Pengujian Internal (*Internal Testing*)

Jalur *Internal Testing* adalah cara tercepat untuk mendistribusikan aplikasi Anda kepada tim internal (hingga 100 penguji) tanpa harus menunggu proses peninjauan (*review*) kebijakan Google Play yang ketat untuk jalur produksi.

```
       +---------------------------------------------+
       |   Generate AAB (Android App Bundle)         |
       +----------------------++----------------------+
                              ||
                              \/
       +---------------------------------------------+
       |   Upload to Google Play Console             |
       +----------------------++----------------------+
                              ||
                              \/
       +---------------------------------------------+
       |   Add Testers Emails to Internal Track      |
       +----------------------++----------------------+
                              ||
                              \/
       +---------------------------------------------+
       |   Distribute via Play Store Link            |
       +---------------------------------------------+
```

### Langkah 1: Membuat Aplikasi di Play Console
1. Masuk ke [Google Play Console](https://play.google.com/console/).
2. Klik **Buat Aplikasi** (Create App).
3. Isi detail dasar seperti Nama Aplikasi, Bahasa Default, dan jenis aplikasi (Aplikasi atau Game).

### Langkah 2: Mengunggah AAB ke Jalur Pengujian Internal
1. Pada menu sebelah kiri, navigasikan ke **Rilis** > **Pengujian internal** (Testing > Internal testing).
2. Klik **Buat rilis baru** (Create new release).
3. Jika diminta untuk mengaktifkan *Play App Signing*, pilih rekomendasi Google (ini wajib agar Google Play dapat mengelola kunci penandatanganan Anda).
4. Tarik dan lepas (*drag and drop*) file `app-release.aab` yang telah Anda buat sebelumnya.
5. Isi nama rilis dan catatan rilis (misalnya: *"Initial release with Gemini API integration"*).
6. Klik **Simpan dan Tinjau Rilis**.

### Langkah 3: Mengelola Penguji Internal
1. Di dalam tab Pengujian Internal, pilih tab **Penguji** (Testers).
2. Buat daftar email baru (masukkan alamat email Google para penguji Anda).
3. Centang daftar email tersebut untuk memberikan akses.
4. Salin **Tautan Gabung** (Join link) yang disediakan di bagian bawah halaman. Bagikan tautan ini kepada penguji Anda agar mereka dapat mengunduh aplikasi langsung dari Google Play Store.

---

## 4. Checklist Pengujian Khusus untuk Aplikasi AI

Saat menguji aplikasi AI di jalur internal, berikan perhatian khusus pada metrik berikut:

* **Penanganan Latensi & Loading State:** Koneksi API ke LLM membutuhkan waktu beberapa detik. Pastikan *Shimmer effect* atau *Progress Bar* berjalan lancar tanpa membuat UI aplikasi membeku (*ANR - Application Not Responding*).
* **Skenario Tanpa Koneksi (Offline Fallback):** Matikan internet pada perangkat penguji. Pastikan aplikasi menampilkan pesan error yang ramah pengguna, bukan langsung *crash*.
* **Penanganan Limitasi Token (Rate Limit):** Pastikan aplikasi Anda mampu menangani error HTTP `429 (Too Many Requests)` secara elegan jika kuota gratis Google AI Studio Anda habis.

---

## Menghadapi Kompleksitas DevOps Android untuk AI

Mengembangkan fungsionalitas kecerdasan buatan langsung di Google AI Studio memang terlihat sangat menyenangkan dan instan. Namun, ketika Anda harus melangkah ke fase DevOps—mengonfigurasi variabel lingkungan Gradle yang rumit, mengamankan arsitektur enkripsi agar API Key tidak dicuri kompetitor, melakukan de-obfuskasi kode dengan Proguard, hingga menavigasi labirin kebijakan rilis Google Play Console yang terus berubah—proses ini sering kali berubah menjadi mimpi buruk teknis yang menyita waktu berhari-hari. 

Satu kesalahan kecil dalam konfigurasi penandatanganan rilis (*Release Signing*) atau manajemen dependensi Gradle dapat menyebabkan *build failure* yang sulit didiagnosis, atau bahkan penolakan aplikasi oleh tim peninjau Google Play. Bagi developer mandiri maupun tim startup yang ingin bergerak cepat ke pasar, mengalokasikan energi untuk urusan infrastruktur rilis ini sering kali mengalihkan fokus utama dari penyempurnaan produk AI itu sendiri.