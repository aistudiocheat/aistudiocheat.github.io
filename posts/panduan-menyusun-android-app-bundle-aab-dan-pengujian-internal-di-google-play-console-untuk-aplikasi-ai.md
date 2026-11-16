---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-11-16"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan kecerdasan buatan (AI) seperti **Gemini API** dari **Google AI Studio** ke dalam aplikasi Android menawarkan potensi besar untuk menciptakan fitur-fitur yang responsif dan cerdas. Namun, alur kerja dari *prototyping* hingga aplikasi siap edar memiliki tantangan tersendiri—mulai dari tata kelola kunci API (*API Key*), optimasi ukuran *binary*, hingga mekanisme distribusi yang aman.

Sebagai pengembang atau tim DevOps, Anda tidak lagi disarankan mengunggah format APK tradisional ke Google Play Store. Google menetapkan **Android App Bundle (AAB)** sebagai standar resmi. 

Artikel ini memuat panduan teknis mendalam tentang cara menyusun berkas AAB yang teroptimasi untuk aplikasi berbasis AI dan mendistribusikannya melalui jalur **Pengujian Internal (Internal Testing)** di Google Play Console.

---

## 1. Amankan API Key Google AI Studio Sebelum Processing Build

Tantangan utama pada aplikasi AI client-side adalah perlindungan kredensial. Jangan pernah menyalin (*hardcode*) API Key Gemini langsung di dalam kode Kotlin/Java atau menyimpan berkas `JSON` rahasia di direktori `assets`.

### Menggunakan Secrets Gradle Plugin
Pendekatan arsitektur terbaik adalah memanfaatkan `secrets-gradle-plugin` agar API Key tersimpan di `local.properties` dan dibaca sebagai variabel `BuildConfig`.

1. Tambahkan dependensi plugin di `build.gradle.kts` (Project Level):

```kotlin
// build.gradle.kts (Project Level)
plugins {
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

2. Terapkan plugin di `build.gradle.kts` (Module Level):

```kotlin
// build.gradle.kts (Module Level / app)
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}

android {
    namespace = "com.example.aiapplication"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.aiapplication"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    
    buildFeatures {
        buildConfig = true
    }
}
```

3. Isikan API Key Anda di berkas `local.properties` (berkas ini **harus** masuk ke `.gitignore`):

```properties
# local.properties
GEMINI_API_KEY=AIzaSyD-EXAMPLE_KEY_GOOGLE_AI_STUDIO
```

4. Panggil variabel dalam kode Kotlin:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel

class AIService {
    private val apiKey = BuildConfig.GEMINI_API_KEY
    
    private val generativeModel = GenerativeModel(
        modelName = "gemini-1.5-flash",
        apiKey = apiKey
    )

    suspend fun generateResponse(prompt: String): String? {
        val response = generativeModel.generateContent(prompt)
        return response.text
    }
}
```

---

## 2. Optimasi ProGuard/R8 untuk SDK AI dan Format AAB

Aplikasi berbasis AI sering kali membawa dependensi yang cukup berat seperti `kotlinx.serialization`, `gRPC`, `OkHttp`, atau library pemrosesan data lokal (seperti TFLite). Saat mengompilasi menjadi AAB, *code shrinking* dan *obfuscation* R8 dapat merusak pemanggilan metode refleksif jika aturan ProGuard tidak dikonfigurasi dengan tepat.

Tambahkan konfigurasi berikut pada berkas `proguard-rules.pro` Anda:

```proguard
# Keeping Google AI SDK & gRPC Components
-keep class com.google.ai.client.generativeai.** { *; }
-dontwarn com.google.ai.client.generativeai.**

# Serialization Rules (Retrofit / KotlinX Serialization)
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod
-keepclassmembers class * {
    @kotlinx.serialization.SerialName <fields>;
}

# OkHttp Rules (digunakan oleh HTTP Client SDK AI)
-dontwarn okhttp3.internal.platform.**
-keepclassmembers class okhttp3.internal.sslsocket.Http2ExchangeCodec { *; }
```

Aktifkan *shrinking* pada `build.gradle.kts` bagian `buildTypes`:

```kotlin
buildTypes {
    release {
        isMinifyEnabled = true
        isShrinkResources = true
        proguardFiles(
            getDefaultProguardFile("proguard-android-optimize.txt"),
            "proguard-rules.pro"
        )
    }
}
```

---

## 3. Membuat Signed Android App Bundle (AAB)

Format AAB memungkinkan Google Play menggunakan *Dynamic Delivery*, yang artinya pengguna hanya mengunduh kode dan aset (*locale*, resolusi layar, arsitektur CPU seperti `arm64-v8a`) yang cocok untuk perangkat mereka. Ini sangat penting untuk menjaga ukuran *installer* aplikasi AI tetap ramah kuota.

### Membuat Signed AAB via Command Line (CI/CD Ready)
Jika Anda menggunakan pipeline DevOps atau baris perintah, buat *Keystore* dan jalankan skrip build Gradle.

```bash
# Command membuat keystore (jika belum ada)
keytool -genkey -v -keystore my-ai-app-key.jks -keyalg RSA \
-keysize 2048 -validity 10000 -alias my-key-alias

# Jalankan kompilasi AAB Release
./gradlew bundleRelease
```

Hasil akhir berkas AAB akan tersimpan di direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## 4. Konfigurasi Pengujian Internal (Internal Testing) di Google Play Console

Jalur *Internal Testing* adalah mekanisme tercepat untuk membagikan aplikasi ke hingga 100 orang penguji (*testers*) tanpa harus melewati proses peninjauan (*review*) ketat dari tim Google Play yang memakan waktu lama.

### Langkah 1: Buat Aplikasi Baru & Pilih Track
1. Masuk ke **Google Play Console**.
2. Pilih **Create app**, isi nama aplikasi, bahasa default, dan deklarasikan aplikasi sebagai *Free* atau *Paid*.
3. Pada menu navigasi sebelah kiri, buka bagian **Testing** > **Internal testing**.

### Langkah 2: Buat Daftar Penguji (Testers List)
1. Pilih tab **Testers**.
2. Klik **Create email list**, beri nama daftar (misal: *Tim QA & Developer AI*).
3. Masukkan alamat Gmail para penguji, lalu simpan.
4. Pastikan centang daftar email tersebut pada halaman pengujian internal.

### Langkah 3: Rilis Rilis Baru (Create New Release)
1. Di halaman *Internal testing*, klik **Create new release**.
2. Unggah berkas `app-release.aab` yang telah disiapkan.
3. Tunggu hingga sistem Google Play memproses metadata AAB (pemeriksaan *Package Name*, *Version Code*, dan struktur modul).
4. Isi **Release notes** untuk memberi tahu penguji mengenai pembaruan fitur (misalnya: *"Integrasi prompt Gemini API v1.5 Flash"*).
5. Klik **Save**, lalu pilih **Next** / **Review release**, dan klik **Start rollout to Internal testing**.

---

## 5. Menguji Aplikasi AI di Perangkat Target

Setelah status rilis berubah menjadi *Available internal*, penguji yang terdaftar harus menerima tautan unduhan:

1. Salin tautan pada bagian **How testers join** (misal: `https://play.google.com/apps/testing/com.example.aiapplication`).
2. Kirim tautan ke penguji. Penguji wajib membuka tautan tersebut, memilih **Accept the invitation**, lalu mengunduh aplikasi langsung dari Google Play Store.
3. **Validasi Integrasi AI**: Pastikan aplikasi terkoneksi ke jaringan, pengujian batasan *rate limit* Gemini API berjalan normal, dan tidak terjadi *crash* akibat aturan Obfuscation/R8 pada paket native.

---

## Kompleksitas Rantai Kerja DevOps Android & Integrasi AI

Menyusun arsitektur aplikasi berbasis Google AI Studio dari tahap *prototype* hingga menjadi produk yang stabil di Google Play Console bukanlah proses yang instan. 

Bagi pengembang indie, pendiri startup, maupun tim internal yang berfokus pada inovasi produk, mengurus berbagai konfigurasi teknis—mulai dari tata kelola *Keystore*, penyusunan `proguard-rules`, penanganan enkripsi kredensial API, *Dynamic Delivery* AAB, hingga penyesuaian regulasi *Play Integrity API* dan alur pengujian internal—sering kali menguras waktu serta sumber daya teknis.

Jika konfigurasi build tidak tepat, Anda dapat mengalami kendala seperti *API Key leak*, kegagalan serialisasi data AI saat *runtime release*, hingga penolakan berkas oleh sistem Google Play. Memastikan setiap aspek DevOps dan kepatuhan sistem berjalan selaras membutuhkan presisi dan pemahaman mendalam atas ekosistem Android modern.

---

## Kesimpulan

Menyusun Android App Bundle (AAB) dan memanfaatkannya melalui saluran Pengujian Internal Google Play Console adalah pendekatan standar industri untuk mendistribusikan aplikasi AI dengan cepat, aman, dan efisien. Dengan memisahkan variabel lingkungan rahasia, mengoptimalkan aturan ProGuard untuk library AI, dan mengisolasi tahap pengujian, Anda dapat memastikan bahwa produk AI Anda siap dipasarkan dengan kualitas teknis terbaik.