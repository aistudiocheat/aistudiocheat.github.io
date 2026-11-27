---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-11-27"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengembangkan aplikasi berbasis Kecerdasan Buatan (AI) menggunakan API dari **Google AI Studio** atau SDK Gemini memang menawarkan fleksibilitas luar biasa. Namun, mengubah prototipe yang berfungsi di lingkungan lokal menjadi aplikasi siap rilis di Play Store memerlukan standar *DevOps* dan keamanan Android yang ketat.

Salah satu format distribusi standar yang diwajibkan oleh Google saat ini adalah **Android App Bundle (.aab)**. Format ini memungkinkan Google Play melakukan optimalisasi ukuran file APK sesuai dengan konfigurasi perangkat pengguna.

Artikel ini akan membahas secara mendalam tata cara menyusun AAB yang aman, melakukan optimasi *build*, hingga mendistribusikannya melalui fitur **Internal Testing** di Google Play Console.

---

## 1. Persiapan Keamanan dan Konfigurasi Proyek Android AI

Aplikasi AI yang mengintegrasikan SDK Google AI Studio (seperti Gemini API) memerlukan penanganan khusus pada *API Key* dan aturan obfuskasi kode (*ProGuard/R8*).

### Mengamankan API Key Menggunakan Secrets Gradle Plugin
Jangan pernah memasukkan *API Key* Google AI Studio secara langsung (*hardcoded*) ke dalam kode sumber. Gunakan plugin `secrets-gradle-plugin` untuk membaca kredensial dari file `local.properties`.

Tambahkan plugin pada file `build.gradle.kts` (Project level):

```kotlin
plugins {
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

Terapkan pada `build.gradle.kts` (Module level):

```kotlin
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}

android {
    namespace = "com.example.aiapplication"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.aiapplication"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

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
}
```

### Konfigurasi ProGuard untuk SDK AI
Saat fitur `isMinifyEnabled` diaktifkan, compiler R8 akan membuang kode yang dianggap tidak terpakai. Untuk mencegah *runtime crash* saat melakukan *parsing* JSON dari API Gemini, tambahkan aturan berikut di `proguard-rules.pro`:

```pro
# Mencegah Obfuskasi pada Model Serialisasi Data AI
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Menjaga SDK Gemini / Google AI Studio Client
-keep class com.google.ai.client.generativeai.** { *; }
-dontwarn com.google.ai.client.generativeai.**
```

---

## 2. Membuat KeyStore dan Mengompilasi Android App Bundle (AAB)

Format `.aab` harus ditandatangani dengan *Cryptographic Key* yang valid sebelum diunggah ke Google Play Console.

### Langkah 1: Membuat Upload Keystore
Gunakan utilitas `keytool` melalui terminal/command line untuk membuat berkas `.jks`:

```bash
keytool -genkey -v -keystore release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias release-alias
```

### Langkah 2: Konfigurasi Signing Config di Gradle
Buka `build.gradle.kts` (Module level) dan sesuaikan blok penandatanganan aplikasi:

```kotlin
android {
    signingConfigs {
        create("release") {
            storeFile = file("release-key.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: "PasswordKeystoreAnda"
            keyAlias = "release-alias"
            keyPassword = System.getenv("KEY_PASSWORD") ?: "PasswordKeyAnda"
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

### Langkah 3: Build Bundel AAB
Jalankan perintah Gradle berikut di terminal Android Studio:

```bash
./gradlew bundleRelease
```

File `.aab` yang siap diunggah akan berada di direktori:
`app/build/outputs/bundle/release/app-release.aab`

---

## 3. Konfigurasi Pengujian Internal (Internal Testing) di Google Play Console

Pengujian Internal adalah jalur (*track*) tercepat untuk mendistribusikan aplikasi ke tim QA atau *internal tester* tanpa harus melewati proses peninjauan (*review*) ketat dari pihak Google Play Store.

### Langkah-Langkah Mengunggah AAB:

1. **Masuk ke Google Play Console:** Buka konsol aplikasi Anda dan pilih aplikasi yang telah dibuat.
2. **Navigasi ke Pengujian Internal:** Pada menu sebelah kiri, cari bagian **Testing** > pilih **Internal testing** (Pengujian internal).
3. **Buat Rilis Baru (Create new release):**
   * Klik tombol **Create new release** di pojok kanan atas.
   * Sertakan file `app-release.aab` yang telah digenerate pada langkah sebelumnya dengan mengklik **Upload**.
4. **Isi Release Notes:** Tuliskan deskripsi singkat mengenai fitur AI yang diuji, misalnya: `"Internal Build v1.0.0: Integrasi Gemini Pro API dan perbaikan alur streaming teks."`
5. **Simpan dan Tinjau Rilis:** Klik **Save**, kemudian **Review release**, dan klik **Start rollout to Internal testing**.

```
[ Dashboard Console ] ➔ [ Testing ] ➔ [ Internal testing ] ➔ [ Create new release ] ➔ [ Upload AAB ] ➔ [ Rollout ]
```

### Menambahkan Penguji Internal (Internal Testers)
1. Pilih tab **Testers** pada halaman Internal Testing.
2. Buat daftar email (*Email List*) yang berisi alamat Google Play pengguna yang ditunjuk sebagai penguji.
3. Salin **Join on the web** atau **Join on Android** URL link dan bagikan kepada tim penguji Anda.

---

## 4. Menghubungkan SHA-1 Release Ke Google AI Studio

Supaya API Key Google AI Studio hanya dapat diakses oleh aplikasi resmi milik Anda, Anda wajib mendaftarkan **SHA-1 Fingerprint** aplikasi ke Google Cloud Console / AI Studio.

Jalankan perintah ini untuk mendapatkan fingerprint dari App Signing Google Play:

```bash
keytool -list -v -keystore release-key.jks -alias release-alias
```

Salin deretan karakter `SHA-1`, lalu buka **Google Cloud Console > APIs & Services > Credentials**, buka kunci API yang Anda gunakan untuk Gemini, lalu tambahkan batasan (*Application Restrictions*) berupa Android apps dengan memasukkan Package Name dan SHA-1 tersebut.

---

## Tantangan Tersembunyi: Mengapa Pipeline Build Aplikasi AI Terasa Rumit?

Membangun aplikasi Android AI berbasis Google AI Studio dari sekadar *proof-of-concept* hingga menjadi aplikasi siap rilis yang stabil bukanlah perkara mudah. Bagi pengembang individual maupun tim yang terbiasa fokus pada pengembangan alur aplikasi (*frontend*), kompleksitas teknis berikut sering kali menjadi hambatan besar:

* **Manajemen Keamanan API & Reverse Engineering:** Aplikasi AI rentan terhadap pencurian *API Key* jika konfigurasi Obfuskasi (R8/ProGuard) dan pengamanan *Native C++/Secrets Manager* tidak dilakukan dengan benar.
* **Integrasi Keamanan Play Integrity API:** Memastikan bahwa permintaan yang masuk ke server AI benar-benar berasal dari biner aplikasi resmi Anda, bukan aplikasi bajakan atau emulator yang berpotensi menghabiskan kuota kuota token API Anda.
* **Optimasi Ukuran AAB & Memory Leak:** Model AI *on-device* maupun pemrosesan *data stream* yang berat sering kali memicu kendala performa, *out-of-memory error*, hingga kegagalan kompilasi AAB karena batasan ukuran file dan library native.
* **Proses Sertifikasi dan Kebijakan Google Play:** Regulasi Google Play Console yang ketat terkait konten hasil pemrosesan AI (*Generative AI Policy*) membutuhkan pengaturan kepatuhan teknis dan pelaporan yang sesuai standar industri.

Proses konfigurasi arsitektur build, pipeline CI/CD, hingga kesiapan rilis produk berstandar *enterprise* sering kali memakan waktu berminggu-minggu jika ditangani tanpa keahlian DevOps Android yang mendalam.

---

## Kesimpulan

Mengompilasi Android App Bundle (AAB) dan mempublikasikannya ke *Internal Testing* Google Play Console merupakan fondasi utama dalam siklus pengujian aplikasi modern berbasis AI. Dengan menerapkan pemisahan kredensial, optimasi ProGuard, dan pembatasan SHA-1 pada API Key Google AI Studio, aplikasi Anda tidak hanya siap diuji oleh tim internal tetapi juga terjamin secara keamanan.