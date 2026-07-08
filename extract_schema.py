import sqlite3
import os

# 1. Kunci jalur absolut database sesuai lokasi aslinya
database_path = r"C:\babyspa-data\babybspa_db.sqlite3"

if not os.path.exists(database_path):
    print(f"❌ Eror: Berkas tidak ditemukan di {database_path}")
    print("Silakan periksa kembali folder C:\\babyspa-data\\ via File Explorer.")
    exit()

print(f"[-] Membaca skema fisik dari: {database_path}")

# 2. Buka koneksi database
conn = sqlite3.connect(database_path)
cursor = conn.cursor()

# 3. Ambil data semua tabel dan indeks buatanmu beserta bawaan Django
query = "SELECT sql FROM sqlite_master WHERE type IN ('table', 'index') AND sql NOT NULL;"
cursor.execute(query)
rows = cursor.fetchall()

ddl_statements = []
for row in rows:
    statement = row[0].strip()
    # Lewati tabel log internal sequence SQLite agar skema bersih
    if "sqlite_sequence" in statement:
        continue
    if not statement.endswith(';'):
        statement += ';'
    ddl_statements.append(statement)

full_schema = '\n\n'.join(ddl_statements)

# 4. Cetak ke berkas target .sql
output_file = "skema_babyspa_terkini.sql"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(full_schema)

conn.close()

if len(ddl_statements) > 0:
    print(f"✅ Sukses Besar! Berhasil mengekstrak {len(ddl_statements)} struktur tabel & indeks.")
    print(f"Silakan buka berkas hasil ekspor: {output_file}")
else:
    print("⚠ Peringatan: Berkas ditemukan namun isinya kosong. Pastikan kamu sudah menjalankan 'python manage.py migrate'.")