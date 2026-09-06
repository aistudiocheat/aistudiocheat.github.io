---
title: "Cara Handle Error Connection Timeout dan Internet Terputus saat Aplikasi Memanggil Google AI Studio"
date: "2026-09-06"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan Large Language Model (LLM) seperti Gemini melalui SDK Google AI Studio ke dalam aplikasi Android adalah langkah besar untuk menghadirkan fitur pintar. Namun, aplikasi yang hebat di lingkungan *local development* belum tentu siap menghadapi kerasnya dunia nyata. 

Di ranah produksi, pengguna Anda akan menghadapi jaringan 4G yang tidak stabil, transisi Wi-Fi ke seluler yang terputus, hingga *dead zone* (blank spot signal). Jika aplikasi Anda tidak siap menangani `SocketTimeoutException` atau hilangnya koneksi internet secara mendadak saat memanggil API Google AI Studio, aplikasi Anda akan mengalami *freeze*, memicu ANR (Application Not Responding), atau bahkan *crash*.

Artikel ini akan membahas secara mendalam cara membangun arsitektur jaringan yang tangguh (*resilient*) pada Android untuk menangani *connection timeout* dan internet terputus saat memanggil Google AI Studio.

---

## 1. Deteksi Dini Koneksi Jaringan (Pre-flight Check)

Sebelum membuang-buang kuota API dan daya baterai perangkat untuk melakukan pemanggilan ke Google AI Studio, lakukan pengecekan apakah perangkat benar-benar terhubung ke internet.

Buat sebuah utility class menggunakan `ConnectivityManager` yang modern dengan memanfaatkan `NetworkCapabilities`:

```kotlin
import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

class NetworkMonitor(private val context: Context) {

    fun isInternetAvailable(): Boolean {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val activeNetwork = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(activeNetwork) ?: return false
        
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
}
```

*Catatan: `NET_CAPABILITY_VALIDATED` memastikan bahwa jaringan tidak hanya terhubung (seperti Wi-Fi publik yang meminta login), tetapi benar-benar memiliki akses internet aktif.*

---

## 2. Mengatur Custom Timeout pada SDK Google AI Studio

Secara default, SDK Google AI Studio (Gemini) menggunakan konfigurasi timeout bawaan. Namun, untuk menangani jaringan yang lambat, Anda perlu mengontrol batas waktu tunggu (*timeout*) secara eksplisit. 

Saat menginisialisasi `GenerativeModel`, Anda dapat menyematkan `RequestOptions` untuk mengatur nilai *read timeout* dan *connection timeout*:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.RequestOptions
import com.google.ai.client.generativeai.type.generationConfig

val requestOptions = RequestOptions(
    // Mengatur timeout maksimal 30 detik
    timeout = 30000 
)

val generativeModel = GenerativeModel(
    modelName = "gemini-1.5-flash",
    apiKey = "API_KEY_ANDA",
    generationConfig = generationConfig {
        temperature = 0.7f
    },
    requestOptions = requestOptions
)
```

---

## 3. Implementasi Mekanisme Retry dengan Exponential Backoff

Ketika terjadi gangguan jaringan sesaat (*transient error*), langsung menampilkan pesan error ke pengguna bukanlah UX yang baik. Praktik terbaik dalam DevOps mobile adalah melakukan percobaan ulang (*retry*) secara otomatis dengan jeda waktu yang meningkat secara eksponensial (*exponential backoff*).

Mari kita buat fungsi ekstensi Kotlin Coroutines untuk menangani hal ini secara elegan:

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
            // Log error untuk kebutuhan analytics/monitoring
            println("Attempt ${attempt + 1} failed: ${e.message}. Retrying in $currentDelay ms...")
        }
        delay(currentDelay)
        currentDelay = (currentDelay * factor).toLong().coerceAtMost(maxDelay)
    }
    return block() // Percobaan terakhir, biarkan melempar exception jika tetap gagal
}
```

---

## 4. Menggabungkan Semuanya dalam Layer Repository

Sekarang kita akan mengintegrasikan `NetworkMonitor`, penanganan timeout, dan mekanisme *retry* ke dalam arsitektur MVVM (Model-View-ViewModel) pada layer Repository.

Kita akan membungkus status respons menggunakan Sealed Class untuk merepresentasikan status UI secara presisi:

```kotlin
sealed class NetworkResult<out T> {
    data class Success<out T>(val data: T) : NetworkResult<T>()
    data class Error(val message: String, val isNoInternet: Boolean = false) : NetworkResult<Nothing>()
    object Loading : NetworkResult<Nothing>()
}
```

Berikut adalah implementasi class `GeminiRepository`:

```kotlin
import com.google.ai.client.generativeai.GenerativeModel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import java.io.IOException
import java.net.SocketTimeoutException

class GeminiRepository(
    private val generativeModel: GenerativeModel,
    private val networkMonitor: NetworkMonitor
) {

    fun generateContent(prompt: String): Flow<NetworkResult<String>> = flow {
        emit(NetworkResult.Loading)

        // 1. Cek Koneksi Internet sebelum memanggil API
        if (!networkMonitor.isInternetAvailable()) {
            emit(NetworkResult.Error("Tidak ada koneksi internet. Silakan periksa jaringan Anda.", isNoInternet = true))
            return@flow
        }

        try {
            // 2. Lakukan pemanggilan dengan mekanisme Retry
            val response = retryWithBackoff(times = 3) {
                generativeModel.generateContent(prompt)
            }
            
            response.text?.let {
                emit(NetworkResult.Success(it))
            } ?: emit(NetworkResult.Error("Gagal mendapatkan respons dari AI."))
            
        } catch (e: SocketTimeoutException) {
            emit(NetworkResult.Error("Koneksi terputus (Timeout). Silakan coba beberapa saat lagi."))
        } catch (e: IOException) {
            emit(NetworkResult.Error("Terjadi kesalahan jaringan: ${e.localizedMessage}"))
        } catch (e: Exception) {
            emit(NetworkResult.Error("Terjadi kesalahan sistem: ${e.localizedMessage}"))
        }
    }
}
```

---

## 5. Implementasi di Sisi UI (Jetpack Compose)

Pada komponen UI, Anda cukup mengamati (*observe*) `NetworkResult` dan menampilkan visualisasi yang relevan kepada pengguna. Jika error terjadi karena masalah internet, tampilkan tombol "Coba Lagi" (*Retry*).

```kotlin
@Composable
fun GeminiScreen(viewModel: GeminiViewModel) {
    val uiState by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.padding(16.bind())) {
        when (uiState) {
            is NetworkResult.Loading -> {
                CircularProgressIndicator()
                Text("Sedang berpikir...")
            }
            is NetworkResult.Success -> {
                Text(text = (uiState as NetworkResult.Success).data)
            }
            is NetworkResult.Error -> {
                val errorState = uiState as NetworkResult.Error
                Text(text = errorState.message, color = Color.Red)
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Button(onClick = { viewModel.retryLastPrompt() }) {
                    Text("Coba Lagi")
                }
            }
            else -> {}
        }
    }
}
```

---

## Mengapa Konfigurasi Produksi Begitu Menantang?

Menerapkan kode di atas pada proyek latihan atau *prototype* berskala kecil memang terlihat sederhana. Namun, realitasnya jauh lebih kompleks ketika Anda melangkah ke tahap produksi (*production-grade application*). 

Mengintegrasikan Google AI Studio ke dalam siklus DevOps Android yang sesungguhnya membutuhkan ketelitian ekstra. Anda harus memikirkan:

1. **Keamanan API Key:** Menyimpan API Key di dalam kode biner Android sangat rentan didekompilasi. Anda memerlukan teknik obfuscation tingkat lanjut dengan ProGuard/R8, enkripsi Native C++ (NDK), atau idealnya membangun arsitektur *Proxy Server* berbasis Cloud.
2. **Manajemen Kuota dan Cost Control:** Membatasi konsumsi token pengguna agar tagihan Google Cloud Anda tidak membengkak akibat *abuse* atau eksploitasi API.
3. **CI/CD Pipeline:** Memastikan pengujian otomatis (Unit Testing & Instrumented Testing) untuk skenario *offline mode* berjalan mulus di server integrasi seperti GitHub Actions atau GitLab CI.
4. **Monitoring & Analytics:** Memasang *crash reporting* (seperti Firebase Crashlytics) dan monitoring performa jaringan untuk mendeteksi seberapa sering pengguna Anda di wilayah tertentu mengalami kegagalan koneksi.

Bagi developer mandiri atau startup yang sedang berfokus pada validasi produk (*Product-Market Fit*), mengonfigurasi seluruh infrastruktur DevOps, keamanan, dan *error handling* yang kokoh ini dari nol bisa menyedot waktu berpekan-pekan—yang seharusnya bisa dialokasikan untuk mematangkan fitur utama aplikasi Anda.