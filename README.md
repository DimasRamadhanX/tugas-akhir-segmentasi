# 👶 Segmentasi Pelanggan Baby Spa

Repositori ini berisi proyek analisis data dan sistem segmentasi pelanggan Baby Spa menggunakan Django (Backend), Pandas, SQLite, serta Jupyter Notebook untuk analisis clustering (DBSCAN vs K-Means).

---

## ⚠️ CATATAN PENTING: Pengambilan Data Raw (Mentah)

Data mentah (**raw data**) berupa file CSV tidak disimpan di dalam repositori Git ini karena ukurannya yang besar dan kebijakan keamanan (diabaikan menggunakan `.gitignore` di bawah folder `data/raw/`).

Untuk menjalankan proyek ini, **Anda harus meminta data mentah secara manual**:
*   **Kontak:** Dimas Ramadhan
*   **Email:** [dimasramadhankerja@gmail.com](mailto:dimasramadhankerja@gmail.com)

Setelah mendapatkan file data mentah, buat folder bernama `data/raw/` di direktori utama proyek (jika belum ada), lalu letakkan file-file berikut di dalamnya:
*   `AHP.csv`
*   `AHP_2.csv`
*   `master_customers.csv`
*   `master_items.csv`
*   `master_transaction_headers.csv`
*   `master_transaction_items.csv`
*   `master_transactions.csv`

---

## 🛠️ Langkah-langkah Setup Proyek

Ikuti petunjuk di bawah ini untuk menyiapkan lingkungan pengembangan lokal Anda:

### 1. Buat dan Aktifkan Virtual Environment
Sangat disarankan menggunakan virtual environment agar dependensi proyek tidak mengganggu lingkungan Python global Anda.

*   **Membuat virtual environment:**
    ```bash
    python -m venv sunny_env
    ```
*   **Mengaktifkan virtual environment:**
    *   **Windows (PowerShell):**
        ```powershell
        .\sunny_env\Scripts\Activate.ps1
        ```
    *   **Windows (CMD):**
        ```cmd
        .\sunny_env\Scripts\activate.bat
        ```
    *   **macOS / Linux:**
        ```bash
        source sunny_env/bin/activate
        ```

### 2. Install Dependensi Proyek
Pastikan virtual environment telah aktif, kemudian jalankan perintah berikut untuk menginstal semua dependensi yang tertera di `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variable
Buat berkas `.env` di direktori utama proyek (sejajar dengan `manage.py`) dan isi dengan konfigurasi berikut:
```env
SECRET_KEY='django-insecure-rr_a8yg&!5ps9g*752j93r!lia_nw7ow^n*8-22l$@^--xk*f^'
DEBUG=True
```
*(Catatan: Sesuaikan `SECRET_KEY` bila diperlukan untuk deployment).*

### 4. Jalankan Migrasi Database
Siapkan skema tabel awal pada SQLite (`babybspa_db.sqlite3`) dengan menjalankan perintah migrasi bawaan Django:
```bash
python manage.py migrate
```

### 5. Impor & Normalisasi Data Raw ke SQLite
Setelah memindahkan file data mentah (CSV) ke `data/raw/`, jalankan perintah khusus Django berikut untuk membersihkan, menormalisasi, dan memasukkannya ke database SQLite secara massal (Bulk Insert):
```bash
python manage.py normalize_to_db
```
> **Catatan:** Perintah ini akan menghapus (truncate) data lama di database lokal terlebih dahulu sebelum mengimpor data yang baru.

### 6. Jalankan Pipeline Update & Normalisasi Lanjutan
Jalankan pipeline Django untuk memperbarui data tambahan (seperti durasi transaksi, kategori produk, jenis kelamin, varian normalisasi, dsb.) secara otomatis:
```bash
python manage.py run_pipeline
```

### 7. Jalankan Server Django
Untuk menguji backend Django lokal, jalankan server pengembangan:
```bash
python manage.py runserver
```
Akses admin Django di: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 📊 Analisis Data (Jupyter Notebook)

Jika Anda ingin melakukan eksperimen clustering, evaluasi elbow/silhouette, visualisasi PCA, atau analisis LRFM (Length, Recency, Frequency, Monetary):
1. Pastikan Jupyter Kernel terdeteksi menggunakan environment `sunny_env`.
2. Jalankan/Buka file notebook utama:
   *   `new_main.ipynb` (Analisis & visualisasi terbaru)
   *   `main.ipynb` (Analisis & visualisasi awal)
