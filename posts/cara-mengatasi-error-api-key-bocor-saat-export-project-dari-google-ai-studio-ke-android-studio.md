---
title: "Cara Mengatasi Error API Key Bocor saat Export Project dari Google AI Studio ke Android Studio"
date: "2026-10-21"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Fitur **Export Code** di Google AI Studio sangat memudahkan developer untuk mengubah *prompt* Gemini menjadi aplikasi Android siap pakai. Hanya dalam beberapa klik, Anda mendapatkan kerangka proyek Kotlin yang siap dibuka di Android Studio.

Namun, kendala klasik yang sering ditemui developer—terutama saat pertama kali melakukan *export*—adalah kemunculan peringatan atau error **"API Key Leaked"** (API Key Bocor). Peringatan ini bisa datang dari Google Cloud Console, sistem deteksi rahasia GitHub, atau pembatalan *build* otomatis oleh Android Gradle Plugin.

Artikel ini akan mengulas mengapa masalah ini terjadi dan memberikan panduan langkah demi langkah untuk mengamankan API key Gemini Anda dengan benar di Android Studio.

---

## Mengapa Error API Key Bocor Bisa Terjadi?

Saat Anda mengunduh atau mengespor proyek dari Google AI Studio, kode templat sering kali menempatkan API key secara langsung (*hardcoded*) di dalam file seperti `BuildConfig.kt`, `MainActivity.kt`, atau `AndroidManifest.xml`.

```kotlin
// contoh praktik BERBAHAYA yang dihasilkan dari export langsung:
val apiKey = "AIzaSyD-EXAMPLE_KEY_123456789" // Key tertanam langsung di source code
val generativeModel = GenerativeModel(
    modelName = "gemini-1.5-flash",
    apiKey = apiKey
)
```

Praktik *hardcoding* ini memicu bahaya keamanan:
1. **Repository Git Publik:** Jika proyek di-push ke GitHub/GitLab, bot pemindai akan langsung mendeteksi API key tersebut dan Google akan otomatis menonaktifkan key Anda karena dianggap telah bocor.
2. **Reverse Engineering:** Seseorang dapat me-decompile file APK Anda dan mengekstrak API key dengan mudah menggunakan tool seperti APKTool.

---

## Langkah Praktis Mengatasi dan Mengamankan API Key

Berikut adalah alur kerja *DevOps/Android Development* standar industri untuk mengatasi error ini secara permanen.

### Langkah 1: Revoke (Cabut) API Key yang Telah Bocor

Jangan gunakan kembali API key yang sudah terlanjur mendapatkan peringatan bocor.

1. Buka [Google AI Studio](https://aistudio.google.com/) atau **Google Cloud Console**.
2. Masuk ke menu **API & Services > Credentials**.
3. Temukan API key yang terindikasi bocor, lalu klik **Delete** atau **Revoke**.
4. Buat API key baru, namun **jangan masukkan key ini ke dalam kode secara langsung**.

---

### Langkah 2: Simpan API Key di `local.properties`

File `local.properties` berada di direktori akar proyek Android Anda. File ini secara *default* sudah terdaftar di dalam `.gitignore`, sehingga tidak akan pernah ikut terunggah ke repositori Git.

Buka file `local.properties` di Android Studio dan tambahkan baris berikut:

```properties
# local.properties
sdk.dir=/Users/username/Library/Android/sdk
GEMINI_API_KEY=AIzaSy_GANTI_DENGAN_API_KEY_BARU_ANDA
```

---

### Langkah 3: Gunakan Secrets Gradle Plugin untuk Android

Google menyediakan plugin resmi bernama **Secrets Gradle Plugin for Android** untuk membaca variabel dari `local.properties` secara aman dan menginjeksikannya ke dalam variabel `BuildConfig` saat proses kompilasi.

#### 1. Tambahkan Plugin ke `build.gradle.kts` (Project Level)

Buka file `build.gradle.kts` tingkat proyek (Root) dan tambahkan *dependency* plugin:

```kotlin
// build.gradle.kts (Project)
plugins {
    // Plugin lainnya...
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

#### 2. Terapkan Plugin di `build.gradle.kts` (App Level)

Buka file `build.gradle.kts` tingkat modul (`app`) dan aktifkan plugin tersebut:

```kotlin
// build.gradle.kts (Module :app)
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}

android {
    namespace = "com.example.appgemini"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.appgemini"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Pastikan fitur buildConfig diaktifkan
    buildFeatures {
        buildConfig = true
    }
}
```

Lakukan **Sync Project with Gradle Files**. Plugin ini akan membaca `GEMINI_API_KEY` dari `local.properties` dan secara otomatis membuat variabel `BuildConfig.GEMINI_API_KEY`.

---

### Langkah 4: Panggil API Key dari `BuildConfig` di Kode Kotlin

Sekarang, ubah kode inisialisasi SDK Gemini di aplikasi Anda agar mengambil key dari `BuildConfig`:

```kotlin
package com.example.appgemini

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.google.ai.client.generativeai.GenerativeModel

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Mengambil API Key dengan aman dari BuildConfig
        val apiKey = BuildConfig.GEMINI_API_KEY

        val generativeModel = GenerativeModel(
            modelName = "gemini-1.5-flash",
            apiKey = apiKey
        )

        // Lanjutkan logika pemanggilan AI...
    }
}
```

Dengan metode ini, API key Anda tidak lagi tertulis sebagai teks biasa di dalam repositori kode.

---

### Langkah 5: Batasi Penggunaan API Key (API Restriction)

Untuk lapisan keamanan ekstra (terutama jika aplikasi akan dirilis ke Google Play Store), batasi hak akses API key Anda di Google Cloud Console:

1. Buka **Google Cloud Console** > **Credentials**.
2. Pilih API Key Anda, lalu masuk ke bagian **Set an application restriction**.
3. Pilih **Android apps**.
4. Masukkan **Package Name** aplikasi Anda (misal: `com.example.appgemini`) dan **SHA-1 fingerprint** dari *keystore* Anda (baik Debug maupun Release).

```bash
# Cara mendapatkan SHA-1 Key Debug via terminal:
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
```

---

## Kompleksitas Mengamankan Aplikasi AI hingga Siap Rilis

Mengatasi error API Key pada fase eksplorasi lokal menggunakan `local.properties` memang menyelesaikan masalah jangka pendek. Namun, ketika Anda berencana membawa aplikasi Android berbasis Google AI Studio ini ke tingkat produksi (*production-ready*), lanskap teknisnya menjadi jauh lebih rumit.

Bagi pemula maupun tim pengembang yang mengejar tenggat waktu, mengonfigurasi arsitektur keamanan dan alur alur kerja DevOps secara mandiri sering kali memicu kebingungan baru:

- **Risiko Dekompilasi APK:** Variabel di `BuildConfig` tetap dapat di-extract menggunakan teknik *static analysis* lanjutan jika tidak dikombinasikan dengan pembungkusan NDK/C++ atau teknik *obfuscation* ProGuard/R8 yang tepat.
- **Arsitektur Backend Proxy:** Untuk standar keamanan tertinggi, API Key Gemini sebenarnya tidak boleh ada di sisi klien (aplikasi Android) sama sekali, melainkan harus dipanggil melalui perantara *Backend Server* / *Cloud Functions* (Firebase/GCP).
- **Pengelolaan Multi-Environment:** Mengatur kuisisi API Key yang berbeda antara lingkungan *Development*, *Staging*, dan *Production* pada pipeline CI/CD (GitHub Actions/GitLab CI) membutuhkan pemahaman mendalam tentang *build flavors* Gradle dan *secret management*.

Konfigurasi dari sekadar kodingan *prototype* Google AI Studio hingga menjadi aplikasi yang aman, stabil, serta memenuhi standar keamanan industri memerlukan ketelitian arsitektur yang matang agar data dan anggaran API Anda terhindar dari penyalahgunaan pihak tidak bertanggung jawab.

---

## Kesimpulan

Error API Key bocor saat melakukan *export project* dari Google AI Studio bukanlah bug, melainkan mekanisme perlindungan otomatis agar kredensial cloud Anda tidak disalahgunakan. Dengan memindahkan key ke file `local.properties`, menggunakan *Secrets Gradle Plugin*, serta menerapkan pembatasan SHA-1 di Google Cloud Console, proyek Android Anda kini jauh lebih aman dan profesional.