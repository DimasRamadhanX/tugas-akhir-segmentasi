import os
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from babyspa_data.models import Product

class Command(BaseCommand):
    help = 'Upsert deskripsi produk dari master_items.csv berdasarkan kesamaan nama produk'

    def handle(self, *args, **options):
        csv_path = r"C:\babyspa-data\data\raw\master_items.csv"
        
        # 1. Validasi keberadaan file CSV
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"File tidak ditemukan di jalur: {csv_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"Membaca data dari {csv_path}..."))

        # 2. Muat data CSV ke dalam dictionary untuk pencarian cepat (O(1))
        # Format map: {nama_produk_lower: deskripsi}
        csv_data_map = {}
        
        try:
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Cek validitas kolom wajib di CSV
                required_columns = {'Item Name', 'Description'}
                if not required_columns.issubset(reader.fieldnames):
                    self.stdout.write(self.style.ERROR(
                        f"Struktur CSV salah! Harus memiliki kolom {required_columns}. "
                        f"Kolom yang ditemukan: {reader.fieldnames}"
                    ))
                    return

                for row in reader:
                    name_key = str(row['Item Name']).strip().lower()
                    description_value = row['Description'].strip() if row['Description'] else None
                    
                    if name_key:
                        csv_data_map[name_key] = description_value
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gagal membaca file CSV: {str(e)}"))
            return

        # 3. Tarik semua produk aktif dari database
        db_products = Product.active_objects.all()
        updated_count = 0

        self.stdout.write(f"Menyamakan data dengan {db_products.count()} produk aktif di database...")

        # 4. Proses update massal menggunakan transaksi atomik demi keamanan data
        with transaction.atomic():
            for product in db_products:
                db_name_key = product.item_name.strip().lower()
                
                # Jika ditemukan kecocokan nama (exact same secara case-insensitive)
                if db_name_key in csv_data_map:
                    new_description = csv_data_map[db_name_key]
                    
                    # Hanya update jika deskripsinya memang berbeda atau berubah
                    if product.description != new_description:
                        product.description = new_description
                        product.save(update_fields=['description', 'updated_at'])
                        updated_count += 1
                        
                        self.stdout.write(self.style.SUCCESS(
                            f" ✅ Diperbarui: '{product.item_name}'"
                        ))

        # 5. Output laporan akhir eksekusi
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"PROSES SELESAI!"))
        self.stdout.write(self.style.SUCCESS(f"Total produk yang berhasil di-upsert deskripsinya: {updated_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))