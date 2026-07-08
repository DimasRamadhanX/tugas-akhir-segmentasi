import os
import csv
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction
from babyspa_data.models import Product, ProductCategory

class Command(BaseCommand):
    help = 'Populasi otomatis kategori unik dari CSV dan update relasi kategori pada model Product'

    def handle(self, *args, **options):
        csv_path = r"C:\babyspa-data\data\raw\master_items.csv"
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"File tidak ditemukan di jalur: {csv_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"Membaca data dari {csv_path}..."))

        # Tempat penampungan data CSV
        # Kategori unik menggunakan set untuk eliminasi duplikat
        kategori_unik = set()
        # Map relasi: {item_name_lower: treatment_name}
        csv_product_map = {}

        try:
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Menyesuaikan nama kolom sesuai instruksi (Item Name dan Treatment Name)
                required_columns = {'Item Name', 'Treatment Name'}
                if not required_columns.issubset(reader.fieldnames):
                    self.stdout.write(self.style.ERROR(
                        f"Struktur kolom CSV salah! Harus memiliki kolom {required_columns}. "
                        f"Kolom yang ditemukan: {reader.fieldnames}"
                    ))
                    return

                for row in reader:
                    item_name = row['Item Name'].strip() if row['Item Name'] else None
                    treatment_name = row['Treatment Name'].strip() if row['Treatment Name'] else None
                    
                    if item_name and treatment_name:
                        kategori_unik.add(treatment_name)
                        csv_product_map[item_name.lower()] = treatment_name
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gagal membaca file CSV: {str(e)}"))
            return

        # Proses database dijalankan secara atomik
        with transaction.atomic():
            # ==================================================================
            # TAHAP 1: POPULASI DATA KATEGORI SECARA UNIK
            # ==================================================================
            self.stdout.write(self.style.NOTICE(f"\n[-] Menyingkronkan {len(kategori_unik)} kategori unik ke database..."))
            category_db_map = {} # Map untuk reuse objek: {nama_kategori_lower: objek_kategori}

            for cat_name in kategori_unik:
                # Ambil atau buat data baru berdasarkan nama kategori
                category_obj, created = ProductCategory.objects.get_or_create(
                    name=cat_name,
                    defaults={'slug': slugify(cat_name)}
                )
                category_db_map[cat_name.lower()] = category_obj
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f" 📂 Kategori baru dibuat: '{cat_name}'"))

            # ==================================================================
            # TAHAP 2: COCOKKAN DAN UPDATE RELASI KATEGORI PADA PRODUCT
            # ==================================================================
            db_products = Product.active_objects.all()
            updated_count = 0
            
            self.stdout.write(self.style.NOTICE(f"\n[-] Menghubungkan kategori ke {db_products.count()} produk di database..."))

            for product in db_products:
                db_name_key = product.item_name.strip().lower()
                
                # Jika nama produk di DB terdaftar di dalam kamus Item Name CSV
                if db_name_key in csv_product_map:
                    target_treatment_name = csv_product_map[db_name_key]
                    category_obj = category_db_map.get(target_treatment_name.lower())
                    
                    if category_obj:
                        # Update hanya jika kategorinya kosong atau berubah
                        if product.category_id != category_obj.id:
                            product.category = category_obj
                            product.save(update_fields=['category', 'updated_at'])
                            updated_count += 1
                            
                            self.stdout.write(self.style.SUCCESS(
                                f" 🔗 Linked: '{product.item_name}' ----> Kategori: '{category_obj.name}'"
                            ))

        # Laporan akhir eksekusi
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(f"PROSES MIGRASI KATEGORI SELESAI!"))
        self.stdout.write(self.style.SUCCESS(f"Total produk yang berhasil di-update kategorinya: {updated_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))