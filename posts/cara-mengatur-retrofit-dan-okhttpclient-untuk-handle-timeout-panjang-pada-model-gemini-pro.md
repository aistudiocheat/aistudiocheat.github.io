---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-10-11"
excerpt: "Pelajari panduan practical mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Model bahasa besar (Large Language Model / LLM) seperti **Gemini Pro** dari Google AI Studio telah mengubah cara kita membangun aplikasi Android yang cerdas. Namun, berbeda dengan REST API tradisional yang umumnya mengembalikan respon JSON dalam hitungan milidetik, Gemini Pro membutuhkan waktu lebih lama untuk memproses *prompt* yang kompleks, melakukan *reasoning*, hingga menghasilkan *long-form content* atau analisis multimodal (teks, gambar, dan video).

Secara bawaan (*default*), library networking standar Android seperti **OkHttpClient** menetapkan batas waktu (*timeout*) sebesar 10 detik. Jika aplikasi Anda mengirimkan prompt yang kompleks ke Gemini Pro, besar kemungkinan request akan terputus di tengah jalan dan melemparkan error `java.net.SocketTimeoutException`.

Dalam artikel ini, kita akan membahas secara mendalam cara mengonfigurasi **Retrofit** dan **OkHttpClient** agar mampu menangani *latency* tinggi dan *timeout* panjang dari model Gemini Pro secara stabil dan elegan.

---

## Memahami Jenis-Jenis Timeout pada OkHttpClient

Sebelum masuk ke kode, penting untuk memahami 4 jenis parameter *timeout* yang disediakan oleh `OkHttpClient.Builder`:

1. **`connectTimeout`**: Batas waktu untuk membuka koneksi TCP ke server Google AI (URL endpoint API).
2. **`writeTimeout`**: Batas waktu untuk mengirimkan payload data (seperti prompt teks panjang atau upload gambar/video ke Gemini).
3. **`readTimeout`**: Batas waktu menunggu data/respon masuk dari server untuk setiap *packet*. **Ini adalah parameter paling krusial untuk Gemini Pro.**
4. **`callTimeout`**: Batas total durasi keseluruhan eksekusi *request* HTTP, mulai dari DNS lookup hingga respon selesai dibaca sepenuhnya.

---

## Langkah 1: Menambahkan Dependensi Retrofit & OkHttp

Pastikan file `build.gradle.kts` (Module :app) Anda sudah mencakup library Retrofit dan OkHttp versi terbaru:

```kotlin
dependencies {
    // Retrofit untuk Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
}
```

---

## Langkah 2: Mengatur OkHttpClient dengan Timeout yang Disesuaikan

Untuk menangani respon Gemini Pro yang berat, kita perlu menaikkan nilai `readTimeout`, `writeTimeout`, dan `callTimeout` secara signifikan (misalnya hingga 2 atau 3 menit).

Berikut contoh konfigurasi kelas penyedia HTTP client (`NetworkModule.kt`):

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkModule {

    private fun createOkHttpClient(): OkHttpClient {
        // Interceptor untuk memantau log lalu lintas data (opsional untuk debugging)
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur koneksi TCP awal (biasanya 30 detik cukup)
            .connectTimeout(30, TimeUnit.SECONDS)
            
            // Batas waktu mengirim data (misal: upload payload multimodal yang besar)
            .writeTimeout(60, TimeUnit.SECONDS)
            
            // PENTING: Beri waktu ekstra bagi Gemini Pro untuk berpikir & memproses generasi teks
            .readTimeout(120, TimeUnit.SECONDS) 
            
            // Batas maksimal total durasi untuk satu siklus API Call
            .callTimeout(180, TimeUnit.SECONDS)
            
            // Menambahkan interceptor
            .addInterceptor(loggingInterceptor)
            
            // Otomatis mencoba ulang jika terjadi kegagalan koneksi di tingkat jaringan
            .retryOnConnectionFailure(true)
            .build()
    }

    fun getOkHttpClient(): OkHttpClient = createOkHttpClient()
}
```

---

## Langkah 3: Mengintegrasikan OkHttpClient ke Retrofit Instance

Setelah `OkHttpClient` siap, pasang instance tersebut ke dalam pembuatan objek Retrofit:

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val instance: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            // Memasang OkHttpClient kustom yang telah dikonfigurasi timeout-nya
            .client(NetworkModule.getOkHttpClient()) 
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Membuat Service Interface untuk Gemini API

Berikut contoh implementasi Retrofit Interface untuk memanggil endpoint model `gemini-1.5-pro`:

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

// Model Data Sederhana (Data Transfer Object)
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

## Langkah 5: Handling Timeout pada ViewModel atau Repository

Di lapisan arsitektur aplikasi (seperti ViewModel), selalu tangkap kemungkinan `SocketTimeoutException` agar aplikasi tidak mengalami *crash* dan pengguna mendapatkan pesan error yang jelas.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import java.net.SocketTimeoutException
import java.io.IOException

class GeminiViewModel : ViewModel() {

    fun askGemini(promptText: String) {
        viewModelScope.launch {
            try {
                val request = GeminiRequest(
                    contents = listOf(Content(parts = listOf(Part(text = promptText))))
                )

                val response = RetrofitClient.instance.generateContent(
                    apiKey = "YOUR_GEMINI_API_KEY",
                    request = request
                )

                if (response.isSuccessful) {
                    val resultText = response.body()?.candidates?.firstOrNull()
                        ?.content?.parts?.firstOrNull()?.text
                    // Tampilkan hasil ke UI
                } else {
                    // Handle Error HTTP (misal 400, 429 Too Many Requests, 500)
                }

            } catch (e: SocketTimeoutException) {
                // Beri tahu user bahwa pemrosesan memakan waktu terlalu lama
                showUiError("Proses pembuatan respon terlalu lama (Timeout). Silakan coba lagi.")
            } catch (e: IOException) {
                // Handle masalah koneksi internet lepas
                showUiError("Gagal terhubung ke server. Periksa koneksi internet Anda.")
            } catch (e: Exception) {
                showUiError("Terjadi kesalahan tidak terduga: ${e.message}")
            }
        }
    }

    private fun showUiError(message: String) {
        // Implementasi snackbar/toast/state error di sini
    }
}
```

---

## Rumitnya Menyiapkan Aplikasi AI Bertaraf Produksi

Mengonfigurasi timeout pada OkHttpClient di lingkungan lokal memang menyelesaikan masalah dasar pertukaran data API. Namun, membawa proyek berbasi **Google AI Studio** hingga siap dirilis ke tingkat **produksi (Production-Ready)** menyajikan tantangan teknis yang jauh lebih rumit, terutama bagi pengembang individu maupun tim kecil.

Beberapa kendala nyata yang sering dihadapi meliputi:

* **Keamanan API Key yang Rentan**: Menaruh API Key Google AI Studio langsung di dalam aplikasi Android—meskipun sudah memakai `BuildConfig` atau ProGuard—sangat mudah di-*reverse engineer* menggunakan tool dekompilasi APK seperti APKTool.
* **Arsitektur Server Proxy/BFF (Backend-For-Frontend)**: Mengharuskan pengembang membangun lapisan *middleware* backend untuk menyembunyikan API key, mengatur *rate limiting*, serta mengelola alokasi kuota user agar tidak membengkakkan tagihan Google Cloud Console.
* **Handling Streaming (SSE)**: Response biasa kerap membuat UX aplikasi terasa lambat ("loading lama"). Untuk UX yang lebih mutakhir, integrasi *Server-Sent Events (SSE)* / response *streaming* melalui Retrofit/OkHttp dengan coroutine flow sangat diperlukan, tetapi penanganannya terbilang rumit.
* **Integrasi CI/CD & Security Audit**: Konfigurasi otomatisasi *build* (seperti GitHub Actions), optimasi *Obfuscation*, hingga kepatuhan standar keamanan Android DevOps sering kali menyita waktu yang tidak sedikit dari fokus utama pengembangan fitur aplikasi.

---

## Kesimpulan

Menyesuaikan parameter `readTimeout` dan `callTimeout` pada OkHttpClient adalah langkah wajib jika Anda mengintegrasikan model AI berkemampuan tinggi seperti **Gemini Pro** ke dalam aplikasi Android. Nilai timeout bawaan sebesar 10 detik perlu dinaikkan hingga 2-3 menit agar proses *reasoning* LLM yang kompleks tidak terputus secara mendadak.

Meskipun demikian, integrasi teknis di sisi klien hanyalah puncak dari gunung es. Memastikan skema autentikasi aman, mengamankan arsitektur komunikasi, serta mengoptimalkan *pipelines* DevOps adalah kunci utama agar aplikasi berbasis Google AI Studio Anda tidak hanya canggih, tetapi juga aman, handal, dan dapat diandalkan oleh para pengguna di seluruh dunia.