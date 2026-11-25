---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-11-25"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Large Language Model (LLM) seperti **Gemini Pro** dari Google AI Studio ke dalam aplikasi Android menawarkan kemampuan pemrosesan bahasa alami yang luar biasa. Namun, dari sudut pandang arsitektur jaringan (*networking*), integrasi AI memiliki karakteristik yang sangat berbeda dibandingkan REST API konvensional.

Model AI seperti Gemini Pro membutuhkan waktu lebih lama untuk melakukan inferensi, terutama saat memproses *prompt* yang kompleks, *context window* yang besar, atau saat menghasilkan respons teks yang panjang. Secara *default*, pustaka HTTP client di Android seperti **OkHttpClient** menetapkan batas waktu (*timeout*) sebesar **10 detik**. Waktu ini sering kali tidak cukup, sehingga aplikasi melempar `java.net.SocketTimeoutException`.

Artikel ini akan membahas secara mendalam cara mengonfigurasi **Retrofit** dan **OkHttpClient** di Android untuk menangani *timeout* panjang saat berkomunikasi dengan API Gemini Pro secara stabil dan efisien.

---

## 1. Mengapa Gemini Pro Membutuhkan Konfigurasi Timeout Khusus?

Saat memanggil REST API standar (misalnya mengambil profil pengguna), server biasanya merespons dalam hitungan milidetik. Namun, pada API Gemini Pro:

1. **Time to First Token (TTFT):** Server memerlukan waktu untuk memproses konteks awal sebelum mulai merespons.
2. **Generasi Respons Berulang:** Pemrosesan token dilakukan secara bertahap. Jika teks output sangat panjang, koneksi HTTP harus tetap terbuka (*keep-alive*) sampai seluruh payload selesai ditransfer.
3. **Kondisi Jaringan Ponsel:** Pada perangkat seluler, latensi jaringan yang fluktuatif dapat memperburuk total waktu transmisi data.

Untuk mengatasi ini, kita perlu menyesuaikan empat parameter utama pada OkHttpClient:
* **`connectTimeout`**: Batas waktu untuk membuat koneksi awal ke server.
* **`readTimeout`**: Batas waktu untuk menunggu paket data masuk setelah koneksi terhubung.
* **`writeTimeout`**: Batas waktu untuk mengirimkan request payload (misalnya teks prompt yang besar).
* **`callTimeout`**: Batas waktu total untuk seluruh eksekusi HTTP request.

---

## 2. Menambahkan Dependensi Gradle

Pastikan proyek Android Anda sudah menyertakan dependensi Retrofit dan OkHttp terbaru pada file `build.gradle.kts` (Module :app):

```kotlin
dependencies {
    // Retrofit
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    
    // Coroutines (Opsional, untuk asynchronous call)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
```

---

## 3. Konfigurasi OkHttpClient dengan Durasi Timeout yang Disesuaikan

Langkah utama untuk mencegah `SocketTimeoutException` adalah menaikkan batas durasi *read* dan *write* pada `OkHttpClient`. Untuk Gemini Pro, durasi **60 hingga 120 detik** adalah standar yang aman untuk request non-streaming.

Berikut adalah implementasi singleton builder untuk `OkHttpClient`:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkClient {

    private const val TIMEOUT_DURATION = 90L // Durasi dalam detik

    fun provideOkHttpClient(): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur timeout khusus Gemini Pro
            .connectTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            .readTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            .writeTimeout(TIMEOUT_DURATION, TimeUnit.SECONDS)
            .callTimeout(120L, TimeUnit.SECONDS) // Total alokasi waktu request
            
            // Mekanisme retry otomatis jika terjadi kegagalan jaringan sementara
            .retryOnConnectionFailure(true)
            .addInterceptor(loggingInterceptor)
            .build()
    }
}
```

---

## 4. Mengabungkan OkHttpClient ke dalam Retrofit Instance

Setelah `OkHttpClient` siap, hubungkan klien tersebut ke instance **Retrofit**.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val instance: GeminiApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(NetworkClient.provideOkHttpClient()) // Memasang custom OkHttpClient
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GeminiApiService::class.java)
    }
}
```

---

## 5. Membuat Interface API dan Menangani Request

Buat interface Retrofit untuk memanggil endpoint model Gemini Pro (`gemini-1.5-pro` atau versi yang sesuai).

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

// Data structure untuk request dan response
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

## 6. Contoh Implementasi di Repository/ViewModel

Gunakan eksekusi berbasis Kotlin Coroutines dengan menangani potensi exception secara eksplisit:

```kotlin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.SocketTimeoutException

class GeminiRepository {

    private val apiService = RetrofitClient.instance

    suspend fun askGemini(apiKey: String, promptText: String): Result<String> {
        return withContext(Dispatchers.IO) {
            try {
                val request = GeminiRequest(
                    contents = listOf(Content(parts = listOf(Part(text = promptText))))
                )
                
                val response = apiService.generateContent(apiKey, request)

                if (response.isSuccessful) {
                    val textOutput = response.body()
                        ?.candidates?.firstOrNull()
                        ?.content?.parts?.firstOrNull()?.text
                    
                    if (textOutput != null) {
                        Result.success(textOutput)
                    } else {
                        Result.failure(Exception("Respons kosong dari model."))
                    }
                } else {
                    Result.failure(Exception("Error HTTP: ${response.code()} ${response.message()}"))
                }
            } catch (e: SocketTimeoutException) {
                // Timeout masih terjadi jika koneksi terputus total
                Result.failure(Exception("Koneksi timeout. Pemrosesan Gemini memerlukan waktu lebih lama. Coba lagi."))
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
}
```

---

## Rumitnya Membawa Proyek Google AI Studio ke Level Production

Menyesuaikan parameter `readTimeout` dan `writeTimeout` di tingkat kode aplikasi Android hanyalah langkah awal dalam pengintegrasian AI. Bagi para pemula atau tim kecil, mengonfigurasi proyek yang awalnya dibuat secara sederhana di Google AI Studio hingga menjadi aplikasi Android tingkat produksi (*production-grade*) terbukti menyimppan tingkat kerumitan teknis yang sangat tinggi.

Beberapa tantangan arsitektural dan DevOps yang sering dihadapi meliputi:

1. **Keamanan API Key:** Menyimpan API Key Google AI Studio langsung di dalam aplikasi Android (*client-side*) sangat berisiko terkena *reverse engineering*. Aplikasi membutuhkan arsitektur backend perantara (*Backend-for-Frontend* / BFF) atau konfigurasi *proxy* yang aman.
2. **Manajemen Rate Limiting dan Quota:** Tanpa infrastruktur pembatas (*rate limiter*) dan antrean (*queue system*) di server, aplikasi Anda dapat mengalami kegagalan massal saat lonjakan pengguna terjadi.
3. **Handling Server-Sent Events (SSE) / Streaming:** Untuk pengalaman pengguna yang interaktif, Anda perlu mengimplementasikan *response streaming* menggunakan Retrofit + OkHttp Server-Sent Events atau WebSockets, yang arsitektur kodenya jauh lebih kompleks daripada REST API biasa.
4. **Keandalan CI/CD & Testing:** Menyiapkan *pipeline* pengujian otomatis untuk menguji respons AI yang bersifat non-deterministik memerlukan penataan arsitektur *mocking* jaringan yang matang pada sistem DevOps Anda.

Mengabaikan aspek-aspek DevOps dan keamanan ini saat merilis aplikasi berisiko menyebabkan kebocoran kredensial, tagihan cloud yang membengkak, hingga pengalaman pengguna yang buruk akibat *crash* yang tidak terprediksi.

---

## Kesimpulan

Mengatur `readTimeout`, `writeTimeout`, dan `callTimeout` pada **OkHttpClient** hingga 60-120 detik adalah solusi paling efektif untuk mengatasi kendala `SocketTimeoutException` saat mengintegrasikan API Gemini Pro di Android.

Pastikan Anda selalu membungkus panggilan jaringan dalam blok *try-catch* yang spesifik menangani `SocketTimeoutException`, serta mempertimbangkan arsitektur backend perantara saat membawa aplikasi Anda dari fase *prototyping* di Google AI Studio menuju fase rilis produksi secara aman.