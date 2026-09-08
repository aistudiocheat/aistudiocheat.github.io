---
title: "Panduan Menyusun Android App Bundle (AAB) dan Pengujian Internal di Google Play Console untuk Aplikasi AI"
date: "2026-09-08"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Artificial Intelligence (AI) ke dalam aplikasi mobile kini bukan lagi sekadar tren, melainkan sebuah kebutuhan standar industri. Dengan kehadiran SDK Google AI Studio (Gemini API), developer Android dapat dengan mudah menyematkan model bahasa besar (LLM) langsung ke dalam genggaman pengguna.

Namun, menulis kode Kotlin yang terhubung ke API AI barulah separuh jalan. Tantangan sesungguhnya ada pada aspek **DevOps Android**: bagaimana mengamankan API key, mengoptimalkan ukuran rilis menggunakan format Android App Bundle (AAB), mengonfigurasi ProGuard agar kode AI tidak *crash* setelah diobfuskasi, hingga mendistribusikannya secara aman melalui jalur Pengujian Internal (Internal Testing) di Google Play Console.

Artikel ini akan memandu Anda secara mendalam langkah demi langkah untuk menyelesaikan siklus rilis aplikasi Android berbasis AI secara profesional.

---

## Langkah 1: Mengamankan API Key Gemini (Google AI Studio)

Jangan pernah menuliskan API Key langsung (*hardcode*) di dalam kode Kotlin atau menyimpannya di file `strings.xml`. Jika repositori Anda bersifat publik di GitHub, bot pemindai akan mencuri API key Anda dalam hitungan detik.

Cara terbaik untuk mengamankan API key di level lokal dan *build pipeline* adalah menggunakan **Secrets Gradle Plugin untuk Android**.

### 1. Tambahkan Plugin ke Project
Buka file `build.gradle.kts` tingkat project (root):

```kotlin
plugins {
    // ... plugin lainnya
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin") version "2.0.1" apply false
}
```

Kemudian, buka `build.gradle.kts` tingkat modul (:app) dan terapkan plugin tersebut:

```kotlin
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("com.google.android.libraries.mapsplatform.secrets-gradle-plugin")
}
```

### 2. Definisikan API Key di `local.properties`
Buka file `local.properties` di direktori utama proyek Anda (pastikan file ini sudah masuk dalam `.gitignore`), lalu tambahkan baris berikut:

```properties
GEMINI_API_KEY=AIzaSyD_ContohApiKeyGeminiAnda YangAsli
```

### 3. Akses API Key dari Kode Kotlin
Plugin secara otomatis akan mengonversi properti tersebut menjadi variabel di kelas `BuildConfig`. Anda dapat memanggilnya seperti ini:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel

val aiModel = GenerativeModel(
    modelName = "gemini-1.5-flash",
    apiKey = BuildConfig.GEMINI_API_KEY
)
```

---

## Langkah 2: Mengonfigurasi ProGuard/R8 untuk SDK AI

Saat Anda membangun rilis produksi (AAB), compiler R8 akan melakukan ciutkan kode (*shrinking*) dan obfuskasi (*obfuscation*). Karena SDK Google AI menggunakan refleksi dan serialisasi JSON di balik layar, obfuskasi yang terlalu agresif dapat menyebabkan aplikasi *crash* dengan *error* seperti `NullPointerException` atau `SerializationException`.

Tambahkan aturan (rules) berikut pada file `proguard-rules.pro` Anda:

```proguard
# Menjaga kelas-kelas dari Google AI SDK agar tidak diobfuskasi
-keep class com.google.ai.client.generativeai.** { *; }
-keep class com.google.ai.client.generativeai.type.** { *; }

# Jika Anda menggunakan Kotlinx Serialization (sering digunakan bersama SDK AI)
-keepattributes *Annotation*,Signature,InnerClasses
-keepclassmembers class * {
    @kotlinx.serialization.Serializable *;
}

# Menjaga library HTTP yang digunakan oleh SDK (misal: OkHttp atau Ktor)
-keep class okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn org.codehaus.mojo.animal_sniffer.IgnoreJRERequirement
```

---

## Langkah 3: Membuat Android App Bundle (AAB) Rilis

Google Play Store mewajibkan format `.aab` untuk aplikasi baru. Keuntungan utama AAB adalah *Dynamic Delivery*, di mana Google Play akan memilah aset dan kode instruksi CPU yang hanya dibutuhkan oleh perangkat target user, sehingga ukuran unduhan menjadi jauh lebih kecil.

### Cara Generate Keystore Baru (Jika Belum Punya)
Jika ini adalah pertama kalinya Anda merilis aplikasi, Anda membutuhkan kunci penandatangan (*signing key*).

Buka terminal dan jalankan perintah `keytool` berikut:

```bash
keytool -genkey -v -keystore rilis-keystore-ai.jks -keyalg RSA -keysize 2048 -validity 10000 -alias kunci-ai
```

### Konfigurasi Signing di `build.gradle.kts` (:app)
Hubungkan keystore Anda ke konfigurasi build rilis:

```kotlin
android {
    ...
    signingConfigs {
        create("release") {
            storeFile = file("rilis-keystore-ai.jks")
            storePassword = System.getenv("SIGNING_STORE_PASSWORD") ?: "PasswordStoreAnda"
            keyAlias = System.getenv("SIGNING_KEY_ALIAS") ?: "kunci-ai"
            keyPassword = System.getenv("SIGNING_KEY_PASSWORD") ?: "PasswordKunciAnda"
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

### Membuat AAB Melalui CLI Gradle
Untuk memicu proses kompilasi rilis, jalankan perintah berikut di terminal Android Studio Anda:

```bash
./gradlew bundleRelease
```
Setelah proses selesai, file `.aab` Anda akan berada di direktori:
`app/build/outputs/bundle/release/app-release.aab`.

---

## Langkah 4: Pengujian Internal di Google Play Console

Jalur Pengujian Internal (Internal Testing) adalah cara tercepat untuk mendistribusikan aplikasi Anda kepada hingga 100 penguji internal terpilih tanpa perlu menunggu peninjauan penuh (*full review*) dari tim Google Play yang memakan waktu berhari-hari.

### 1. Buat Aplikasi Baru di Google Play Console
* Masuk ke [Google Play Console](https://play.google.com/console/).
* Klik **Buat aplikasi** (Create app).
* Isi nama aplikasi Anda (misal: "Gemini AI Assistant"), pilih bahasa default, dan tentukan jenis aplikasi (Aplikasi, Gratis/Berbayar).

### 2. Daftarkan Daftar Penguji (Testers)
Sebelum mengunggah berkas, buat daftar penguji internal Anda:
* Di menu navigasi kiri, gulir ke bawah ke bagian **Rilis** (Release) > **Pengujian** (Testing) > **Pengujian internal** (Internal testing).
* Pilih tab **Penguji** (Testers).
* Di bawah opsi "Email lists", klik **Buat daftar email**.
* Masukkan alamat email Gmail para penguji Anda (termasuk email Anda sendiri untuk menguji di perangkat pribadi). Klik **Simpan**.

### 3. Unggah File AAB
* Masih di halaman Pengujian Internal, klik tombol **Buat rilis baru** (Create new release) di sudut kanan atas.
* Jika diminta untuk menyetujui *Play App Signing*, pilih **Aktifkan** (disarankan karena ini wajib untuk AAB).
* Tarik dan lepas (drag-and-drop) file `app-release.aab` yang telah Anda buat sebelumnya ke area unggah.
* Isi nama rilis dan catatan rilis (*release notes*) singkat (misal: "Integrasi awal Gemini API dengan keamanan ProGuard").
* Klik **Simpan sebagai draf**, lalu klik **Tinjau rilis** dan **Mulai peluncuran ke Pengujian Internal**.

### 4. Distribusikan Link Pengujian
* Kembali ke tab **Penguji** di menu Pengujian Internal.
* Gulir ke bagian bawah untuk menemukan **Tautan keikutsertaan** (How testers join your test).
* Salin tautan tersebut dan bagikan kepada penguji terdaftar Anda.
* Penguji harus membuka tautan tersebut dari perangkat Android mereka, menerima undangan pengujian, lalu mereka akan diarahkan untuk mengunduh versi rilis langsung dari Google Play Store.

---

## Tantangan Nyata dalam Menghubungkan Google AI Studio ke Jalur Produksi

Mengonfigurasi proyek Android dari tahap prototipe di Google AI Studio hingga menjadi versi rilis siap pakai di Google Play Store sering kali tampak mudah di atas kertas. Namun pada praktiknya, proses ini menyimpan kerumitan tingkat tinggi bagi para developer, terutama pemula.

Banyak tantangan tak terduga yang kerap muncul di fase akhir ini, seperti:

*   **Masalah Gradle & Versi Dependency:** Bentrokan versi Kotlin, Gradle, dan SDK Google AI sering kali memicu error kompilasi yang sulit dipahami.
*   **Kehilangan Keystore / File JKS:** Sekali Anda kehilangan file *signing key* atau melupakan password-nya, Anda tidak akan pernah bisa memperbarui aplikasi yang sama di Play Store lagi.
*   **Kebijakan Sensor Konten AI Google:** Google Play memiliki kebijakan yang sangat ketat mengenai konten yang dihasilkan oleh AI (*AI-generated content*). Aplikasi Anda terancam ditolak secara instan jika tidak menyediakan sistem pelaporan konten tidak pantas atau filter keamanan yang memadai.
*   **Masalah Kuota & Geografis:** Gemini API memiliki batasan wilayah (*regional availability*) serta batas kuota ketat (*rate limit*). Mengelola transisi dari API Key gratisan ke sistem *billing* berbayar tanpa mengganggu pengalaman pengguna memerlukan arsitektur backend yang solid.

Proses konfigurasi arsitektur DevOps, penataan build variant, hingga penanganan regulasi Google Play Console memang membutuhkan presisi tinggi dan ketelitian ekstra agar proyek AI Anda tidak terhambat di tengah jalan sebelum sempat dicoba oleh pengguna.