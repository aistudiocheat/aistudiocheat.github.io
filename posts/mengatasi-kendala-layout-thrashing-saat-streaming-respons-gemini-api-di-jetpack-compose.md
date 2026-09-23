---
title: "Mengatasi Kendala Layout Thrashing saat Streaming Respons Gemini API di Jetpack Compose"
date: "2026-09-23"
excerpt: "Pelajari panduan praktis mengatasi kendala teknis saat mengembangkan, mengamankan, atau merilis aplikasi Android berbasis Google AI Studio."
tags: ["Android", "Google AI Studio", "Gemini API", "DevOps"]
---

Mengintegrasikan Large Language Model (LLM) seperti Gemini API ke dalam aplikasi Android memberikan dimensi interaktivitas baru yang luar biasa. Salah satu fitur terbaiknya adalah *streaming response* (menggunakan `generateContentStream`), di mana pengguna dapat melihat teks dihasilkan secara *real-time*, kata demi kata, mirip seperti ChatGPT.

Namun, di balik keindahan UX ini, terdapat tantangan performa yang serius di sisi frontend, khususnya jika Anda menggunakan **Jetpack Compose**. Fenomena ini disebut **Layout Thrashing** (atau dalam konteks Compose: *excessive recomposition* dan *repeated measurement passes*). 

Artikel ini akan mengupas tuntas mengapa hal ini terjadi dan bagaimana cara mengatasinya agar aplikasi Android Anda tetap berjalan mulus di 60fps (atau 120fps) bahkan saat menerima ribuan karakter per detik dari Gemini API.

---

## Memahami Masalah: Mengapa Streaming Gemini Menyebabkan Layout Thrashing?

Dalam Jetpack Compose, UI bersifat deklaratif. Ketika state berubah, Compose akan melakukan **Recomposition** (rekomposisi) untuk memperbarui tampilan.

Saat Anda melakukan streaming dari Gemini API, Anda menerima potongan teks (*chunks*) dalam interval milidetik yang sangat cepat. Jika Anda memperbarui state String secara langsung setiap kali *chunk* baru tiba, hal berikut akan terjadi:

1. **Rekomposisi Berantai:** Composable `Text` yang menampilkan jawaban akan merekomposisi dirinya sendiri secara konstan.
2. **Layout Phase Overload:** Setiap kali teks bertambah, Compose harus mengukur ulang (*measure*) lebar dan tinggi teks baru, serta memposisikan ulang (*layout*) elemen-elemen di sekitarnya (seperti bubble chat, tombol, atau scroll position).
3. **CPU Spike:** Proses kalkulasi layout teks (terutama dengan *auto-wrapping* dan *dynamic height*) adalah operasi berat. Jika terjadi puluhan kali dalam satu detik, CPU akan mengalami *spike*, menyebabkan *dropped frames* (aplikasi terlihat patah-patah/laggy).

---

## Langkah 1: Gunakan State Buffering (Throttling) pada Coroutine Flow

Solusi pertama adalah membatasi seberapa sering UI diperbarui. Pengguna tidak akan menyadari jika teks diperbarui setiap 50–100 milidetik sekali, alih-alih setiap 2 milidetik. Kita bisa menggunakan operator flow untuk melakukan *buffer* atau *throttle*.

Berikut adalah implementasi `ViewModel` menggunakan Kotlin Coroutines untuk mengelompokkan emisi data dari Gemini API:

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.ai.client.generativeai.GenerativeModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.buffer
import kotlinx.coroutines.flow.collectIndexed
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

class ChatViewModel(private val generativeModel: GenerativeModel) : ViewModel() {

    private val _uiState = MutableStateFlow("")
    val uiState = _uiState.asStateFlow()

    fun startStreamingResponse(prompt: String) {
        viewModelScope.launch {
            _uiState.value = ""
            var accumulatedText = ""
            
            try {
                generativeModel.generateContentStream(prompt)
                    .collect { response ->
                        accumulatedText += response.text ?: ""
                        
                        // Buffer taktik: Update UI hanya jika ada teks baru,
                        // berikan delay mikro untuk mencegah overload main thread
                        _uiState.value = accumulatedText
                        delay(30) // Throttle aman untuk mata manusia & CPU
                    }
            } catch (e: Exception) {
                _uiState.value = "Error: ${e.localizedMessage}"
            }
        }
    }
}
```

*Catatan: Penggunaan `delay(30)` memberikan waktu bernapas bagi UI Thread untuk menyelesaikan fase layout sebelum menerima update teks berikutnya.*

---

## Langkah 2: Isolasi Rekomposisi dengan Composable Terpisah

Jangan biarkan seluruh layar merekomposisi dirinya hanya karena satu komponen teks sedang melakukan streaming. Isolasi komponen teks tersebut ke dalam Composable-nya sendiri dan gunakan parameter bertipe `State<T>` atau fungsi lambda untuk membaca state secara *deferred* (ditunda).

Mari buat Composable `StreamingTextBubble` yang efisien:

```kotlin
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun StreamingTextBubble(
    textProvider: () -> String, // Menggunakan lambda untuk mencegah recomposition pada parent
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .background(Color(0xFFF1F1F1), shape = RoundedCornerShape(12.dp))
            .padding(16.dp)
    ) {
        Text(
            text = textProvider(), // State dibaca langsung di dalam Text composable target
            fontSize = 16.sp,
            color = Color.Black
        )
    }
}
```

Dengan meneruskan `textProvider: () -> String` (bukan langsung `String`), Composable induk yang memanggil `StreamingTextBubble` tidak akan ikut merekomposisi ulang setiap kali teks berubah. Hanya Composable `Text` internal yang akan diperbarui.

---

## Langkah 3: Gunakan LazyListState dengan Efisien

Jika Anda menampilkan teks streaming ini di dalam sebuah daftar chat (`LazyColumn`), autoscroll ke bawah saat teks bertambah dapat memperparah Layout Thrashing. Pastikan Anda hanya melakukan scroll ketika memang ada penambahan baris yang signifikan, dan bungkus dengan `derivedStateOf`.

Berikut contoh implementasi chat screen:

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier

@Composable
fun ChatScreen(viewModel: ChatViewModel) {
    val streamText by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()

    // Optimasi scroll: Hanya scroll ke bawah jika item terakhir terlihat
    val isAtBottom by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val visibleItemsInfo = layoutInfo.visibleItemsInfo
            if (layoutInfo.totalItemsCount == 0) {
                true
            } else {
                val lastVisibleItem = visibleItemsInfo.lastOrNull()
                lastVisibleItem != null && lastVisibleItem.index == layoutInfo.totalItemsCount - 1
            }
        }
    }

    LaunchedEffect(streamText) {
        if (isAtBottom && streamText.isNotEmpty()) {
            listState.animateScrollToItem(listState.layoutInfo.totalItemsCount - 1)
        }
    }

    LazyColumn(
        state = listState,
        modifier = Modifier.fillMaxSize()
    ) {
        // Item chat lainnya...
        
        item {
            StreamingTextBubble(
                textProvider = { streamText }
            )
        }
    }
}
```

---

## Langkah 4: Terapkan Penjadwalan Profiling dengan Baseline Profiles

Untuk memastikan runtime Android (ART) mengompilasi kode kritis Anda sebelum aplikasi dijalankan (AOT - *Ahead of Time*), buat **Baseline Profile** khusus untuk skenario *chat streaming* Anda. Ini mengurangi waktu kompilasi JIT (*Just-In-Time*) saat teks Gemini dirender secara intensif.

Tambahkan dependensi Baseline Profile Generator di modul Gradle Anda dan rekam interaksi saat teks sedang di-stream. Hal ini akan mengurangi *jank* secara drastis pada perangkat kelas menengah ke bawah.

---

## Menghadapi Realitas Pengembangan Aplikasi AI saat ini

Menerapkan trik performa Jetpack Compose seperti di atas memang sangat memuaskan ketika Anda melihat UI berjalan mulus tanpa lag. Namun, mengoptimalkan rendering hanyalah satu dari sekian banyak tantangan nyata dalam siklus hidup pengembangan aplikasi Android bertenaga AI.

Bagi banyak developer dan tim produk, melangkah keluar dari kenyamanan Google AI Studio (tempat Anda bermain-main dengan prompt) untuk masuk ke fase produksi nyata adalah proses yang sangat rumit dan melelahkan. 

Anda harus memikirkan aspek DevOps dan arsitektur yang kompleks, seperti:
*   **Keamanan API Key:** Bagaimana mengamankan API key Gemini agar tidak didekompilasi dari file APK (menggunakan App Check atau Proxy Backend).
*   **Arsitektur Multi-Platform/Multi-Device:** Memastikan aplikasi berjalan stabil di berbagai versi SDK Android dan ukuran layar yang berbeda.
*   **Manajemen Rate Limiting:** Menangani kendala kuota API dari Google AI Studio dan menyiapkan sistem fallback.
*   **CI/CD Pipeline:** Mengotomatiskan pengujian fungsionalitas AI agar tidak merusak fitur lama setiap kali model diperbarui.

Mengonfigurasi semua infrastruktur ini dari nol sering kali menyita waktu berharga yang seharusnya bisa Anda gunakan untuk mematangkan fitur unik dan *user experience* aplikasi Anda.