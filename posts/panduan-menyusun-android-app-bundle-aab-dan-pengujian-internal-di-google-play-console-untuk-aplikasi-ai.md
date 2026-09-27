---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-09-27"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan Large Language Model (LLM) seperti Gemini API melalui Google AI Studio ke dalam aplikasi Android adalah langkah awal yang revolusioner. Namun, menjembatani fase *prototype* di lokal hingga menjadi aplikasi siap produksi di Google Play Store membutuhkan pemahaman DevOps Android yang matang. 

Format **Android App Bundle (AAB)** kini menjadi standar wajib rilis di Google Play Store menggantikan APK konvensional karena menawarkan optimasi ukuran unduhan yang jauh lebih efisien. Bagi aplikasi berbasis AI, efisiensi ukuran dan keamanan *resource* adalah segalanya.

Artikel ini akan memandu Anda secara mendalam mengenai cara menyusun AAB yang aman, melakukan konfigurasi R8/Proguard khusus pustaka AI, hingga mendistribusikannya melalui jalur Pengujian Internal (Internal Testing) di Google Play Console.

---

## Langkah 1: Mengamankan API Key AI Studio pada Level Gradle

Sebelum membuat *build* produksi, pastikan API Key Google AI Studio (Gemini API) Anda tidak bocor ke dalam repositori publik (seperti GitHub) atau mudah didekompilasi melalui teknik *reverse engineering*.

### 1. Gunakan `local.properties`
Simpan API Key Anda di file `local.properties` yang terletak di root proyek Anda (pastikan file ini masuk ke dalam `.gitignore`):

```properties
# local.properties
GEMINI_API_KEY=AIzaSyYourActualSecureGeminiKeyHere
```

### 2. Konfigurasi `build.gradle.kts` (App Level)
Gunakan `secrets-gradle-plugin` atau baca langsung dari properti Gradle untuk menginjeksikannya ke dalam `BuildConfig`:

```kotlin
// build.gradle.kts (Module: app)
import java.util.Properties

val localProperties = Properties().apply {
    val localPropertiesFile = rootProject.file("local.properties")
    if (localPropertiesFile.exists()) {
        localPropertiesFile.inputStream().use { load(it) }
    }
}

android {
    namespace = "com.example.aiapp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.aiapp"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        // Injeksikan API Key ke BuildConfig
        val geminiKey = localProperties.getProperty("GEMINI_API_KEY") ?: ""
        buildConfigField("String", "GEMINI_API_KEY", "\"$geminiKey\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true // Aktifkan Proguard/R8
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    
    buildFeatures {
        buildConfig = true
    }
}
```

---

## Langkah 2: Konfigurasi Proguard/R8 Khusus SDK Google AI

Optimasi kode (minifikasi) sangat penting untuk memangkas ukuran AAB. Namun, pustaka serialisasi JSON dan HTTP client yang digunakan oleh SDK Google AI (seperti `com.google.ai.client.generativeai`) memerlukan aturan Proguard khusus agar tidak mengalami *crash* saat dijalankan di mode *release*.

Tambahkan aturan berikut pada file `proguard-rules.pro`:

```pro
# Mempertahankan anotasi yang digunakan oleh serialization/retrofit jika ada
-keepattributes Signature, InnerClasses, EnclosingMethod, Annotation

# Menjaga model data internal Google AI SDK dari obfuscation
-keep class com.google.ai.client.generativeai.type.** { *; }
-keep class com.google.ai.client.generativeai.api.** { *; }

# Jika Anda menggunakan Kotlin Serialization (sering digunakan bersama Gemini SDK)
-keepclassmembers class * {
    @kotlinx.serialization.SerialName <fields>;
}
-keep,unused class kotlinx.serialization.json.** { *; }
```

---

## Langkah 3: Membuat Android App Bundle (AAB)

Setelah konfigurasi build dan keamanan siap, saatnya melakukan kompilasi proyek menjadi format `.aab`.

### Melalui Android Studio (GUI):
1. Buka Android Studio, pilih menu **Build > Generate Signed Bundle / APK...**
2. Pilih **Android App Bundle** dan klik **Next**.
3. Pilih atau buat Keystore baru (simpan file `.jks` ini dengan aman, karena Anda membutuhkannya untuk setiap pembaruan aplikasi).
4. Pilih varian build **release**, tentukan folder output, lalu klik **Create**.

### Melalui Gradle Wrapper (CLI):
Jika Anda menggunakan sistem CI/CD (seperti GitHub Actions), jalankan perintah berikut di terminal proyek Anda:

```bash
./gradlew bundleRelease
```
File AAB yang dihasilkan akan berada di direktori: `app/build/outputs/bundle/release/app-release.aab`.

---

## Langkah 4: Mengunggah ke Jalur Pengujian Internal Google Play Console

Pengujian Internal adalah cara terbaik untuk menguji performa model AI Anda pada berbagai perangkat fisik tanpa perlu menunggu proses review publik yang memakan waktu lama.

### 1. Membuat Daftar Penguji (Tester)
1. Masuk ke [Google Play Console](https://play.google.com/console/).
2. Pilih aplikasi Anda, lalu navigasikan ke menu **Users and permissions > Groups** atau langsung ke menu **Setup > Email lists**.
3. Buat daftar email penguji internal Anda (maksimal 100 email per daftar).

### 2. Membuat Rilis Pengujian Internal
1. Pada menu navigasi kiri, di bawah bagian **Testing**, pilih **Internal testing**.
2. Klik tombol **Create new release** di pojok kanan atas.
3. Pada opsi **App integrity**, pastikan *Play App Signing* sudah aktif.
4. Tarik dan lepas (drag-and-drop) file `app-release.aab` yang telah Anda buat sebelumnya ke area unggah.
5. Isi **Release name** dan **Release notes** (misalnya: *"Initial release with Gemini API integration and R8 optimizations"*).
6. Klik **Next**, lalu pilih **Save and publish**.

### 3. Membagikan Link Pengujian
Setelah rilis dipublikasikan (proses ini biasanya instan atau memakan waktu kurang dari beberapa jam untuk pengujian internal), gulir ke bawah ke tab **Testers**. Salin tautan **Join on Android** atau **Join on the web** dan bagikan kepada tim penguji Anda.

---

## Tantangan Tersembunyi: Mengapa Jalur dari Google AI Studio ke Play Store Begitu Terjal?

Di atas kertas, langkah-langkah di atas terlihat sangat runut dan sederhana. Namun, realitas di lapangan sering kali berbeda, terutama bagi para pengembang atau tim yang baru pertama kali meluncurkan aplikasi berbasis kecerdasan buatan.

Mengonfigurasi proyek dari tahap eksperimen di Google AI Studio hingga menjadi aplikasi siap produksi di Google Play Console menyimpan kompleksitas yang sangat tinggi:

*   **Masalah Keamanan Kunci (API Exposure):** Sedikit kecerobohan dalam konfigurasi Gradle dapat menyebabkan API Key Gemini Anda bocor ke publik, yang berujung pada penyalahgunaan kuota dan tagihan yang membengkak.
*   **Kompatibilitas Runtime AI:** Model AI membutuhkan penanganan *asynchronous* yang intensif (seperti Kotlin Coroutines atau Flow). Ketika dikombinasikan dengan optimasi R8/Proguard, aplikasi sering kali mengalami *silent crash* (aplikasi tertutup tanpa pesan error yang jelas) pada perangkat tertentu karena *class* penting terhapus selama proses minifikasi.
*   **Kebijakan Konten AI Google Play:** Google menerapkan aturan yang sangat ketat terkait aplikasi yang menghasilkan konten berbasis AI (Generative AI). Kegagalan menyediakan fitur pelaporan konten yang tidak pantas (*User-Generated Content policy*) atau kegagalan konfigurasi fungsionalitas dasar saat pengujian internal dapat membuat aplikasi Anda langsung ditolak saat pengajuan produksi.
*   **Manajemen Keystore & Play Integrity:** Salah mengonfigurasi sertifikat penandatanganan aplikasi (*App Signing Key*) di Play Console dapat mengunci aplikasi Anda selamanya dari pembaruan di masa mendatang.

Bagi pemula atau tim fokus bisnis tanpa dedikasi staf DevOps Android khusus, mengatasi labirin konfigurasi Gradle, penyesuaian dependensi SDK, sertifikat rilis, hingga kepatuhan kebijakan Google Play Console ini sering kali menguras waktu berminggu-minggu yang seharusnya bisa dialokasikan untuk menyempurnakan fitur AI itu sendiri.