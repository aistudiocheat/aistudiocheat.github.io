---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-11-11"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Perkembangan teknologi kecerdasan buatan (AI) yang masif membuat integrasi *Large Language Models* (LLM) seperti Gemini API dari Google AI Studio ke dalam aplikasi Android semakin populer. Namun, mendeploy aplikasi berbasis AI memiliki tantangan tersendiri: ukuran dependensi SDK yang membengkak, perlindungan API Key agar tidak bocor, hingga konfigurasi obfuscation yang berisiko merusak *data model* parsing JSON AI.

Menggunakan format legacy APK untuk distribusi produksi sudah tidak direkomendasikan dan telah digantikan oleh **Android App Bundle (AAB)**. Dengan AAB, Google Play akan membuatkan APK yang dioptimalkan sesuai dengan konfigurasi perangkat pengguna (*split APKs*), sehingga ukuran unduhan menjadi jauh lebih kecil.

Artikel ini memandu Anda secara teknis dari tahap pengamanan kode, *build* AAB, hingga distribusi di **Internal Testing Google Play Console** khusus untuk aplikasi berbasis AI.

---

## Step 1: Amankan API Key Google AI Studio di Tingkat Build

Kesalahan paling fatal yang sering dilakukan pengembang adalah menaruh API Key Gemini secara *hardcoded* di dalam kode Kotlin/Java. Kunci ini mudah diekstrak menggunakan teknik *reverse engineering* (dekompilasi APK).

Gunakan **Secrets Gradle Plugin** atau baca variabel dari `local.properties`:

### 1. Tambahkan API Key di `local.properties`
```properties
# local.properties (Jangan pernah di-commit ke Git)
GEMINI_API_KEY=AIzaSyYourSecretKeyFromGoogleAIStudio
```

### 2. Konfigurasi `build.gradle.kts` (Module :app)
Pastikan fitur `buildConfig` diaktifkan untuk membaca variabel dari `local.properties`:

```kotlin
import java.util.Properties

val localProperties = Properties()
val localPropertiesFile = rootProject.file("local.properties")
if (localPropertiesFile.exists()) {
    localProperties.load(localPropertiesFile.inputStream())
}

android {
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.ai.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        // Menyuntikkan API Key ke BuildConfig secara aman
        val apiKey = localProperties.getProperty("GEMINI_API_KEY") ?: ""
        buildConfigField("String", "GEMINI_API_KEY", "\"$apiKey\"")
    }

    buildFeatures {
        buildConfig = true
    }
}
```

---

## Step 2: Konfigurasi Optimization & ProGuard Rules untuk SDK AI

SDK AI seperti `google-genai` atau perpustakaan pendukung (*OkHttp*, *Retrofit*, *Moshi/Gson*, *Protobuf*) sering menggunakan refleksi (*reflection*). Jika *R8/ProGuard* mengecilkan (*shrink*) atau mengacak (*obfuscate*) kelas ini tanpa aturan yang benar, aplikasi AI Anda akan *crash* saat melakukan parsing *response* dari server.

Buka file `proguard-rules.pro` dan tambahkan aturan khusus berikut:

```proguard
# Menjaga Data Class parsing JSON untuk Gemini API
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Menjaga kelas model internal SDK AI agar tidak ter-obfuscate
-keep class com.google.ai.client.generativeai.** { *; }
-keep interface com.google.ai.client.generativeai.** { *; }

# Jika Anda menggunakan Kotlin Coroutines & Flow untuk streaming teks AI
-keepclassmembers class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**

# Protobuf (yang umum digunakan di SDK Google AI)
-keepclassmembers class * extends com.google.protobuf.GeneratedMessageLite {
    <fields>;
}
```

---

## Step 3: Membuat Signed Android App Bundle (AAB)

Langkah selanjutnya adalah membuat berkas `.aab` yang telah ditandatangani (*signed*) menggunakan Keystore produksi atau staging Anda.

### 1. Generate Keystore via Terminal (Opsional)
Jika Anda belum memiliki Keystore, buat melalui CLI:

```bash
keytool -genkey -v -keystore my-ai-app-key.jks \
  -alias my-ai-alias -keyalg RSA -keysize 2048 -validity 10000
```

### 2. Build AAB via Gradle Command Line
Jalankan perintah Gradle berikut di terminal proyek Anda untuk membuat berkas release:

```bash
# Untuk Linux / macOS
./gradlew bundleRelease

# Untuk Windows PowerShell
.\gradlew bundleRelease
```

Hasil berkas AAB dapat ditemukan pada direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## Step 4: Mengonfigurasi Pengujian Internal (Internal Testing) di Google Play Console

Jalur *Internal Testing* adalah cara tercepat untuk mendistribusikan aplikasi kepada tim QA atau *beta tester* (hingga 100 akun) tanpa melalui proses peninjauan (*review*) aplikasi yang ketat dari Google.

### Langkah-langkah Pengaturan:

1. **Buka Google Play Console** dan pilih aplikasi Anda.
2. Pada menu bilah samping (*sidebar*), buka **Testing** > **Internal testing**.
3. Klik tombol **Create new release** di pojok kanan atas.
4. **Upload File AAB**: Unggah berkas `app-release.aab` yang telah di-*build*.
5. **Set Up App Signing**: Pilih **Use Google-generated key** jika ini pertama kali Anda mengunggah aplikasi. Google Play akan mengelola kunci penandatanganan aplikasi secara aman.
6. **Isi Release Notes**: Berikan catatan perubahan, misalnya: *"Integrasi Gemini API streaming response dan perbaikan bug UI chat."*
7. Klik **Save** lalu **Next**, kemudian **Start rollout to Internal testing**.

---

## Step 5: Menambahkan Penguji Internal & Konfigurasi SHA-256 GCP

Agar penguji dapat mengunduh aplikasi dan fungsi AI berjalan lancar:

### 1. Tambahkan Daftar Penguji (Testers)
* Buka tab **Testers** di menu Internal Testing.
* Buat *Email List* baru dan masukkan alamat email Google para penguji.
* Salin **Join on the web** atau **Join on Android** link dan bagikan ke tim Anda.

### 2. PENTING: Mendaftarkan SHA-256 Play App Signing ke Google Cloud Console
Ketika Anda mengunggah AAB, Google Play akan menandatangani ulang APK penguji menggunakan kunci *App Signing*. Jika Gemini API Key Anda dibatasi (*restricted*) berdasarkan *Package Name* dan *SHA-256 Fingerprint*, Anda **WAJIB** mendaftarkan fingerprint dari Play Console ke GCP:

1. Di Play Console, buka **Setup** > **App Integrity**.
2. Salin **SHA-256 certificate fingerprint** di bagian *App signing key certificate*.
3. Buka **Google Cloud Console** > **APIs & Services** > **Credentials**.
4. Edit API Key yang Anda gunakan untuk Google AI Studio.
5. Tambahkan restriction **Android apps**, masukkan *Package Name* dan *SHA-256 Fingerprint* dari Play Console tadi.

---

## Tantangan & Kompleksitas Pipeline Rilis Aplikasi AI

Mengonfigurasi aplikasi Android dari tahap purwarupa *Google AI Studio* hingga menjadi versi yang siap masuk ke jalur produksi sebenarnya menyimpan banyak kendala teknis yang tersembunyi. Bagi pemula maupun tim yang terbiasa fokus pada pengembangan *frontend*, pengelolaan rantai *DevOps* seluler ini sering kali menjadi hambatan besar.

Beberapa kendala rumit yang kerap ditemui antara lain:
* **Mismatch Certificate SHA-256**: API Key AI menolak merespons (*HTTP 403 Forbidden*) di HP penguji karena beda *fingerprint* antara *Debug Key*, *Upload Key*, dan *Play Signing Key*.
* **ProGuard Shrinking Regression**: Aplikasi berjalan mulus di *Debug mode*, tetapi mendadak *crash* saat di-*build* menjadi AAB *Release* akibat dependensi SDK AI yang terpotong oleh R8 compiler.
* **Pengelolaan CI/CD Automation**: Mengatur *GitHub Actions* atau *GitLab CI* untuk mengotomatisasi *build* AAB, pengujian unit, hingga otomatis *deploy* ke Google Play API tanpa mengekspos Keystore dan API Key secara ceroboh.
* **Dynamic Feature Modules**: Memisahkan modul library AI yang berat (*seperti TFLite model / ONNX Runtime*) menggunakan *Play Feature Delivery* agar ukuran awal pengunduhan aplikasi tetap ringan.

Proses konfigurasi ini membutuhkan ketelitian tinggi pada aspek keamanan, optimasi sistem, serta pemahaman mendalam tentang ekosistem Google Play Console dan Google Cloud Infrastructure.

---

## Kesimpulan

Menyusun Android App Bundle (AAB) dan menyalurkannya via pengujian internal Google Play Console adalah standar industri untuk menjamin kualitas aplikasi AI sebelum dilepas ke publik. Dengan mengamankan API key di level *build*, mengatur konfigurasi ProGuard secara pas, dan mendaftarkan SHA-256 Play Integrity dengan benar, aplikasi berbasis Gemini AI Anda akan berjalan stabil dan aman di berbagai perangkat penguji.