---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-11-20"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan Large Language Model (LLM) seperti **Google Gemini Pro** ke dalam aplikasi Android menawarkan kapabilitas AI yang luar biasa. Namun, dari sudut pandang arsitektur jaringan, model AI generatif memiliki karakteristik yang sangat berbeda dibandingkan REST API konvensional.

Jika API standar biasanya memberikan respons dalam hitungan milidetik, model Gemini Pro yang memproses *prompt* kompleks, analisis dokumen, atau *multimodal input* bisa membutuhkan waktu beberapa detik hingga puluhan detik untuk menghasilkan respons lengkap.

Secara *default*, HTTP client di Android seperti **OkHttpClient** memiliki durasi *timeout* sebesar 10 detik. Jika permintaan ke Gemini Pro melebihi batas ini, aplikasi Anda akan mengalami `java.net.SocketTimeoutException`. 

Artikel ini akan membahas secara mendalam cara mengonfigurasi **Retrofit** dan **OkHttpClient** di Kotlin untuk menangani durasi *timeout* yang panjang secara aman dan efisien.

---

## Mengapa Gemini Pro Membutuhkan Konfigurasi Timeout Khusus?

Saat mengirimkan permintaan ke Gemini API via HTTP, ada empat jenis *timeout* pada OkHttpClient yang perlu dipahami:

1. **`connectTimeout`**: Waktu maksimum untuk membuat koneksi TCP dengan server Google.
2. **`readTimeout`**: Waktu maksimum jeda antara dua paket data yang diterima dari server. Ini adalah poin paling kritis saat menunggu pemrosesan token LLM.
3. **`writeTimeout`**: Waktu maksimum untuk mengirimkan *request body* (misalnya gambar berukuran besar pada Gemini Pro Vision/Multimodal).
4. **`callTimeout`**: Batas waktu total untuk seluruh siklus HTTP (mulai dari DNS lookup, koneksi, hingga respons selesai dibaca).

Untuk model Gemini Pro, nilai *default* (10 detik) sangat tidak cukup. Anda perlu menaikkan nilai `readTimeout` dan `callTimeout` secara spesifik.

---

## Langkah 1: Menambahkan Dependensi yang Dibutuhkan

Pastikan proyek Android Anda sudah menggunakan dependensi Retrofit dan OkHttpClient terbaru pada file `build.gradle.kts` (Module :app):

```kotlin
dependencies {
    // Retrofit & Converter
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Kotlin Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
```

---

## Langkah 2: Mengonfigurasi Custom OkHttpClient

Langkah paling krusial adalah membuat *instance* `OkHttpClient` dengan durasi *timeout* yang sudah disesuaikan untuk kebutuhan *LLM processing*. 

Di sini kita menetapkan `readTimeout` hingga **60 - 90 detik** untuk mengantisipasi *generation time* yang panjang dari Gemini Pro.

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkModule {

    private fun provideLoggingInterceptor(): HttpLoggingInterceptor {
        return HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
    }

    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            // Menetapkan koneksi TCP maksimal 30 detik
            .connectTimeout(30, TimeUnit.SECONDS)
            
            // Menetapkan batas kirim data (bermanfaat untuk payload gambar/file besar)
            .writeTimeout(30, TimeUnit.SECONDS)
            
            // Menetapkan batas waktu tunggu respons dari Gemini Pro (diperpanjang)
            .readTimeout(90, TimeUnit.SECONDS)
            
            // Batas total siklus request (opsional, sesuaikan dengan kasus penggunaan)
            .callTimeout(120, TimeUnit.SECONDS)
            
            // Menambahkan logging untuk debugging di lingkungan development
            .addInterceptor(provideLoggingInterceptor())
            
            // Otomatis mencoba kembali jika ada kegagalan koneksi transien
            .retryOnConnectionFailure(true)
            .build()
    }
}
```

---

## Langkah 3: Menghubungkan OkHttpClient ke Retrofit Builder

Setelah `OkHttpClient` siap, pasangkan *instance* tersebut ke `Retrofit.Builder`.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val instance: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(NetworkModule.provideOkHttpClient()) // Memasang custom OkHttpClient
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
}
```

---

## Langkah 4: Membuat Service Interface untuk Gemini API

Berikut adalah contoh pembuatan interface Retrofit untuk memanggil endpoint Gemini Pro:

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

// Model sederhana untuk Request & Response
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

## Langkah 5: Handling Timeout Exception pada Level Repository/ViewModel

Meskipun *timeout* sudah diperpanjang, aplikasi tetap harus siap menangani skenario buruk jika jaringan pengguna terputus (*SocketTimeoutException*). 

Gunakan blok `try-catch` yang spesifik pada layer Repository atau ViewModel:

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
                val textResponse = response.body()
                    ?.candidates?.firstOrNull()
                    ?.content?.parts?.firstOrNull()?.text
                    ?: "Tidak ada respons dari model."
                Result.success(textResponse)
            } else {
                Result.failure(Exception("HTTP Error: ${response.code()} ${response.message()}"))
            }
        } catch (e: SocketTimeoutException) {
            // Menangani kustomisasi pesan saat timeout terjadi
            Result.failure(Exception("Proses membutuhkan waktu terlalu lama. Silakan coba lagi."))
        } catch (e: IOException) {
            // Menangani masalah koneksi internet secara umum
            Result.failure(Exception("Gagal terhubung ke server. Periksa koneksi internet Anda."))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

---

## Praktik Terbaik (Best Practices) DevOps & Android Integration

1. **Gunakan Streaming API jika memungkinkan**: Daripada menunggu seluruh blok teks selesai dibuat (yang memicu delay panjang), pertimbangkan untuk menggunakan endpoint *Server-Sent Events* (SSE) atau WebSockets untuk *streaming response* karakter demi karakter.
2. **Jangan Hardcode API Key**: Gunakan *Secrets Gradle Plugin* atau simpan API Key di *Native C/C++ Layer* (NDK) agar tidak mudah di-*decompile* oleh pihak yang tidak bertanggung jawab.
3. **UX Loading State yang Jelas**: Karena *latency* LLM tinggi, berikan indikator *loading* atau *shimmer effect* yang informatif kepada pengguna agar mereka tahu bahwa proses sedang berjalan.

---

## Tantangan Menuju Versi Production-Ready

Mengonfigurasi Retrofit untuk mengutip respons sederhana dari Google AI Studio di lingkungan *development* atau *prototype* memang terlihat mudah. Namun, membawa proyek aplikasi AI hingga benar-benar siap dirilis ke tingkat produksi (*production-ready*) menyajikan tantangan teknis yang jauh lebih rumit bagi banyak pengembang dan pemula.

Beberapa kendala kompleks yang sering ditemui di lapangan antara lain:

* **Arsitektur Keamanan API Key**: Melindungi API Key agar tidak bocor dari reverse engineering aplikasi Android.
* **Dynamic Timeout & Retry Exponential Backoff**: Mengatur strategi *retry logic* yang cerdas tanpa membebani kuota API atau merusak pengalaman pengguna (*User Experience*).
* **Manajemen State Coroutines & Memory Leak**: Menangani pergantian orientasi layar (*configuration changes*) saat proses pembuatan respons AI sedang berlangsung.
* **Integrasi CI/CD & Obfuscation (ProGuard/R8)**: Memastikan kode terenkripsi dengan aman tanpa merusak struktur serialization JSON Retrofit saat *build release*.

Jika Anda mengalami keterbatasan waktu, rumitnya konfigurasi jaringan Android DevOps, atau ingin memastikan arsitektur aplikasi AI Anda dibuat dengan standar keamanan dan performa terbaik industri, bekerja sama dengan profesional berpengalaman adalah langkah strategis terbaik untuk mempercepat rilis produk Anda ke pasar.

---

## Kesimpulan

Menangani *latency* tinggi dari model AI seperti Gemini Pro membutuhkan penyesuaian khusus pada konfigurasi networking layer Android Anda. Dengan menyesuaikan durasi `readTimeout` dan `callTimeout` pada OkHttpClient serta menerapkan *error handling* yang tepat pada Retrofit, aplikasi Android Anda akan jauh lebih stabil dan bebas dari *crash* akibat *timeout exception*.