---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-11-10"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Perkembangan teknologi kecerdasan buatan (*Artificial Intelligence*) yang begitu pesat memicu peningkatan signifikan dalam pengembangan aplikasi Android berbasis AI. Dengan hadirnya **Google AI Studio** dan **Gemini API**, pengembang kini dapat mengintegrasikan kemampuan LLM (*Large Language Model*) langsung ke dalam genggaman pengguna.

Namun, mengubah prototipe aplikasi AI menjadi produk siap rilis yang aman, ringan, dan stabil membutuhkan penanganan DevOps Android yang tepat. Penggunaan format legacy APK sudah tidak lagi direkomendasikan. Google Play Store kini mewajibkan penggunaan **Android App Bundle (AAB)**.

Artikel ini akan membahas panduan komprehensif mulai dari mengamankan *API Key*, melakukan *build* file AAB yang teroptimasi, hingga mengonfigurasi jalur **Pengujian Internal (Internal Testing)** di Google Play Console.

---

## Langkah 1: Pengamanan API Key dan Optimasi Proyek Aplikasi AI

Aplikasi AI yang memanfaatkan Google AI Studio sangat bergantung pada *API Key*. Menyimpan *API Key* secara langsung (*hardcoding*) di dalam kode sumber (*source code*) adalah celah keamanan serius yang dapat dieksploitasi melalui teknik *reverse engineering*.

### 1. Amankan API Key dengan Secrets Gradle Plugin

Gunakan plugin resmi `secrets-gradle-plugin` untuk menyembunyikan API key Gemini dari repository Git Anda.

Tambahkan plugin pada file `build.gradle.kts` tingkat proyek (Root):

```kotlin
// build.gradle.kts (Project Level)
plugins {
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

Terapkan plugin pada file `build.gradle.kts` tingkat modul aplikasi:

```kotlin
// build.gradle.kts (Module :app)
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}

android {
    compileSdk = 35

    defaultConfig {
        applicationId = "com.contoh.appai"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true // Mengaktifkan ProGuard/R8
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

Simpan *API Key* Anda pada file `local.properties`:

```properties
GEMINI_API_KEY=AIzaSyYourSecretKeyHereFromGoogleAIStudio
```

Kini Anda dapat memanggil kunci tersebut secara aman melalui file Kotlin:

```kotlin
val apiKey = BuildConfig.GEMINI_API_KEY
val generativeModel = GenerativeModel(
    modelName = "gemini-1.5-flash",
    apiKey = apiKey
)
```

### 2. Konfigurasi ProGuard Rules untuk SDK AI

Optimasi R8/ProGuard dapat menyebabkan kegagalan *parsing* JSON atau hilangnya class SDK Gemini jika tidak dikonfigurasi dengan benar. Tambahkan aturan berikut pada `proguard-rules.pro`:

```proguard
# Menjaga Data Class parsing respon Gemini API
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Menjaga library gRPC / OkHttp yang digunakan SDK AI
-keepattributes Signature, InnerClasses, EnclosingMethod
-dontwarn okio.**
-dontwarn org.codehaus.mojo.animal_sniffer.**
```

---

## Langkah 2: Membuat Digital Signature dan Release AAB

Format AAB mengelompokkan kodenya sedemikian rupa sehingga Google Play Console dapat mendistribusikan APK yang disesuaikan (*Dynamic Delivery*) dengan konfigurasi perangkat pengguna (arsitektur CPU, bahasa, dan resolusi layar).

### 1. Membuat Keystore (Signing Key)

Jalankan perintah berikut di terminal untuk membuat file `keystore` rilis:

```bash
keytool -genkey -v -keystore my-ai-app-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias my-key-alias
```

*Pastikan Anda menyimpan file `.jks`, kata sandi, dan alias di tempat yang aman.*

### 2. Melakukan Build AAB Melalui Android Studio

1. Buka Android Studio.
2. Pilih menu **Build > Generate Signed Bundle / APK...**
3. Pilih **Android App Bundle** lalu klik **Next**.
4. Masukkan direktori file `my-ai-app-key.jks`, kata sandi *keystore*, *alias*, dan kata sandi *alias*.
5. Pilih *Build Variant*: **release**.
6. Klik **Create**. File `.aab` akan tergenerasi di folder `app/release/app-release.aab`.

---

## Langkah 3: Konfigurasi Pengujian Internal di Google Play Console

Pengujian Internal (*Internal Testing*) memungkinkan Anda mendistribusikan aplikasi ke hingga 100 penguji terdaftar untuk memvalidasi performa fitur AI secara cepat tanpa melalui proses peninjauan publik yang lama.

```
+-----------------------------------------------------------------------+
|                 Bagan Alur Distribusi AAB Aplikasi AI                  |
+-----------------------------------------------------------------------+
|                                                                       |
|  [ Local Dev ] ---> [ Build AAB (Signed) ] ---> [ Upload Play Console ] |
|                                                         |             |
|                                                         v             |
|  [ Play App Signing (SHA-1 Setup) ] <--- [ Play Console Storage ]     |
|                 |                                                     |
|                 v                                                     |
|  [ Google AI Studio (Restriksi Key) ]                                  |
|                 |                                                     |
|                 v                                                     |
|  [ Penguji Internal (Tes Aplikasi via Play Store) ]                   |
|                                                                       |
+-----------------------------------------------------------------------+
```

### 1. Buat Aplikasi Baru di Google Play Console
* Masuk ke dashboard [Google Play Console](https://play.google.com/console).
* Klik tombol **Buat Aplikasi** (*Create App*).
* Isi nama aplikasi, bahasa bawaan, dan deklarasikan bahwa aplikasi ini adalah aplikasi gratis/berbayar.

### 2. Aktifkan Play App Signing
Google Play Console secara otomatis mengelola kunci penandatanganan aplikasi Anda. Saat pertama kali mengunggah AAB, **Play App Signing** akan aktif secara otomatis.

### 3. Unggah Bundle ke Track Pengujian Internal
1. Pada menu navigasi sebelah kiri, buka **Pengujian > Pengujian internal** (*Testing > Internal testing*).
2. Klik tab **Penguji** (*Testers*), buat daftar email yang berisi akun Google milik para penguji internal Anda.
3. Klik **Buat Rilis Baru** (*Create new release*).
4. Unggah file `app-release.aab` yang telah Anda buat pada Langkah 2.
5. Beri Nama Rilis (misal: `1.0.0-build-01-beta-ai`).
6. Klik **Simpan** lalu pilih **Tinjau rilis**, dilanjutkan dengan **Mulai peluncuran ke Pengujian Internal**.

---

## Langkah 4: Sinkronisasi SHA-1 Play Console dengan Google AI Studio

Fitur AI pada aplikasi Anda dapat mengalami kegagalan (*error 403 Forbidden*) jika *API Key* dibatasi berdasarkan *Fingerprint Certificate SHA-1*, sementara SHA-1 yang terdaftar belum diperbarui.

Sebab, saat AAB diunggah, Google Play akan menandatangani ulang APK akhir menggunakan kunci *Play App Signing*, yang memiliki SHA-1 berbeda dari *Keystore* lokal Anda.

### Cara Menghubungkan SHA-1 Play Console:

1. Di Google Play Console, buka menu **Penyiapan > Integritas Aplikasi** (*Setup > App integrity*).
2. Pada tab **Play App Signing**, salin **Sidik jari sertifikat SHA-1** (*SHA-1 certificate fingerprint*).
3. Buka **Google Cloud Console** atau **Google AI Studio API Credentials**.
4. Edit kredensial *API Key* Gemini Anda.
5. Tambahkan pembatasan aplikasi (*Application restrictions*) ke **Android apps**.
6. Masukkan **Package Name** aplikasi dan salin nilai **SHA-1** dari Play Console tadi.
7. Simpan perubahan.

```
[Google Play Console SHA-1] ---> [Google AI Studio Restrictions] ---> [API Gemini Berhasil Dikonfirmasi]
```

---

## Kompleksitas Integrasi AI dan Infrastruktur Android: Tantangan yang Sering Diabaikan

Proses di atas menggambarkan bahwa membangun aplikasi AI modern tidak sekadar berfokus pada kualitas respon *prompt* atau pemilihan arsitektur *Dynamic Delivery*. Terdapat koordinasi infrastruktur teknis yang rumit di balik layar.

Bagi banyak pengembang individual maupun tim yang baru pertama kali membawa proyek Google AI Studio ke tingkat produksi, beberapa kendala kritis ini kerap menjadi penghambat utama:

* **Sertifikat Signatures yang Bentrok:** Kebingungan membedakan antara SHA-1 *Debug*, SHA-1 *Release Local*, dan SHA-1 *Play App Signing* yang menyebabkan API AI berhenti berfungsi mendadak saat diinstal oleh penguji.
* **Kebocoran Kredensial:** Kesalahan konfigurasi file Gradle yang menyebabkan *API Key* komersial bernilai tinggi terekspos di repo publik atau terurai saat file AAB didekompilasi.
* **ProGuard Truncation:** Terhapusnya pustaka internal gRPC, Retrofit, atau serialisasi data AI akibat optimasi kode yang terlalu agresif, yang berujung pada kendala *crash-on-launch*.
* **Otomatisasi CI/CD:** Kesulitan membangun alur kerja *Continuous Integration/Continuous Deployment* (seperti GitHub Actions atau Bitrise) yang mampu melakukan *build*, *signing*, dan *auto-deploy* file AAB langsung ke Google Play Console secara aman.

Rangkaian kendala di atas menunjukkan bahwa menjembatani prototip AI cerdas menjadi aplikasi *enterprise-grade* di Google Play Store memerlukan ketelitian teknis, pemahaman mendalam tentang ekosistem Google Cloud, serta implementasi standar keamanan Android DevOps yang ketat.