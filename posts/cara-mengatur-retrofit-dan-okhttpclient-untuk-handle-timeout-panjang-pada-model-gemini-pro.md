---
title: "Cara Mengatur Retrofit dan OkHttpClient untuk Handle Timeout Panjang pada Model Gemini Pro"
date: "2026-11-28"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan *Large Language Models* (LLM) seperti **Gemini Pro** dari Google AI Studio ke dalam aplikasi Android menghadirkan tantangan teknis tersendiri. Berbeda dengan API RESTful konvensional yang biasanya memberikan respon dalam hitungan milidetik, Gemini Pro membutuhkan waktu lebih lama untuk melakukan *inference*, memproses prompt kompleks, dan menggenerasi teks atau kode berukuran besar.

Secara *default*, HTTP client di Android seperti **OkHttpClient** memiliki durasi *timeout* sebesar **10 detik**. Jika model Gemini Pro membutuhkan waktu 15 hingga 30 detik untuk menghasilkan jawaban lengkap, aplikasi Android Anda akan secara otomatis melempar pengecualian `java.net.SocketTimeoutException`.

Artikel ini akan membahas secara mendalam cara mengkonfigurasi **Retrofit** dan **OkHttpClient** di Android (Kotlin) untuk menangani *timeout* panjang saat berkomunikasi dengan API Gemini Pro secara stabil.

---

## Memahami Jenis Timeout pada OkHttpClient

Sebelum masuk ke implementasi kode, sangat penting untuk memahami 4 jenis durasi *timeout* yang disediakan oleh OkHttpClient:

1. **`connectTimeout`**: Waktu maksimum untuk membangun koneksi awal TCP/TLS dengan server (Google AI Studio Gateway).
2. **`readTimeout`**: Waktu maksimum jeda antar paket data yang diterima dari server setelah koneksi berhasil. Ini adalah titik paling krusial untuk LLM.
3. **`writeTimeout`**: Waktu maksimum untuk mengirim data *request* (payload prompt) ke server.
4. **`callTimeout`**: Waktu batas total untuk seluruh eksekusi HTTP request (mulai dari DNS lookup hingga respon selesai dibaca).

Untuk model Gemini Pro, peningkatan durasi pada **`readTimeout`** dan **`callTimeout`** adalah kunci utama.

---

## Langkah 1: Menambahkan Dependensi

Pastikan file `build.gradle.kts` (Module :app) Anda telah memuat dependensi Retrofit dan OkHttp versi terbaru:

```kotlin
dependencies {
    // OkHttp & Logging Interceptor
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Retrofit & Converter
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // Kotlin Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
```

---

## Langkah 2: Mengonfigurasi OkHttpClient dengan Timeout Panjang

Buatlah instance `OkHttpClient` khusus yang menaikkan batasan waktu secara signifikan. Untuk permintaan standar Gemini Pro, mengatur *timeout* hingga **60-120 detik** sangat direkomendasikan.

```kotlin
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

object NetworkClient {

    private fun createOkHttpClient(): OkHttpClient {
        // Logging interceptor untuk mendebug request/response
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        return OkHttpClient.Builder()
            // Mengatur timeout lebih panjang khusus untuk Gemini API
            .connectTimeout(30, TimeUnit.SECONDS) // Batas waktu koneksi ke server
            .readTimeout(90, TimeUnit.SECONDS)    // Batas waktu menunggu pemrosesan LLM
            .writeTimeout(30, TimeUnit.SECONDS)   // Batas waktu mengirim data prompt
            .callTimeout(120, TimeUnit.SECONDS)   // Batas waktu total satu HTTP call
            .addInterceptor(loggingInterceptor)
            .retryOnConnectionFailure(true)       // Otomatis mencoba ulang jika koneksi terputus
            .build()
    }

    val okHttpClient: OkHttpClient by lazy {
        createOkHttpClient()
    }
}
```

---

## Langkah 3: Menghubungkan OkHttpClient ke Instance Retrofit

Setelah `OkHttpClient` dikonfigurasi, suntikkan instance tersebut ke dalam builder Retrofit.

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object GeminiApiClient {

    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(NetworkClient.okHttpClient) // Memasukkan OkHttpClient dengan timeout panjang
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    fun <T> createService(serviceClass: Class<T>): T {
        return retrofit.create(serviceClass)
    }
}
```

---

## Langkah 4: Membuat Service Interface dan Model Data

Definisikan *endpoint* API Gemini Pro sesuai dengan dokumentasi resmi Google AI Studio.

```kotlin
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

// Model Request sederhanan
data class GeminiRequest(
    val contents: List<Content>
)

data class Content(
    val parts: List<Part>
)

data class Part(
    val text: String
)

// Model Response
data class GeminiResponse(
    val candidates: List<Candidate>?
)

data class Candidate(
    val content: Content?
)

// Retrofit Interface
interface GeminiApiService {
    @POST("v1beta/models/gemini-pro:generateContent")
    suspend fun generateContent(
        @Query("key") apiKey: String,
        @Body request: GeminiRequest
    ): Response<GeminiResponse>
}
```

---

## Langkah 5: Mengatasi Error Timeout dengan Safe API Call

Saat memanggil API ini dari ViewModel, pastikan Anda menangkap `SocketTimeoutException` dan memberikan umpan balik (feedback) yang baik kepada pengguna agar aplikasi tidak *crash*.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.net.SocketTimeoutException
import java.io.IOException

sealed class UiState {
    object Idle : UiState()
    object Loading : UiState()
    data class Success(val result: String) : UiState()
    data class Error(val message: String) : UiState()
}

class GeminiViewModel : ViewModel() {

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState

    private val apiService = GeminiApiClient.createService(GeminiApiService::class.java)

    fun askGemini(promptText: String, apiKey: String) {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                val request = GeminiRequest(
                    contents = listOf(Content(parts = listOf(Part(text = promptText))))
                )
                
                val response = apiService.generateContent(apiKey = apiKey, request = request)

                if (response.isSuccessful) {
                    val textResult = response.body()?.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
                    _uiState.value = UiState.Success(textResult ?: "Tidak ada respon.")
                } else {
                    _uiState.value = UiState.Error("HTTP Error: ${response.code()} ${response.message()}")
                }

            } catch (e: SocketTimeoutException) {
                // Menangani error jika proses AI memakan waktu melebih readTimeout
                _uiState.value = UiState.Error("Koneksi timeout. Pemrosesan model Gemini memerlukan waktu lebih lama. Silakan coba lagi.")
            } catch (e: IOException) {
                _uiState.value = UiState.Error("Terjadi kesalahan jaringan: ${e.localizedMessage}")
            } catch (e: Exception) {
                _uiState.value = UiState.Error("Terjadi kesalahan sistem: ${e.localizedMessage}")
            }
        }
    }
}
```

---

## Realita Mengembangkan Aplikasi Berbasis AI Studio untuk Produksi

Mengatur nilai *timeout* pada OkHttpClient memang dapat menyelesaikan masalah `SocketTimeoutException` secara teknis pada tahap awal. Namun, saat Anda berencana merilis aplikasi berbasis Google AI Studio ke tingkat produksi (*production-ready*), tantangan yang sebenarnya baru saja dimulai.

Bagi pengembang pemula maupun tim kecil, menjembatani *prototype* sederhana dari Google AI Studio menjadi aplikasi Android profesional memiliki arsitektur yang sangat kompleks, seperti:

1. **Keamanan API Key**: Menyimpan API Key Google AI Studio langsung di dalam kode Kotlin (meskipun menggunakan `BuildConfig`) sangat rentan terhadap teknik *reverse-engineering*. Penerapan *Secrets Gradle Plugin*, NDK (C++ native layer), atau pembuatan *Backend-For-Frontend* (BFF) proxy mutlak diperlukan.
2. **Penanganan Server-Sent Events (SSE) / Streaming Response**: Mengubah arsitektur Retrofit dari request-response standar menjadi *streaming* data (*Server-Sent Events*) agar teks dari Gemini muncul secara *real-time* per kata (mirip ChatGPT) membutuhkan penanganan *Flow* dan OkHttp *EventSource* yang lebih rumit.
3. **Arsitektur DevOps & Network Resiliency**: Implementasi *exponential backoff retry strategy*, *circuit breaker pattern*, serta manajemen kuota *rate-limit* API agar aplikasi tidak mendadak berhenti saat lonjakan pengguna (*peak load*).
4. **Optimasi Build dan ProGuard/R8 Rules**: Memastikan aturan obfuscation tidak merusak serialisasi JSON pada model data Gemini saat APK dirilis dalam mode release.

Mencoba mengonfigurasi semua lapisan keamanan, manajemen state coroutine yang lancar, dan arsitektur *DevOps pipeline* ini sendirian dari nol sering kali memakan waktu berminggu-minggu dan rentan terhadap *bug* fatal yang memengaruhi pengalaman pengguna.

---

## Kesimpulan

Menangani pemrosesan AI berdurasi panjang pada Android memerlukan penyesuaian konfigurasi *network layer*. Dengan menaikkan `readTimeout` dan `callTimeout` pada **OkHttpClient** hingga 90–120 detik, serta memadukannya bersama **Retrofit** dan **Kotlin Coroutines**, aplikasi Android Anda dapat mengeksekusi *prompt* kompleks pada Gemini Pro tanpa kendala *timeout*.

Pastikan Anda selalu menangani `SocketTimeoutException` secara elegan di layar UI agar pengguna tetap mendapatkan kejelasan informasi saat model AI sedang bekerja keras memproses data.