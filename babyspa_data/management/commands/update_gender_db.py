import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from babyspa_data.models import Customer

class Command(BaseCommand):
    help = 'Memperbarui kolom gender pada tabel Customer dari master_customers.csv'

    def parse_gender(self, val):
        """
        Mengonversi teks dari CSV menjadi Boolean.
        True = Laki-laki, False = Perempuan, None = Tidak diketahui
        """
        if pd.isna(val):
            return None
        
        val_str = str(val).strip().lower()
        
        # Kamus kata kunci Laki-laki
        if val_str in ['male', 'm', 'laki-laki', 'l', 'pria']:
            return True
        # Kamus kata kunci Perempuan
        elif val_str in ['female', 'f', 'perempuan', 'p', 'wanita']:
            return False
            
        return None

    @transaction.atomic
    def handle(self, *args, **options):
        raw_dir = os.path.join("data", "raw")
        csv_path = os.path.join(raw_dir, "master_customers.csv")

        self.stdout.write(f"1. Membaca file {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("File master_customers.csv tidak ditemukan!"))
            return

        # Deteksi otomatis nama kolom untuk gender di CSV
        gender_col = None
        for col in ['Gender', 'Sex', 'Jenis Kelamin', 'gender', 'sex']:
            if col in df.columns:
                gender_col = col
                break
        
        if not gender_col:
            self.stdout.write(self.style.ERROR("Kolom representasi gender tidak ditemukan di CSV!"))
            self.stdout.write("Pastikan file CSV memiliki kolom bernama 'Gender' atau 'Sex'.")
            return

        self.stdout.write(f" -> Kolom terdeteksi: '{gender_col}'")
        self.stdout.write("\n2. Memuat data pelanggan dari database (Memory mapping)...")
        
        # Ambil semua pelanggan dari database dan jadikan dictionary dengan kunci erp_id
        customers_db = {c.erp_id: c for c in Customer.active_objects.all()}
        customers_to_update = []

        self.stdout.write("\n3. Memproses pencocokan data...")
        for _, row in df.iterrows():
            erp_id = row.get('ID')
            if pd.isna(erp_id):
                continue
            
            # Jika pelanggan dengan erp_id tersebut ada di database
            cust_obj = customers_db.get(erp_id)
            if cust_obj:
                new_gender = self.parse_gender(row[gender_col])
                
                # Masukkan ke daftar antrean HANYA jika nilainya berubah atau belum ada
                if cust_obj.gender != new_gender:
                    cust_obj.gender = new_gender
                    customers_to_update.append(cust_obj)

        # 4. EKSEKUSI BULK UPDATE
        if customers_to_update:
            total_update = len(customers_to_update)
            self.stdout.write(f"\n4. Mengeksekusi pembaruan untuk {total_update} pelanggan...")
            
            # bulk_update jauh lebih efisien daripada memanggil .save() satu per satu
            Customer.active_objects.bulk_update(customers_to_update, ['gender'], batch_size=2000)
            
            self.stdout.write(self.style.SUCCESS(f"=== BINGO! Berhasil memperbarui {total_update} data gender ==="))
        else:
            self.stdout.write(self.style.WARNING("\n=== Tidak ada data yang perlu diperbarui (semua sudah sinkron) ==="))