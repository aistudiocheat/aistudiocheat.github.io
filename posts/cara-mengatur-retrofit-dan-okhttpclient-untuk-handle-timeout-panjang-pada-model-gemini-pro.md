---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-09-09"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Large Language Model (LLM) seperti Gemini Pro ke dalam aplikasi Android native kini menjadi standar baru dalam menciptakan aplikasi yang cerdas. Namun, berbeda dengan REST API tradisional yang memberikan respon dalam hitungan milidetik, LLM membutuhkan waktu pemrosesan (*token generation*) yang jauh lebih lama, terutama saat menangani *prompt* kompleks, *multimodal* (gambar dan teks), atau *system instruction* yang panjang.

Secara default, **OkHttpClient** memiliki batas waktu (*timeout*) sebesar 10 detik. Jika Anda menggunakan konfigurasi default ini untuk memanggil API Gemini Pro, aplikasi Anda akan sangat sering mengalami `java.net.SocketTimeoutException`. 

Artikel ini akan membahas secara mendalam cara mengonfigurasi Retrofit dan OkHttpClient agar dapat menangani *response time* yang panjang dari Gemini Pro secara aman dan efisien.

---

## Mengapa Gemini Pro Membutuhkan Timeout Lebih Panjang?

Sebelum masuk ke kode, penting untuk memahami *bottleneck* yang terjadi. Model Gemini Pro bekerja dengan cara melakukan *streaming* atau menghasilkan seluruh teks sebelum mengirimkannya kembali ke klien. Proses ini melibatkan:

1. **Pre-processing & Tokenization:** Menganalisis input pengguna.
2. **Model Inference:** Menghasilkan token demi token secara berurutan.
3. **Safety Filtering:** Memeriksa konten terhadap kebijakan keamanan Google AI.

Untuk *prompt* yang kompleks, proses ini bisa memakan waktu antara **15 hingga 45 detik**. Oleh karena itu, kita harus menaikkan ambang batas *timeout* pada jaringan aplikasi Android kita.

---

## Langkah 1: Menambahkan Dependensi yang Diperlukan

Pastikan Anda telah menambahkan dependensi Retrofit dan OkHttp terbaru di dalam file `build.gradle` (Module: app) Anda:

```kotlin
dependencies {
    // Retrofit
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")

    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
}
```

---

## Langkah 2: Mengonfigurasi OkHttpClient dengan Timeout Kustom

Kunci dari penyelesaian masalah *timeout* ini terletak pada konfigurasi `OkHttpClient`. Kita perlu mengatur tiga parameter utama:
* **Connect Timeout:** Waktu maksimal untuk membangun koneksi dengan server Google.
* **Read Timeout:** Waktu maksimal untuk menunggu data masuk (ini yang paling krusial untuk LLM).
* **Write Timeout:** Waktu maksimal untuk mengirimkan data (penting jika Anda mengirim gambar berukuran besar ke Gemini Pro).

Berikut adalah cara membuat *instance* `OkHttpClient` dengan konfigurasi yang direkomendasikan (60 detik):

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object HttpClientProvider {

    fun provideOkHttpClient(): OkHttpClient {
        // Logging interceptor untuk mempermudah debugging proses development
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur timeout menjadi 60 detik (1 menit)
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .addInterceptor(loggingInterceptor)
            .retryOnConnectionFailure(true) // Mencoba kembali jika koneksi sempat terputus
            .build()
    }
}
```

---

## Langkah 3: Membuat Retrofit Service untuk Gemini API

Setelah `OkHttpClient` siap, kita bisa menyematkannya ke dalam `Retrofit.Builder`. Mari kita buat interface API untuk Gemini Pro sesuai dengan spesifikasi Google AI Studio.

### 1. Definisikan Model Data (Request & Response)

```kotlin
// Request Model
data class GeminiRequest(
    val contents: List<Content>
)

data class Content(
    val parts: List<Part>
)

data class Part(
    val text: String
)

// Response Model sederhana
data class GeminiResponse(
    val candidates: List<Candidate>?
)

data class Candidate(
    val content: Content?
)
```

### 2. Definisikan Interface Retrofit

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

interface GeminiApiService {
    @POST("v1beta/models/gemini-pro:generateContent")
    async fun generateContent(
        @Query("key") apiKey: String,
        @Body request: GeminiRequest
    ): Response<GeminiResponse>
}
```

### 3. Inisialisasi Retrofit Client

Sekarang, hubungkan `OkHttpClient` yang sudah kita kustomisasi tadi ke dalam konfigurasi Retrofit:

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson:GsonConverterFactory

object RetrofitClient {
    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val geminiService: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(HttpClientProvider.provideOkHttpClient()) // Menggunakan OkHttpClient kustom
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Menangani Error Timeout di Sisi UI/Repository

Meskipun kita sudah memperpanjang *timeout* menjadi 60 detik, skenario buruk seperti jaringan pengguna yang sangat lambat (misalnya di area 3G) tetap dapat memicu `SocketTimeoutException`. Kita harus menangani exception ini dengan elegan agar aplikasi tidak *crash*.

Berikut adalah contoh implementasi pemanggilan API di dalam Repository atau ViewModel menggunakan blok `try-catch` Kotlin Coroutines:

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

                if (response.isSuccessful) {
                    response.body()?.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
                        ?: "Tidak ada respon yang dihasilkan."
                } else {
                    "Error: ${response.code()} - ${response.errorBody()?.string()}"
                }
            } catch (e: SocketTimeoutException) {
                // Penanganan khusus untuk masalah timeout
                "Koneksi timeout. Server Gemini membutuhkan waktu terlalu lama untuk merespon. Silakan coba lagi."
            } catch (e: IOException) {
                // Penanganan untuk masalah jaringan umum (misal: tidak ada internet)
                "Gagal terhubung ke internet. Periksa koneksi Anda."
            } catch (e: Exception) {
                "Terjadi kesalahan sistem: ${e.localizedMessage}"
            }
        }
    }
}
```

---

## Dari Prototype ke Produksi: Tantangan Nyata Developer Android

Mengonfigurasi *timeout* pada Retrofit dan OkHttpClient di atas kertas tampak seperti solusi yang sederhana. Namun, saat Anda mulai melangkah keluar dari fase *sandbox* (Google AI Studio) dan bersiap merilis aplikasi berbasis kecerdasan buatan ini ke Google Play Store untuk ribuan pengguna, Anda akan menyadari bahwa realitas pengembangan aplikasi AI jauh lebih kompleks.

Bagi pemula, menyulap sebuah kode *prototype* sederhana dari Google AI Studio menjadi aplikasi kelas produksi (*production-grade*) sering kali terasa sangat membingungkan dan melelahkan. Anda harus memikirkan banyak variabel arsitektur yang rumit, seperti:

* **Keamanan API Key:** Menyimpan API Key langsung di dalam kode Android sangat rawan didekompilasi oleh pihak tidak bertanggung jawab. Bagaimana cara mengamankannya menggunakan arsitektur *backend-proxy* atau enkripsi tingkat tinggi?
* **Manajemen State UI:** Bagaimana cara menangani transisi UI, indikator *loading* yang interaktif selama 60 detik proses inferensi, hingga penanganan skenario *re-connection* tanpa merusak pengalaman pengguna (*UX*)?
* **Cost & Rate Limiting:** Bagaimana cara melacak penggunaan token agar tagihan API tidak membengkak secara tidak terduga?
* **DevOps & CI/CD:** Bagaimana mengotomatisasi pengujian, memastikan performa jaringan tetap stabil di berbagai versi OS Android, dan mengelola *environment variable* (Development, Staging, Production)?

Tantangan-tantangan teknis inilah yang sering kali membuat peluncuran aplikasi tertunda berbulan-bulan atau bahkan gagal total di tengah jalan akibat arsitektur dasar yang rapuh.

Jika Anda sedang membangun aplikasi Android berbasis Gemini API dan ingin memastikan aplikasi Anda tidak hanya berfungsi secara lokal, tetapi juga aman, skalabel, memiliki performa optimal di jaringan buruk, serta siap pakai untuk pasar massal, berkolaborasi dengan ahli di bidang Android DevOps dan sistem integrasi adalah langkah strategis terbaik untuk menghemat waktu dan biaya pengembangan Anda.