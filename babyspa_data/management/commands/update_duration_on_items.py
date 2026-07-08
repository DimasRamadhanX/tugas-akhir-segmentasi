import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
# Menggunakan model Product secara murni
from babyspa_data.models.product import Product


class Command(BaseCommand):
    help = "Membaca CSV, sinkronisasi Master-Variant menggunakan active_objects dengan toleransi kesamaan nama"

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help='Bypass interactive confirmation',
        )

    def handle(self, *args, **options):
        FILE_PATH = r"C:\babyspa-data\data\raw\master_items.csv"

        if not os.path.exists(FILE_PATH):
            self.stdout.write(
                self.style.ERROR(f"⚠ File tidak ditemukan di: {FILE_PATH}")
            )
            return

        self.stdout.write(f"🔄 Membaca data dari: {FILE_PATH}")
        df = pd.read_csv(FILE_PATH)

        # Standarisasi nilai teks untuk menghindari error NaN / Float kosong dari pandas
        df["Variant Name"] = df["Variant Name"].fillna("").astype(str).str.strip()
        df["Item Name"] = df["Item Name"].fillna("").astype(str).str.strip()
        df["Duration"] = df["Duration"].fillna("").astype(str).str.strip()

        def clean_price(price_val):
            if pd.isna(price_val):
                return 0.0
            p_str = (
                str(price_val).replace(".", "").replace(",", ".").strip()
            )
            try:
                return float(p_str)
            except:
                return 0.0

        # =============================================================================
        # RENDERING TABEL PREVIEW DATA SEBELUM KONFIRMASI
        # =============================================================================
        total_rows = len(df)
        self.stdout.write(f"\n📊 TOTAL DATA TERDETEKSI: {total_rows} BARIS")
        self.stdout.write("=========================================================================================")
        self.stdout.write("📋 PREVIEW PEMETAAN DATA DAN DURASI (10 BARIS PERTAMA):")
        self.stdout.write("=========================================================================================")
        
        preview_cols = ["Item Name", "Variant Name", "Duration"]
        if "Duration_Minutes" in df.columns:
            preview_cols.append("Duration_Minutes")
            
        self.stdout.write(df[preview_cols].head(10).to_string(index=False))
        self.stdout.write("=========================================================================================\n")

        # =============================================================================
        # KONFIRMASI INTERAKTIF (YA / TIDAK)
        # =============================================================================
        if options.get('no_input'):
            pilihan = 'ya'
            self.stdout.write("🚀 Memulai proses sinkronisasi data melalui active_objects...")
        else:
            while True:
                pilihan = (
                    input("Apakah data di atas sudah benar dan siap disimpan ke database? (ya/tidak): ")
                    .strip()
                    .lower()
                )
                if pilihan == "ya":
                    self.stdout.write("🚀 Memulai proses sinkronisasi data melalui active_objects...")
                    break
                elif pilihan == "tidak":
                    self.stdout.write(
                        self.style.WARNING("❌ Proses dibatalkan oleh pengguna.")
                    )
                    return
                else:
                    self.stdout.write("Pilihan tidak valid. Ketik 'ya' atau 'tidak'.")

        # =============================================================================
        # PROSES SINKRONISASI MURNI MENGGUNAKAN active_objects
        # =============================================================================
        try:
            with transaction.atomic():
                # --- TAHAP 1: SINKRONISASI PRODUK MASTER INDUK ---
                self.stdout.write("\n-> Tahap 1: Memproses Produk Master...")
                
                # Baris master di CSV diidentifikasi dari kolom 'Variant Name' yang kosong
                df_master = df[df["Variant Name"] == ""].drop_duplicates(subset=["Item Name"])

                for _, row in df_master.iterrows():
                    # Kueri murni menggunakan active_objects
                    existing_masters = Product.active_objects.filter(
                        item_name=row["Item Name"], 
                        master_product__isnull=True
                    )

                    if existing_masters.exists():
                        # Update data pada record pertama yang ditemukan
                        master_obj = existing_masters.first()
                        master_obj.retail_price = clean_price(row["Retail Price"])
                        master_obj.description = row["Description"] if pd.notna(row["Description"]) else ""
                        master_obj.duration = int(row["Duration_Minutes"]) if "Duration_Minutes" in row else 0
                        master_obj.save()

                        # Deteksi dan bersihkan duplikasi master jika ada lebih dari satu di DB
                        if existing_masters.count() > 1:
                            duplicate_ids = existing_masters.values_list('id', flat=True)[1:]
                            Product.active_objects.filter(id__in=duplicate_ids).delete()
                    else:
                        # Buat data master baru jika belum tersedia
                        Product.active_objects.create(
                            item_name=row["Item Name"],
                            master_product=None,
                            retail_price=clean_price(row["Retail Price"]),
                            description=row["Description"] if pd.notna(row["Description"]) else "",
                            duration=int(row["Duration_Minutes"]) if "Duration_Minutes" in row else 0,
                        )

                # --- TAHAP 2: SINKRONISASI PRODUK VARIANT ---
                self.stdout.write("-> Tahap 2: Menghubungkan Produk Variant ke master_product_id...")
                
                # Ambil baris yang memiliki Variant Name
                df_variant = df[df["Variant Name"] != ""].drop_duplicates(subset=["Item Name", "Variant Name"])

                for _, row in df_variant.iterrows():
                    # Cari produk induknya terlebih dahulu di active_objects berdasarkan Item Name di CSV
                    parent_product = Product.active_objects.filter(
                        item_name=row["Item Name"], 
                        master_product__isnull=True
                    ).first()

                    # Antisipasi jika master tidak sengaja absen, buat otomatis sebagai langkah pengaman
                    if not parent_product:
                        parent_product = Product.active_objects.create(
                            item_name=row["Item Name"],
                            retail_price=clean_price(row["Retail Price"]),
                            description=row["Description"] if pd.notna(row["Description"]) else "",
                            duration=int(row["Duration_Minutes"]) if "Duration_Minutes" in row else 0,
                            master_product=None
                        )

                    # [AKURASI]: Gunakan Variant Name langsung dari CSV untuk nama di database.
                    # Ini mengakomodasi jika nama variant sama persis dengan nama master tanpa merusak struktur sumbu FK.
                    target_variant_name = row["Variant Name"]
                    
                    existing_variants = Product.active_objects.filter(
                        item_name=target_variant_name,
                        master_product=parent_product
                    )

                    if existing_variants.exists():
                        # Update variant aktif pertama yang ditemukan
                        variant_obj = existing_variants.first()
                        variant_obj.retail_price = clean_price(row["Retail Price"])
                        variant_obj.description = row["Description"] if pd.notna(row["Description"]) else ""
                        variant_obj.duration = int(row["Duration_Minutes"]) if "Duration_Minutes" in row else 0
                        variant_obj.save()

                        # Bersihkan duplikasi variant ganda yang menginduk ke master yang sama
                        if existing_variants.count() > 1:
                            duplicate_variant_ids = existing_variants.values_list('id', flat=True)[1:]
                            Product.active_objects.filter(id__in=duplicate_variant_ids).delete()
                    else:
                        # Tambahkan variant baru dan kunci relasi ID master ke kolom master_product_id
                        Product.active_objects.create(
                            item_name=target_variant_name,
                            master_product=parent_product,
                            retail_price=clean_price(row["Retail Price"]),
                            description=row["Description"] if pd.notna(row["Description"]) else "",
                            duration=int(row["Duration_Minutes"]) if "Duration_Minutes" in row else 0,
                        )

            self.stdout.write(
                self.style.SUCCESS("========================================================")
            )
            self.stdout.write(
                self.style.SUCCESS("✅ BERHASIL: Sinkronisasi active_objects selesai tanpa manipulasi string nama!")
            )
            self.style.SUCCESS("========================================================")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Terjadi kegagalan saat sinkronisasi data: {str(e)}")
            )