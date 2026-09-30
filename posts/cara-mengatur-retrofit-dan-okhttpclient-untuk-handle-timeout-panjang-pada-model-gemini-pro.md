---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-09-30"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan Large Language Model (LLM) seperti Gemini Pro ke dalam aplikasi Android memberikan potensi luar biasa. Namun, tidak seperti REST API tradisional yang merespons dalam hitungan milidetik, model AI generatif sering kali membutuhkan waktu beberapa detik—bahkan menit—untuk memproses prompt yang kompleks dan menghasilkan respons (token).

Secara *default*, pustaka jaringan populer di Android seperti **OkHttpClient** dan **Retrofit** dikonfigurasi dengan batas waktu (*timeout*) yang cukup ketat (biasanya 10 detik). Jika Anda menggunakan konfigurasi bawaan ini untuk memanggil API Gemini Pro, aplikasi Anda akan sering mengalami `SocketTimeoutException`.

Artikel ini akan membahas secara mendalam cara mengonfigurasi OkHttpClient dan Retrofit agar mampu menangani *timeout* panjang saat berkomunikasi dengan model Gemini Pro secara stabil dan efisien.

---

## Mengapa Gemini Pro Membutuhkan Timeout Lebih Panjang?

Sebelum masuk ke kode, kita perlu memahami karakteristik respons dari Gemini Pro:
1. **Time to First Token (TTFT):** Waktu yang dibutuhkan model untuk mulai memproses dan mengirimkan karakter pertama.
2. **Panjang Prompt & Output:** Semakin kompleks instruksi Anda atau semakin panjang artikel/kode yang perlu dihasilkan, semakin lama waktu pemrosesan di sisi server Google AI Studio.
3. **Network Latency:** Latensi jaringan global, terutama jika pengguna berada pada koneksi seluler yang tidak stabil.

Oleh karena itu, sangat direkomendasikan untuk menaikkan ambang batas *timeout* hingga **60 hingga 120 detik** untuk operasi non-streaming.

---

## Langkah 1: Menambahkan Dependency yang Diperlukan

Pastikan file `build.gradle.kts` (modul app) Anda sudah menyertakan dependency Retrofit dan OkHttp versi terbaru.

```kotlin
dependencies {
    // Retrofit & Gson Converter
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")

    // OkHttp & Logging Interceptor
    implementation(platform("com.squareup.okhttp3:okhttp-bom:4.12.0"))
    implementation("com.squareup.okhttp3:okhttp")
    implementation("com.squareup.okhttp3:logging-interceptor")
}
```

---

## Langkah 2: Mengonfigurasi OkHttpClient dengan Timeout Panjang

Kunci utama penanganan *timeout* terletak pada konfigurasi `OkHttpClient.Builder`. Kita perlu menyesuaikan tiga parameter utama:
*   **Connect Timeout:** Batas waktu untuk membangun koneksi TCP dengan server.
*   **Read Timeout:** Batas waktu untuk membaca data dari server (ini yang paling krusial untuk LLM).
*   **Write Timeout:** Batas waktu untuk mengirimkan data/payload ke server.

Berikut adalah cara membuat instansiasi `OkHttpClient` yang dioptimalkan untuk Gemini API:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object HttpClientProvider {

    fun provideOkHttpClient(): OkHttpClient {
        // Interceptor untuk memantau request dan response selama fase development
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur timeout hingga 90 detik
            .connectTimeout(90, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .writeTimeout(90, TimeUnit.SECONDS)
            // Menambahkan interceptor log
            .addInterceptor(loggingInterceptor)
            // Konfigurasi tambahan: Retry on connection failure
            .retryOnConnectionFailure(true)
            .build()
    }
}
```

---

## Langkah 3: Menghubungkan OkHttpClient dengan Retrofit

Setelah `OkHttpClient` dengan kapasitas *timeout* panjang siap, kita perlu menyuntikkannya (*inject*) ke dalam builder Retrofit.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val geminiService: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(HttpClientProvider.provideOkHttpClient()) // Menggunakan OkHttpClient custom
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Membuat Interface API untuk Gemini Pro

Untuk melakukan panggilan ke Google AI Studio, kita perlu mendefinisikan endpoint dan struktur request/response. Berikut adalah contoh sederhana implementasi endpoint `generateContent` untuk Gemini Pro.

### 1. Definisikan Data Class (Request & Response)

```kotlin
// Request Models
data class GeminiRequest(
    val contents: List<Content>
)

data class Content(
    val parts: List<Part>
)

data class Part(
    val text: String
)

// Response Models
data class GeminiResponse(
    val candidates: List<Candidate>?
)

data class Candidate(
    val content: Content?
)
```

### 2. Buat Retrofit Interface

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
```

---

## Langkah 5: Eksekusi Request dan Penanganan Error (Exception Handling)

Di lapisan repository atau ViewModel, lakukan pemanggilan API menggunakan blok `try-catch` untuk menangkap error *timeout* atau masalah jaringan lainnya secara elegan.

```kotlin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException
import java.net.SocketTimeoutException

class GeminiRepository {
    private val apiService = RetrofitClient.geminiService

    suspend fun askGemini(prompt: String, apiKey: String): String {
        return withContext(Dispatchers.IO) {
            try {
                val request = GeminiRequest(
                    contents = listOf(Content(parts = listOf(Part(text = prompt))))
                )
                val response = apiService.generateContent(apiKey, request)
                response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
                    ?: "Tidak ada respons dari model."
            } catch (e: SocketTimeoutException) {
                // Spesifik menangani timeout
                "Gagal terhubung: Waktu tunggu habis. Silakan coba beberapa saat lagi."
            } catch (e: IOException) {
                // Menangani masalah jaringan umum
                "Kesalahan jaringan: ${e.message}"
            } catch (e: Exception) {
                // Menangani error tak terduga lainnya
                "Terjadi kesalahan: ${e.localizedMessage}"
            }
        }
    }
}
```

---

## Tantangan Nyata: Mengapa Fase Produksi Jauh Lebih Rumit?

Mengonfigurasi *timeout* pada level lokal seperti di atas memang menyelesaikan masalah teknis instan saat proses *debugging* di emulator Anda. Namun, membawa proyek aplikasi AI dari sekadar prototipe di Google AI Studio hingga menjadi aplikasi siap rilis (produksi) di Google Play Store menyimpan kompleksitas yang kerap kali membuat pengembang pemula frustrasi.

Beberapa kendala besar yang akan Anda hadapi meliputi:
*   **Keamanan API Key:** Menyimpan API Key Google AI Studio langsung di dalam kode aplikasi (*hardcoded*) sangat berbahaya karena mudah didekompilasi menggunakan teknik *reverse engineering*.
*   **Arsitektur DevOps yang Rumit:** Untuk mengamankan API Key, Anda harus membangun *Middle-tier Server* atau memanfaatkan arsitektur *Serverless* (seperti Firebase Cloud Functions). Ini berarti Anda harus mengelola *environment variables*, CI/CD pipelines, dan konfigurasi server tambahan.
*   **Skalabilitas & Rate Limiting:** Mengelola kuota API, menangani error HTTP 429 (Too Many Requests), dan menerapkan mekanisme *exponential backoff* yang dinamis agar aplikasi tidak mendadak macet saat diakses oleh ribuan pengguna secara bersamaan.

Bagi pemula atau tim kecil yang fokus utamanya adalah menghadirkan produk dengan cepat ke pasar, mengurusi tumpukan teknologi DevOps, arsitektur *backend* penyelamat API Key, hingga optimasi performa jaringan ini sering kali menjadi hambatan besar yang memakan waktu berbulan-bulan.