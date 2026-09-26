---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-09-26"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan kecerdasan buatan (AI) seperti Gemini API dari Google AI Studio ke dalam aplikasi Android adalah langkah revolusioner untuk menghadirkan fitur pintar yang interaktif. Namun, perjalanan dari fase *prototype* di local machine hingga aplikasi siap diunduh oleh pengguna di Google Play Store memiliki tantangan tersendiri.

Untuk merilis aplikasi modern, Google mewajibkan penggunaan format **Android App Bundle (AAB)** menggantikan APK tradisional. Selain itu, sebelum aplikasi Anda diakses oleh publik, Anda wajib melakukan **Pengujian Internal (Internal Testing)** untuk memastikan model AI berjalan optimal tanpa *crash* di berbagai perangkat.

Artikel ini akan membahas secara mendalam langkah-demi-langkah menyusun AAB yang aman, mengoptimalkan build untuk library AI, dan mengonfigurasi jalur pengujian internal di Google Play Console.

---

## 1. Amankan API Key Gemini Sebelum Membuat AAB

Sebelum melakukan kompilasi (compile) ke format AAB, aspek keamanan adalah hal yang paling krusial. Menyimpan API Key Google AI Studio secara *hardcoded* di dalam kode Kotlin/Java sangat berbahaya karena dapat diekstraksi melalui proses *reverse engineering*.

Gunakan **Secrets Gradle Plugin** untuk menyimpan API Key dengan aman di file `local.properties` (yang secara otomatis diabaikan oleh Git).

### Langkah 1: Konfigurasi `build.gradle` (Project Level)
Tambahkan plugin Secrets Gradle di file `build.gradle.kts` tingkat proyek:

```kotlin
plugins {
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

### Langkah 2: Konfigurasi `build.gradle` (Module App Level)
Terapkan plugin di file `build.gradle.kts` modul aplikasi Anda:

```kotlin
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}

android {
    // ... konfigurasi standar lainnya
}
```

### Langkah 3: Definisikan API Key di `local.properties`
Buka file `local.properties` di root direktori proyek Anda dan tambahkan baris berikut:

```properties
GEMINI_API_KEY=AIzaSyD_ContohApiKeyGeminiAndaYangSangatRahasia
```

Sekarang, Anda dapat mengakses key tersebut dengan aman dari manifes atau kode Kotlin menggunakan kelas `BuildConfig`:

```kotlin
val apiKey = BuildConfig.GEMINI_API_KEY
val generativeModel = GenerativeModel(
    modelName = "gemini-1.5-flash",
    apiKey = apiKey
)
```

---

## 2. Optimalisasi ProGuard dan R8 untuk SDK AI

SDK Google AI Client sering kali menggunakan proses serialisasi data (seperti JSON/Protobuf) dan refleksi (*reflection*) di balik layar. Jika Anda mengaktifkan penciutan kode (*code shrinking*) menggunakan R8/ProGuard tanpa konfigurasi yang tepat, aplikasi AI Anda berisiko mengalami *crash* saat dijalankan dalam mode Release.

Buka file `proguard-rules.pro` Anda dan pastikan aturan berikut ditambahkan untuk menjaga kelas model AI agar tidak dihapus atau dikacaukan (*obfuscated*):

```pro
# Mempertahankan model data dari SDK Google AI (Gemini)
-keep class com.google.ai.client.generativeai.** { *; }
-keep interface com.google.ai.client.generativeai.** { *; }

# Jika Anda menggunakan Kotlin Serialization (sering dipasangkan dengan SDK AI)
-keepclassmembers class * {
    @kotlinx.serialization.SerialName <fields>;
}

# Mempertahankan library HTTP yang digunakan untuk memanggil API
-keepattributes Signature, InnerClasses, EnclosingMethod
-dontwarn okhttp3.**
-dontwarn okio.**
```

---

## 3. Menghasilkan Android App Bundle (AAB) yang Ditandatangani

Format AAB memungkinkan Google Play menggunakan fitur **Play App Delivery** untuk membuat APK yang dioptimalkan sesuai dengan konfigurasi perangkat masing-masing pengguna (menghemat ukuran unduhan hingga 30%).

Berikut adalah cara membuat *Signed* AAB:

### Langkah 1: Konfigurasi Signing Config di Gradle
Disarankan untuk mengonfigurasi penandatanganan rilis secara otomatis melalui `build.gradle.kts` demi konsistensi DevOps pipeline:

```kotlin
android {
    ...
    signingConfigs {
        create("release") {
            storeFile = file(project.property("MYAPP_RELEASE_STORE_FILE") as String)
            storePassword = project.property("MYAPP_RELEASE_STORE_PASSWORD") as String
            keyAlias = project.property("MYAPP_RELEASE_KEY_ALIAS") as String
            keyPassword = project.property("MYAPP_RELEASE_KEY_PASSWORD") as String
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```
*Catatan: Pastikan detail kredensial keystore disimpan di file `gradle.properties` lokal (tidak masuk ke Git repository).*

### Langkah 2: Build AAB Melalui CLI
Jalankan perintah Gradle berikut di terminal Android Studio Anda untuk menghasilkan file AAB:

```bash
./gradlew bundleRelease
```
Setelah proses selesai, file AAB Anda akan berada di direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## 4. Mengunggah dan Mengonfigurasi Pengujian Internal di Google Play Console

Pengujian Internal adalah metode tercepat untuk membagikan aplikasi AI Anda kepada maksimal 100 penguji internal tanpa perlu menunggu proses review aplikasi yang memakan waktu lama dari Google.

### Langkah 1: Buat Rilis Pengujian Internal
1. Masuk ke [Google Play Console](https://play.google.com/console/).
2. Pilih aplikasi Anda dari daftar proyek (atau buat aplikasi baru terlebih dahulu jika belum ada).
3. Pada menu navigasi sebelah kiri, gulir ke area **Siklus Rilis (Release)** -> **Pengujian (Testing)** -> **Pengujian internal (Internal testing)**.
4. Klik tombol **Buat rilis baru (Create new release)** di kanan atas.

### Langkah 2: Unggah File AAB Aplikasi AI Anda
1. Di bagian **App bundle**, klik **Unggah (Upload)**.
2. Pilih file `app-release.aab` yang telah Anda buat pada langkah sebelumnya.
3. Tunggu hingga proses unggah dan verifikasi library selesai. Google Play Console akan secara otomatis memproses struktur AAB Anda.

### Langkah 3: Tambahkan Penguji (Testers)
1. Klik tab **Penguji (Testers)** di halaman Pengujian Internal.
2. Buat daftar email baru (misalnya: "Tim QA Aplikasi AI").
3. Masukkan alamat email Google para penguji Anda, lalu klik **Simpan perubahan (Save changes)**.
4. Salin tautan **Link keikutsertaan (Opt-in URL)** yang disediakan di bagian bawah halaman. Bagikan tautan ini kepada tim penguji Anda agar mereka dapat menerima undangan pengujian dan mengunduh aplikasi langsung dari Google Play Store di perangkat mereka.

---

## Mengapa Konfigurasi Produksi Aplikasi AI Sering Kali Menyulitkan?

Bagi para pengembang pemula maupun tim yang baru saja bermigrasi dari sekadar membuat *prototype* di Google AI Studio, proses membawa aplikasi hingga tahap produksi sering kali menghadirkan tembok tebal yang membingungkan. 

Meskipun menulis kode integrasi Gemini API di emulator tampak sederhana, proses DevOps Android yang sebenarnya jauh lebih kompleks. Anda harus berhadapan dengan sinkronisasi versi Gradle yang sensitif, enkripsi API Key yang rentan bocor jika salah langkah, penanganan error R8/ProGuard yang sering kali membuat aplikasi langsung *force close* saat di-install dari Play Store, hingga kebijakan Google Play Console yang sangat ketat mengenai verifikasi ID dan penandatanganan aplikasi (*Play App Signing*). 

Sering kali, masalah sepele seperti salah konfigurasi SHA-1 fingerprint pada API Console dapat menyebabkan fitur AI Anda macet total hanya di perangkat penguji, sementara berjalan mulus di laptop Anda. Memahami arsitektur DevOps Android ini membutuhkan waktu dan trial-and-error yang tidak sebentar.

---

## Kesimpulan

Menyusun Android App Bundle (AAB) yang aman dan mendistribusikannya melalui Jalur Pengujian Internal adalah standar industri yang krusial untuk memastikan aplikasi berbasis kecerdasan buatan Anda berjalan optimal, efisien, dan aman. Dengan menerapkan pemisahan API Key menggunakan Secrets Gradle Plugin dan mengoptimalkan konfigurasi ProGuard untuk library AI, Anda telah meminimalkan risiko keamanan dan stabilitas sejak dini.

Lakukan pengujian internal secara menyeluruh terhadap performa model AI dan latensi respons API sebelum akhirnya melangkah ke jalur Pengujian Terbuka (Beta) maupun Rilis Produksi. Selamat berkarya dan kembangkan aplikasi AI inovatif Anda!