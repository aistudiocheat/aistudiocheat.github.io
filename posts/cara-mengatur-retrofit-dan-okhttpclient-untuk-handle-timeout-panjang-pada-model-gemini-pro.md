---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-11-10"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

# Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro

Integrasi *Large Language Model* (LLM) seperti **Google Gemini Pro** ke dalam aplikasi Android menawarkan kapabilitas AI yang luar biasa, mulai dari pemrosesan teks tingkat lanjut hingga analisis kode. Namun, pengembang Android sering kali berhadapan dengan masalah klasik saat berinteraksi dengan API AI: **`java.net.SocketTimeoutException`**.

Berbeda dengan REST API standar yang mengembalikan respon JSON berukuran kecil dalam hitungan milidetik, Gemini Pro membutuhkan waktu lebih lama untuk memproses *prompt* yang kompleks dan menghasilkan *output* teks yang panjang (*token generation*).

Secara *default*, library `OkHttpClient` hanya memberikan batas waktu (*timeout*) sekitar 10 detik. Jika Gemini Pro membutuhkan waktu 30 detik untuk berpikir, aplikasi Anda akan otomatis *crash* atau *error*. 

Dalam artikel ini, kita akan membahas cara mengonfigurasi **OkHttpClient** dan **Retrofit** secara tepat agar mampu menangani *timeout* panjang pada model Gemini Pro dengan aman dan efisien.

---

## Mengapa Gemini Pro Membutuhkan Timeout Lebih Panjang?

Sebelum masuk ke kode, penting untuk memahami tiga jenis *timeout* utama dalam OkHttpClient:

1. **`connectTimeout`**: Waktu maksimal yang dibutuhkan untuk membuat koneksi TCP awal ke server Google AI (biasanya cukup 15–30 detik).
2. **`writeTimeout`**: Waktu maksimal untuk mengirimkan data *request* (termasuk *payload* prompt atau gambar yang diunggah) ke server.
3. **`readTimeout`**: Waktu maksimal menunggu paket data masuk setelah koneksi terhubung. **Ini adalah poin krusial untuk Gemini Pro**, karena proses *reasoning* AI terjadi di fase ini.

---

## Langkah 1: Tambahkan Dependensi yang Dibutuhkan

Pastikan proyek Android Anda sudah menggunakan versi terbaru dari Retrofit, OkHttpClient, dan Kotlin Coroutines di berkas `build.gradle.kts` (Module :app):

```kotlin
dependencies {
    // Retrofit & Gson Converter
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // OkHttp Logging Interceptor (Opsional, untuk debugging)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Kotlin Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
```

---

## Langkah 2: Konfigurasi OkHttpClient dengan Custom Timeout

Kunci utama penanganan *timeout* panjang terletak pada instansiasi `OkHttpClient`. Kita akan meningkatkan nilai `readTimeout` dan `writeTimeout` hingga **60 sampai 120 detik**, tergantung pada kompleksitas *prompt* aplikasi Anda.

Buat sebuah berkas Kotlin, misalnya `NetworkModule.kt`:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkClient {

    private const val TIMEOUT_SECONDS = 90L // Durasi timeout disesuaikan (90 detik)

    fun provideOkHttpClient(apiKey: String): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // 1. Atur Timeout Panjang untuk Gemini Pro
            .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .writeTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
            
            // 2. Tambahkan Interceptor untuk Header API Key (Keamanan)
            .addInterceptor { chain ->
                val originalRequest = chain.request()
                val originalUrl = originalRequest.url

                // Menambahkan API Key secara otomatis ke Query Parameter
                val urlWithApiKey = originalUrl.newBuilder()
                    .addQueryParameter("key", apiKey)
                    .build()

                val newRequest = originalRequest.newBuilder()
                    .url(urlWithApiKey)
                    .build()

                chain.proceed(newRequest)
            }
            .addInterceptor(loggingInterceptor)
            .build()
    }
}
```

---

## Langkah 3: Integrasi OkHttpClient ke Retrofit Builder

Setelah `OkHttpClient` dikonfigurasi, langkah berikutnya adalah menyambungkannya ke *instance* Retrofit.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    fun getGeminiService(apiKey: String): GeminiApiService {
        val okHttpClient = NetworkClient.provideOkHttpClient(apiKey)

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient) // Memasang OkHttpClient yang sudah dikonfigurasi
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## Langkah 4: Buat API Interface untuk Gemini Pro

Buat interface `GeminiApiService.kt` untuk memanggil *endpoint* `generateContent`.

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path

// Model Request sederhahana
data class GeminiRequest(val contents: List<Content>)
data class Content(val parts: List<Part>)
data class Part(val text: String)

// Model Response sederhana
data class GeminiResponse(val candidates: List<Candidate>?)
data class Candidate(val content: Content?)

interface GeminiApiService {
    @POST("v1beta/models/gemini-1.5-pro:generateContent")
    suspend fun generateContent(
        @Body request: GeminiRequest
    ): Response<GeminiResponse>
}
```

---

## Langkah 5: Handling Timeout Exception dengan Graceful Error Handling

Meskipun *timeout* telah diperpanjang menjadi 90 detik, gangguan jaringan seluler tetap bisa menyebabkan koneksi terputus. Pastikan repository atau ViewModel Anda siap menangani `SocketTimeoutException` agar aplikasi tidak *force close*.

```kotlin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.SocketTimeoutException
import java.io.IOException

class GeminiRepository(private val apiService: GeminiApiService) {

    suspend fun askGemini(promptText: String): Result<String> {
        return withContext(Dispatchers.IO) {
            try {
                val request = GeminiRequest(
                    contents = listOf(Content(parts = listOf(Part(text = promptText))))
                )
                
                val response = apiService.generateContent(request)

                if (response.isSuccessful) {
                    val resultText = response.body()
                        ?.candidates?.firstOrNull()
                        ?.content?.parts?.firstOrNull()?.text
                        ?: "Tidak ada respon dari model."
                    Result.success(resultText)
                } else {
                    Result.failure(Exception("Error Code: ${response.code()} - ${response.message()}"))
                }
            } catch (e: SocketTimeoutException) {
                // Handling spesifik saat koneksi mengalami timeout
                Result.failure(Exception("Koneksi timeout. Gemini Pro membutuhkan waktu lebih lama untuk memproses permintaan Anda."))
            } catch (e: IOException) {
                // Handling masalah jaringan umum
                Result.failure(Exception("Gagal terhubung ke server. Periksa koneksi internet Anda."))
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
}
```

---

## Realita Mengembangkan Aplikasi AI: Dari Prototip ke Versi Produksi

Mengatur `readTimeout` pada OkHttpClient hanyalah satu dari sekian banyak konfigurasi teknis dasar saat bekerja dengan LLM di Android. 

Ketika Anda mencoba membawa *prototype* yang dibuat di **Google AI Studio** menjadi aplikasi komersial tingkat produksi (*production-grade*), kompleksitasnya akan meningkat secara drastis:

* **Masalah Keamanan Kunci API:** Menyimpan API Key langsung di dalam berkas Kotlin atau `BuildConfig` sangat berisiko di-decompile. Anda membutuhkan infrastruktur *Proxy Backend* atau *Serverless Architecture* untuk menyembunyikan kredensial tersebut.
* **Optimasi Streaming Response (Server-Sent Events):** Menunggu 90 detik hingga seluruh teks selesai dibuat membuat pengalaman pengguna (*UX*) menjadi buruk. Anda perlu mengimplementasikan *HTTP Streaming* (Retrofit + Flow/SSE) agar teks muncul secara bertahap (*typing effect*).
* **Manajemen Token & Cost:** Memastikan prompt tidak melebihi batas *token context window* serta mengimplementasikan *caching* respon agar biaya API tidak membengkak.
* **Konfigurasi Build & CI/CD DevOps:** Menyiapkan ProGuard/R8 obfuscation yang aman untuk Retrofit DTO, pengujian otomatis, hingga arsitektur *Clean Architecture* yang scalable.

Bagi banyak *developer* independen, tim kecil, atau perusahaan yang ingin fokus pada pengembangan fitur bisnis, rumitnya pengelolaan integrasi arsitektur AI, masalah *networking*, hingga arsitektur *DevOps* Android ini sering kali menyita waktu dan sumber daya yang sangat besar. Mengonfigurasi seluruh *stack* ini secara mandiri tanpa fondasi DevOps dan *mobile engineering* yang matang kerap memicu bug tak terduga saat rilis di Play Store.

---

## Kesimpulan

Mengatasi kendala *timeout* pada model Gemini Pro di Android memerlukan penyesuaian khusus pada layer jaringan `OkHttpClient` dengan meningkatkan batas `readTimeout` dan `writeTimeout`. Dipadukan dengan *exception handling* yang tepat di Coroutines, aplikasi Anda akan menjadi jauh lebih stabil saat memproses *prompt* berukuran besar.

Pastikan untuk selalu menguji performa koneksi aplikasi Anda di berbagai kondisi jaringan (3G, 4G, 5G, dan Wi-Fi lambat) guna memastikan *user experience* tetap optimal!