---
title: "Cara Handle Error Connection Timeout dan Internet Terputus saat Aplikasi Memanggil Google AI Studio"
date: "2026-09-06"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Integrasi Large Language Model (LLM) seperti Gemini API melalui Google AI Studio ke dalam aplikasi Android telah membuka lembaran baru dalam inovasi fitur pintar. Namun, aplikasi berbasis AI sangat bergantung pada stabilitas koneksi internet. Respons dari LLM sering kali membutuhkan waktu (latency) yang lebih lama dibanding API REST biasa, terutama untuk tugas-tugas kompleks seperti pembuatan konten panjang atau pemrosesan gambar.

Masalah utama yang sering dihadapi oleh developer adalah **Connection Timeout** (`SocketTimeoutException`) dan **Internet Terputus** (`UnknownHostException`). Jika tidak ditangani dengan baik, aplikasi Anda akan mengalami *crash*, *freeze*, atau memberikan *User Experience* (UX) yang buruk.

Artikel ini akan membahas secara mendalam dan praktis cara mengantisipasi serta menangani *error* koneksi saat aplikasi Android Anda memanggil Google AI Studio.

---

## 1. Mengonfigurasi Custom Timeout pada HTTP Client

Secara default, SDK Google AI Client memiliki batas waktu (timeout) bawaan. Namun, untuk koneksi internet seluler yang tidak stabil (seperti jaringan 3G/4G di daerah pelosok), Anda perlu memperpanjang atau menyesuaikan konfigurasi timeout ini menggunakan `OkHttpClient` sebagai engine di balik layar.

Berikut adalah cara mengonfigurasi `OkHttpClient` dengan timeout kustom pada proyek Android Anda:

```kotlin
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

fun provideOkHttpClient(): OkHttpClient {
    return OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS) // Waktu maksimal untuk terhubung ke server
        .writeTimeout(30, TimeUnit.SECONDS)   // Waktu maksimal untuk mengirim data
        .readTimeout(60, TimeUnit.SECONDS)    // Waktu maksimal untuk menerima respons dari Gemini
        .retryOnConnectionFailure(true)       // Mencoba kembali jika koneksi gagal di awal
        .build()
}
```

*Catatan: Pastikan Anda meneruskan konfigurasi HTTP client ini ke dalam inisialisasi SDK Gemini atau library dependency injection (seperti Hilt/Koin) yang Anda gunakan.*

---

## 2. Mendeteksi Status Internet Secara Real-Time

Sebelum melakukan *request* ke Google AI Studio, langkah terbaik adalah memeriksa apakah perangkat pengguna benar-benar terhubung ke internet. Memanggil API saat perangkat offline hanya akan membuang daya baterai dan memicu *error* yang tidak perlu.

Kita bisa menggunakan `ConnectivityManager` dengan `NetworkCallback` untuk memantau status jaringan secara *real-time*:

```kotlin
import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class NetworkMonitor(context: Context) {
    private val connectivityManager = 
        context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        
    private val _isOnline = MutableStateFlow(false)
    val isOnline: StateFlow<Boolean> = _isOnline

    init {
        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        connectivityManager.registerNetworkCallback(request, object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                _isOnline.value = true
            }

            override fun onLost(network: Network) {
                _isOnline.value = false
            }
        })
    }
}
```

Dengan *class* di atas, ViewModel Anda dapat mengamati (`collect`) status `isOnline` sebelum mengeksekusi fungsi pemanggilan API Google AI Studio.

---

## 3. Implementasi Mekanisme Retry dengan Exponential Backoff

Jika koneksi terputus sesaat (misalnya saat pengguna melewati terowongan atau berganti BTS), langsung menampilkan pesan *error* bukanlah solusi cerdas. Pendekatan terbaik adalah melakukan **Exponential Backoff Retry**—mencoba kembali panggilan API dengan jeda waktu yang semakin meningkat.

Berikut implementasi fungsi utilitas berbasis Kotlin Coroutines:

```kotlin
import kotlinx.coroutines.delay
import java.io.IOException

suspend fun <T> retryWithBackoff(
    times: Int = 3,
    initialDelay: Long = 1000, // 1 detik
    maxDelay: Long = 6000,     // 6 detik
    factor: Double = 2.0,
    block: suspend () -> T
): T {
    var currentDelay = initialDelay
    repeat(times - 1) { attempt ->
        try {
            return block()
        } catch (e: IOException) {
            // Log error atau kirim ke crash reporting tool seperti Firebase Crashlytics
            println("Attempt ${attempt + 1} failed: ${e.message}. Retrying in $currentDelay ms...")
        }
        delay(currentDelay)
        currentDelay = (currentDelay * factor).toLong().coerceAtMost(maxDelay)
    }
    return block() // Percobaan terakhir, jika gagal akan melempar exception ke luar
}
```

---

## 4. Error Handling yang Kokoh pada Google AI Studio SDK

Sekarang, mari kita satukan semua komponen di atas saat memanggil `GenerativeModel` dari SDK Google AI Client. Kita akan menangkap berbagai jenis *exception* secara spesifik untuk memberikan pesan yang relevan kepada pengguna.

```kotlin
import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.GenerateContentResponse
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

class GeminiRepository(
    private val generativeModel: GenerativeModel,
    private val networkMonitor: NetworkMonitor
) {

    suspend fun generateAiContent(prompt: String): Result<GenerateContentResponse> {
        // 1. Cek koneksi lokal terlebih dahulu
        if (!networkMonitor.isOnline.value) {
            return Result.failure(Exception("Tidak ada koneksi internet. Silakan periksa jaringan Anda."))
        }

        return try {
            // 2. Eksekusi panggilan dengan mekanisme retry
            val response = retryWithBackoff(times = 3) {
                generativeModel.generateContent(prompt)
            }
            Result.success(response)
        } catch (e: SocketTimeoutException) {
            Result.failure(Exception("Koneksi ke Google AI Studio lambat (Timeout). Silakan coba lagi."))
        } catch (e: UnknownHostException) {
            Result.failure(Exception("Gagal menghubungi server. Pastikan paket data atau Wi-Fi Anda aktif."))
        } catch (e: IOException) {
            Result.failure(Exception("Terjadi masalah jaringan yang tidak terduga: ${e.localizedMessage}"))
        } catch (e: Exception) {
            Result.failure(Exception("Terjadi kesalahan sistem: ${e.localizedMessage}"))
        }
    }
}
```

---

## Tantangan Nyata: Dari Prototype hingga Siap Rilis (Production-Ready)

Mengimplementasikan kode *error handling* di atas pada dasarnya menyelesaikan masalah teknis dasar di sisi klien (*client-side*). Namun, jika Anda berniat merilis aplikasi ini ke Google Play Store untuk ribuan pengguna aktif, tantangan sesungguhnya baru saja dimulai.

Bagi pemula maupun developer menengah, mengonfigurasi proyek dari Google AI Studio hingga menjadi versi produksi sangatlah rumit. Beberapa kendala yang sering memicu frustrasi meliputi:

1. **Keamanan API Key:** Menyimpan API Key Google AI Studio langsung di dalam kode Android sangat rawan didekompilasi (di-reverse engineer) oleh pihak tidak bertanggung jawab. Anda harus membangun *proxy server* atau menggunakan Firebase Vertex AI untuk mengamankannya.
2. **Arsitektur Pipeline DevOps:** Mengintegrasikan pengujian otomatis (CI/CD) agar API Key tidak bocor ke repositori publik (seperti GitHub/GitLab).
3. **Manajemen Rate Limit:** Google AI Studio versi gratis memiliki limit kuota yang ketat. Anda harus mampu merancang sistem *caching* lokal (Room Database) untuk menghemat panggilan API yang berulang.
4. **Sinkronisasi State UI yang Kompleks:** Menghandle transisi UI dari *loading*, *success*, hingga *retry state* secara mulus tanpa membuat aplikasi terasa patah-patah (*janky*).

Memaksakan diri mempelajari dan mengonfigurasi seluruh infrastruktur keamanan, backend proxy, dan DevOps Android ini sendirian sering kali memakan waktu berminggu-minggu, bahkan berbulan-bulan—waktu yang seharusnya bisa Anda gunakan untuk fokus mematangkan fitur utama aplikasi Anda.