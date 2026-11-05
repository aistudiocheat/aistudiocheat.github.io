---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-11-05"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan *Large Language Model* (LLM) seperti Google Gemini Pro ke dalam aplikasi Android native memberikan kemampuan AI yang luar biasa. Namun, tidak seperti REST API tradisional yang merespons dalam hitungan milidetik, model AI generatif sering kali membutuhkan waktu pemrosesan yang jauh lebih lama—terutama saat menangani *prompt* yang kompleks, analisis dokumen, atau *multimodal input* (teks + gambar/video).

Secara *default*, pustaka jaringan populer di Android seperti **OkHttpClient** menetapkan batas waktu (*timeout*) standar sebesar **10 detik**. Jika model Gemini Pro membutuhkan waktu 15–30 detik untuk merangkai respons, aplikasi Anda akan secara otomatis melempar `java.net.SocketTimeoutException`.

Artikel ini akan membahas secara mendalam cara mengonfigurasi **Retrofit** dan **OkHttpClient** agar tangguh menangani *response time* yang panjang dari API Gemini Pro.

---

## Memahami 4 Jenis Timeout pada OkHttpClient

Sebelum masuk ke implementasi kode, penting untuk memahami empat jenis konfigurasi *timeout* yang disediakan oleh `OkHttpClient`:

1. **`connectTimeout`**: Waktu maksimum yang dialokasikan untuk membuat koneksi awal ke *server* (TCP handshake).
2. **`readTimeout`**: Waktu maksimum menunggu paket data diterima setelah koneksi terhubung. Ini adalah variabel **paling krusial** untuk API LLM seperti Gemini Pro.
3. **`writeTimeout`**: Waktu maksimum yang dibutuhkan untuk mengirimkan *request body* ke *server* (sangat berpengaruh jika Anda mengunggah gambar/file besar ke Gemini).
4. **`callTimeout`**: Batas waktu total untuk seluruh eksekusi HTTP *call* (mulai dari DNS lookup hingga membaca respons selesai).

---

## Langkah 1: Menambahkan Dependensi yang Dibutuhkan

Pastikan Anda telah menambahkan pustaka Retrofit, OkHttp, dan Kotlin Coroutines pada berkas `build.gradle.kts` (Module :app):

```kotlin
dependencies {
    // Retrofit & Converter
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0") // atau Moshi

    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Kotlin Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
```

---

## Langkah 2: Mengatur OkHttpClient dengan Timeout Kustom

Untuk menangani latensi tinggi dari model Gemini Pro, disarankan untuk memperpanjang `readTimeout` dan `writeTimeout` setidaknya hingga **60 sampai 120 detik**.

Berikut adalah implementasi konfigurasi `OkHttpClient`:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkModule {

    private const val TIMEOUT_DURATION = 90L // Waktu timeout dalam detik

    fun provideOkHttpClient(): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur waktu tunggu koneksi awal
            .connectTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            // Mengatur waktu tunggu membaca respons dari Gemini Pro
            .readTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            // Mengatur waktu tunggu pengiriman data (misal: upload gambar/prompt besar)
            .writeTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            // Menambahkan interceptor untuk logging saat debugging
            .addInterceptor(loggingInterceptor)
            // Menambahkan Header API Key jika diperlukan secara terpusat
            .addInterceptor { chain ->
                val originalRequest = chain.request()
                val requestBuilder = originalRequest.newBuilder()
                    .header("Content-Type", "application/json")
                chain.proceed(requestBuilder.build())
            }
            .build()
    }
}
```

---

## Langkah 3: Mengintegrasikan OkHttpClient ke Retrofit Instance

Setelah `OkHttpClient` berhasil dikonfigurasi, suntikkan (*inject*) *client* tersebut ke dalam *builder* Retrofit.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val instance: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(NetworkModule.provideOkHttpClient()) // Memakai OkHttpClient kustom
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Membuat API Interface untuk Gemini Pro

Definisikan *endpoint* Google AI Studio pada interface Retrofit menggunakan fungsi *suspend* agar berjalan secara *asynchronous* menggunakan Coroutines.

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

// Data Class Sederhana untuk Payload Gemini
data class GeminiRequest(val contents: List<Content>)
data class Content(val parts: List<Part>)
data class Part(val text: String)

data class GeminiResponse(val candidates: List<Candidate>?)
data class Candidate(val content: Content?)

interface GeminiApiService {

    @POST("v1beta/models/gemini-1.5-pro:generateContent")
    suspend fun generateContent(
        @Query("key") apiKey: String,
        @Body request: GeminiRequest
    ): Response<GeminiResponse>
}
```

---

## Langkah 5: Handling Timeout dan Error di Layer Repository

Memperpanjang *timeout* tidak menjamin jaringan selalu stabil. Di Android, kita tetap harus menangani skenario ketika koneksi terputus atau melebihi batas waktu melalui blok `try-catch`.

```kotlin
import java.net.SocketTimeoutException
import java.io.IOException

class GeminiRepository(private val apiService: GeminiApiService) {

    suspend fun askGemini(prompt: String, apiKey: String): Result<String> {
        return try {
            val request = GeminiRequest(
                contents = listOf(Content(parts = listOf(Part(text = prompt))))
            )
            val response = apiService.generateContent(apiKey, request)

            if (response.isSuccessful) {
                val text = response.body()
                    ?.candidates?.firstOrNull()
                    ?.content?.parts?.firstOrNull()?.text
                Result.success(text ?: "Tidak ada respons dari model.")
            } else {
                Result.failure(Exception("HTTP Error: ${response.code()} ${response.message()}"))
            }
        } catch (e: SocketTimeoutException) {
            // Error khusus jika timeout tetap terjadi
            Result.failure(Exception("Koneksi timeout. Model Gemini butuh waktu lebih lama untuk merespons."))
        } catch (e: IOException) {
            // Error koneksi internet/jaringan umum
            Result.failure(Exception("Gagal terhubung ke server. Periksa koneksi internet Anda."))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

---

## Praktik Terbaik DevOps & Keamanan dalam Penanganan API Gemini

1. **Gunakan Server-Sent Events (SSE) / Streaming:**  
   Daripada menunggu seluruh teks selesai dibuat (`generateContent`), gunakan *endpoint* `streamGenerateContent` agar respons dikirimkan secara bertahap (chunk). Ini membuat *user interface* (UI) terasa jauh lebih responsif.
2. **Jangan Hardcode API Key:**  
   Simpan API Key di berkas `local.properties` dan panggil melalui `BuildConfig` atau gunakan plugin *Secrets Gradle*.
3. **Atur Policy Re-try:**  
   Gunakan pustaka seperti Resilience4j atau *custom interceptor* untuk melakukan *exponential backoff* jika mendapatkan *HTTP status code* `429` (Rate Limit) atau `503` (Service Unavailable).

---

## Dari Prototype Google AI Studio ke Production: Tantangan Nyata Pengembang

Mengatur durasi *timeout* pada Retrofit dan OkHttpClient secara teknis terbilang sederhana. Namun, **membawa integrasi Google AI Studio dari tahap *prototype* sederhana hingga siap dirilis ke *production* (Google Play Store) adalah cerita yang sangat berbeda.**

Banyak *developer* dan tim produk pemula yang terjebak pada kompleksitas tingkat lanjut seperti:

* **Manajemen Keamanan API Key:** Menyimpan API Key langsung di dalam kode aplikasi Android sangat berisiko terkena *reverse-engineering*. Solusi aman membutuhkan *Backend Proxy* (seperti Firebase Cloud Functions atau Node.js middleware) yang harus dirancang dari nol.
* **Integrasi Streaming UI (Server-Sent Events):** Mengubah *flow* Retrofit dari HTTP standar menjadi *streaming data* secara *real-time* ke Jetpack Compose atau XML View.
* **Arsitektur CI/CD dan DevOps:** Mengatur otomasi *build*, pengujian integrasi AI, serta strategi *caching* respons agar biaya penggunaan Token API Gemini tidak membengkak.
* **Optimalisasi Retain State & Lifecycle:** Menangani *screen rotation* atau kondisi *app process death* saat aplikasi sedang menunggu respons AI yang lama.

Memahami semua konfigurasi *networking*, skema arsitektur *clean code*, hingga pipeline DevOps secara mandiri sering kali memakan waktu berminggu-minggu dan berpotensi menunda peluncuran produk Anda ke pasar.

---

## Kesimpulan

Mengatasi kendala *timeout* pada model Gemini Pro di Android memerlukan penyesuaian khusus pada komponen `OkHttpClient` di dalam pustaka Retrofit. Dengan meningkatkan `readTimeout` dan `writeTimeout` serta menerapkan *exception handling* yang tepat, aplikasi Android Anda dapat memproses *prompt* berukuran besar secara stabil tanpa terkendala *crash* akibat `SocketTimeoutException`.