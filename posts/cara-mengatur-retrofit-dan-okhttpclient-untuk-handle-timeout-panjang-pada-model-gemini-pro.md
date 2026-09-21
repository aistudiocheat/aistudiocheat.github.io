---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-09-21"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Model bahasa besar (LLM) seperti **Gemini Pro** dari Google AI Studio memiliki kemampuan luar biasa untuk memproses dan menghasilkan teks, kode, hingga menganalisis gambar. Namun, dari sudut pandang *mobile development*, berinteraksi dengan API AI generatif memiliki karakteristik yang sangat berbeda dibandingkan dengan API REST tradisional.

Masalah utama yang sering dihadapi developer Android adalah **latency (waktu tunggu) yang tinggi**. Model Gemini Pro membutuhkan waktu beberapa detik hingga hitungan menit untuk melakukan *reasoning* dan menghasilkan respons yang panjang (terutama jika Anda tidak menggunakan metode *streaming*). 

Secara *default*, pustaka jaringan populer seperti **OkHttpClient** hanya memberikan batas toleransi waktu tunggu (timeout) selama 10 detik. Jika Anda tidak mengubah konfigurasi ini, aplikasi Anda dipastikan akan sering melempar error `java.net.SocketTimeoutException`.

Artikel ini akan membahas secara mendalam cara mengonfigurasi **Retrofit** dan **OkHttpClient** untuk menangani *timeout* panjang pada model Gemini Pro dengan aman dan efisien.

---

## Mengapa Gemini Pro Membutuhkan Timeout yang Lebih Panjang?

Sebelum masuk ke kode, mari pahami tiga jenis *timeout* yang ada pada `OkHttpClient`:

1. **Connect Timeout:** Waktu yang dialokasikan untuk membangun koneksi TCP dengan server Google.
2. **Write Timeout:** Waktu yang dialokasikan untuk mengirimkan *request body* (prompt Anda) ke server.
3. **Read Timeout:** Waktu yang dialokasikan untuk menunggu respons (token/teks yang dihasilkan Gemini) dari server setelah koneksi berhasil dibuat.

Untuk Gemini Pro, **Read Timeout** adalah parameter paling kritis. Proses komputasi AI di sisi server Google memerlukan waktu untuk melakukan pemrosesan (inference). Oleh karena itu, kita perlu melonggarkan batas waktu ini secara signifikan.

---

## Langkah 1: Tambahkan Dependensi yang Diperlukan

Pastikan file `build.gradle.kts` (modul app) Anda sudah menyertakan dependensi Retrofit, OkHttp, dan Coroutines terbaru.

```kotlin
dependencies {
    // Retrofit & OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coroutines untuk asynchronous calling
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
```

---

## Langkah 2: Konfigurasi OkHttpClient dengan Timeout Panjang

Kita akan membuat instance `OkHttpClient` dengan meningkatkan nilai *Read*, *Write*, dan *Connect* timeout. Untuk Gemini Pro, direkomendasikan untuk mengatur **Read Timeout hingga 60 atau 90 detik**.

Berikut adalah implementasi pembuatan `OkHttpClient` di Kotlin:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkClient {

    private fun provideLoggingInterceptor(): HttpLoggingInterceptor {
        return HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
    }

    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            // Hubungkan ke server maksimal dalam 30 detik
            .connectTimeout(30, TimeUnit.SECONDS)
            
            // Tunggu respons penuh dari Gemini Pro hingga 90 detik
            .readTimeout(90, TimeUnit.SECONDS)
            
            // Kirim data/prompt ke server maksimal dalam 30 detik
            .writeTimeout(30, TimeUnit.SECONDS)
            
            // Menambahkan interceptor untuk debugging log (opsional)
            .addInterceptor(provideLoggingInterceptor())
            .build()
    }
}
```

---

## Langkah 3: Integrasikan OkHttpClient dengan Retrofit

Setelah memiliki konfigurasi `OkHttpClient` yang kuat, langkah selanjutnya adalah menerapkannya ke dalam instance `Retrofit`.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson:GsonConverterFactory

object RetrofitClient {
    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val geminiService: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(NetworkClient.provideOkHttpClient()) // Menggunakan OkHttpClient kustom kita
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Buat Representasi API Gemini Pro

Untuk berinteraksi dengan API Google AI Studio, kita perlu mendefinisikan *interface* Retrofit beserta kelas representasi data (*data class*) untuk *request* dan *response*.

*Catatan: Contoh di bawah adalah struktur sederhana untuk memanggil endpoint non-streaming `generateContent`.*

```kotlin
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

interface GeminiApiService {
    @POST("v1beta/models/gemini-pro:generateContent")
    suspend fun generateContent(
        @Query("key") apiKey: String,
        @Body request: GeminiRequest
    ): GeminiResponse
}

// Data Class Model untuk Request & Response
data class GeminiRequest(
    val contents: List<Content>
)

data class Content(
    val parts: List<Part>
)

data class Part(
    val text: String
)

data class GeminiResponse(
    val candidates: List<Candidate>?
)

data class Candidate(
    val content: Content?
)
```

---

## Langkah 5: Eksekusi Request dengan Aman

Karena proses ini memakan waktu lama (bisa mencapai 1 menit), Anda wajib menjalankannya di dalam Coroutine (`Dispatchers.IO`) dan menangani potensi error yang terjadi demi menjaga *User Experience* (UX) agar aplikasi tidak *force close*.

```kotlin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.IOException
import retrofit2.HttpException

fun generateAIResponse(promptText: String, apiKey: String) {
    CoroutineScope(Dispatchers.Main).launch {
        // Tampilkan loading indicator ke user disini
        
        try {
            val request = GeminiRequest(
                contents = listOf(Content(parts = listOf(Part(text = promptText))))
            )
            
            val response = withContext(Dispatchers.IO) {
                RetrofitClient.geminiService.generateContent(apiKey, request)
            }
            
            val generatedText = response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
            if (generatedText != null) {
                // Tampilkan hasil ke UI
                println("Gemini Response: $generatedText")
            } else {
                println("Gagal mendapatkan konten dari respons.")
            }
            
        } catch (e: HttpException) {
            // Menangani error dari server (Misal: Rate limit, API Key salah)
            println("Http Error: ${e.message()}")
        } catch (e: IOException) {
            // Menangani timeout atau kehilangan koneksi internet
            println("Network Error: Koneksi timeout atau terputus. Silakan coba lagi.")
        } finally {
            // Sembunyikan loading indicator disini
        }
    }
}
```

---

## Tantangan Nyata: Dari Prototype Google AI Studio ke Produksi Massal

Mengonfigurasi *timeout* pada Retrofit secara lokal di komputer Anda memang tampak sederhana dengan panduan di atas. Namun, membawa proyek aplikasi Android berbasis AI dari tahap *prototype* di Google AI Studio hingga siap dirilis ke Google Play Store memiliki tingkat kompleksitas yang jauh lebih tinggi.

Bagi pemula maupun developer solo, Anda akan dihadapkan pada tantangan DevOps dan arsitektur yang cukup rumit, seperti:
* **Keamanan API Key:** Menyimpan API Key Google AI Studio langsung di dalam kode aplikasi Android sangat berbahaya karena rentan di-decompile (reverse engineering) oleh pihak tidak bertanggung jawab.
* **Arsitektur Backend Proxy:** Untuk mengamankan API Key, Anda perlu membangun server perantara (backend proxy/gateway) yang menjembatani aplikasi Android dengan Google AI Studio.
* **Manajemen Rate Limiting:** Bagaimana mengelola antrean *request* pengguna agar kuota API Anda tidak habis seketika.
* **Offline Handling & Caching:** Strategi menyimpan hasil generasi AI agar pengguna tidak perlu melakukan request berulang untuk prompt yang sama, menghemat biaya operasional API Anda.

Menghadapi tumpukan teknologi (tech stack) baru seperti setup server, integrasi CI/CD untuk rilis aplikasi, hingga pengamanan enkripsi tingkat tinggi sering kali menguras waktu dan energi yang seharusnya bisa Anda fokuskan untuk menyempurnakan fitur utama aplikasi Anda.