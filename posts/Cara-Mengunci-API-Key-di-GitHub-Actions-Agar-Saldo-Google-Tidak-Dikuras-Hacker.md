# Cara Mengunci API Key di GitHub Actions Agar Saldo Google Tidak Dikuras Hacker

Membuat aplikasi berbasis kecerdasan buatan (AI) lewat **Google AI Studio** memang sangat menyenangkan. Hanya dengan mengekspor kode Kotlin bawaannya, aplikasi Anda sudah bisa langsung menggunakan kecerdasan model Gemini. 

Namun, ada satu kecerobohan fatal yang sering dilakukan oleh developer pemula maupun agensi: **Menuliskan `GEMINI_API_KEY` secara terang-terangan (hardcoded) di dalam file kode, lalu mengunggahnya ke repositori GitHub.**

Jika Anda melakukan hal ini, Anda sedang membuka pintu selebar-lebarnya bagi robot pemindai (*crawler*) milik hacker. Dalam hitungan menit, kunci API Anda akan dicuri, kuota server dikuras untuk kepentingan mereka, dan Anda akan terbangun keesokan harinya dengan tagihan Google Cloud yang membengkak hingga puluhan juta rupiah.

Bagaimana cara menguncinya dengan standar keamanan industri menggunakan **GitHub Secrets**? Simak panduan DevOps praktisnya berikut ini.

## 🔒 1. Berhenti Menulis API Key di File `Strings.xml` atau Kotlin!

Langkah pertama untuk selamat adalah menghapus semua teks API Key fisik dari dalam proyek Anda. Jangan pernah menaruh token rahasia di dalam file `AndroidManifest.xml`, `strings.xml`, atau langsung di dalam variabel *class* Kotlin Anda. 

Sebagai gantinya, gunakan file konfigurasi lokal bernama `.env` atau `local.properties` saat melakukan pengujian di komputer sendiri, dan pastikan file tersebut sudah dimasukkan ke dalam daftar `.gitignore` agar tidak ikut terunggah ke internet.

## 🔐 2. Memanfaatkan Fitur Enkripsi GitHub Secrets

Ketika proyek Anda dipindahkan ke dalam *pipeline* otomatisasi *cloud* **GitHub Actions**, server memerlukan akses ke API Key Anda untuk melakukan proses *compile*. Cara paling aman untuk menyediakannya adalah dengan menyembunyikannya di dalam brankas digital bawaan GitHub bernama **GitHub Secrets**.

### Cara Memasang Secrets di Repositori Anda:
1. Masuk ke halaman repositori proyek Anda di GitHub.
2. Klik tab **Settings** ➡️ **Secrets and variables** ➡️ **Actions**.
3. Klik tombol **New repository secret**.
4. Pada kolom *Name*, ketik: `GEMINI_API_KEY`
5. Pada kolom *Value*, masukkan token kunci API asli Anda dari Google AI Studio.
6. Klik **Add secret**.

Dengan cara ini, token Anda akan dienkripsi secara total oleh sistem keamanan tingkat tinggi milik GitHub. Kunci tersebut tidak akan pernah terlihat oleh siapa pun, bahkan oleh anggota tim Anda sendiri di dalam kode.

## 🤖 3. Cara Menyuntikkan Secrets ke Dalam Script Workflow

Setelah kunci rahasia disimpan di dalam brankas GitHub, tugas berikutnya adalah menyuruh script otomatisasi `.github/workflows/android.yml` untuk mengambil kunci tersebut dan menyuntikkannya secara dinamis ke dalam aplikasi saat proses *build* berjalan di memori server.

Berikut adalah potongan skrip cerdas DevOps untuk mengotomatiskan injeksi tersebut tanpa meninggalkan jejak file fisik:

```bash
# Mengunci dan menyuntikkan GEMINI_API_KEY langsung saat kompilasi Gradle
./gradlew assembleRelease \
  --no-configuration-cache \
  -PGEMINI_API_KEY="\${{ secrets.GEMINI_API_KEY }}"
```
Di dalam kode Kotlin aplikasi Anda (terutama menggunakan *Build Konfigurasi*), sistem akan otomatis membaca variabel rahasia tersebut dengan aman saat aplikasi dijalankan oleh pengguna, tanpa ada risiko kodenya bisa dibongkar (*reverse engineering*) oleh hacker.

## 🚀 Solusi Terima Beres Standar Korporat

Menyusun sistem enkripsi berlapis, mengamankan file *Keystore* digital Base64, hingga memastikan file `.env` tidak terhapus saat pembersihan Gradle adalah pekerjaan DevOps yang membutuhkan ketelitian tinggi. Salah satu baris kode saja bisa menyebabkan alur kerja otomatisasi Anda macet dan memunculkan eror warna merah yang membingungkan.

Jika Anda ingin mengamankan dapur finansial aplikasi AI Anda sekarang juga tanpa perlu pusing melewati ratusan kali kegagalan ujicoba sistem, kami di **Studio Cheat** siap memasangkan infrastruktur keamanannya untuk Anda.

Kami menyusun sistem *Ultimate CloudBuilder Pro* yang mengunci seluruh kredensial berharga Anda di dalam GitHub Secrets, memastikan aplikasi Anda 100% aman, ringan, anti-hacker, dan siap menghasilkan keuntungan AdMob secara mandiri selamanya cukup dengan sekali klik!
