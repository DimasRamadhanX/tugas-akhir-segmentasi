import os
import re
import pandas as pd
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db import transaction
from django.utils.text import slugify
from babyspa_data.models import Customer, Branch, Product, ProductCategory, Transaction, TransactionItem

class Command(BaseCommand):
    help = 'Normalisasi CSV mentah dengan Bulk Insert dan Pemisah Tabel yang Jelas (disinkronkan dengan pipeline)'

    def clean_price(self, price_str):
        if pd.isna(price_str) or price_str == "":
            return 0.0
        if isinstance(price_str, str):
            price_str = price_str.replace('.', '').replace(',', '.')
        try:
            return float(price_str)
        except ValueError:
            return 0.0

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

    def parse_duration_to_minutes(self, dur_str):
        """
        Mengonversi string seperti '1h 45min', '1h', atau '30min' menjadi total menit.
        """
        if pd.isna(dur_str) or not str(dur_str).strip():
            return 0.0
            
        dur_str = str(dur_str).lower().strip()
        hours = 0
        minutes = 0
        
        # Ekstrak jam (h)
        h_match = re.search(r'(\d+)\s*h', dur_str)
        if h_match:
            hours = int(h_match.group(1))
            
        # Ekstrak menit (m / min)
        m_match = re.search(r'(\d+)\s*m', dur_str)
        if m_match:
            minutes = int(m_match.group(1))
            
        return float((hours * 60) + minutes)

    @transaction.atomic
    def handle(self, *args, **options):
        raw_dir = os.path.join("data", "raw")
        
        # ==========================================
        # 0. TRUNCATE DATABASE LAMA
        # ==========================================
        self.stdout.write(self.style.WARNING("0. Menghapus (Truncate) data lama di database..."))
        TransactionItem.active_objects.all().delete()
        Transaction.active_objects.all().delete()
        Product.active_objects.all().delete()
        Customer.active_objects.all().delete()
        Branch.active_objects.all().delete()
        self.stdout.write(self.style.SUCCESS("   -> Database berhasil dikosongkan!"))

        # ==========================================
        # 1. LOAD DATASET CSV
        # ==========================================
        self.stdout.write("\n1. Membaca file CSV mentah...")
        try:
            df_cust = pd.read_csv(os.path.join(raw_dir, "master_customers.csv"))
            df_item_master = pd.read_csv(os.path.join(raw_dir, "master_items.csv"))
            df_tx_items = pd.read_csv(os.path.join(raw_dir, "master_transaction_items.csv"))
            df_tx_headers = pd.read_csv(os.path.join(raw_dir, "master_transaction_headers.csv"))
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"File tidak ditemukan: {e}"))
            return

        # ==========================================
        # --- INSERT TABLE: BRANCH ---
        # ==========================================
        self.stdout.write("\n2. Menyimpan Master Cabang...")
        branches = {
            4807: {"name": "Solo_Manahan", "city": "Surakarta"},
            4883: {"name": "Jogja_Maguwo", "city": "Yogyakarta"},
            12482: {"name": "Jogja_Bausasran", "city": "Yogyakarta"},
            12483: {"name": "Solo_Baru", "city": "Surakarta"},
            13158: {"name": "Gresik", "city": "Gresik"}
        }
        branch_objs = {}
        for loc_id, data in branches.items():
            branch, _ = Branch.active_objects.get_or_create(
                location_id=loc_id,
                defaults={"branch_name": data["name"], "city": data["city"]}
            )
            branch_objs[loc_id] = branch

        # ==========================================
        # --- INSERT TABLE: PRODUCT ---
        # ==========================================
        total_items = len(df_item_master)
        self.stdout.write(f"\n3. Menyimpan Master Produk ({total_items} baris dari master + on-the-fly)...")
        
        # A. Get-or-Create Kategori Unik
        kategori_unik = set()
        for idx, row in df_item_master.iterrows():
            treatment_name = row.get('Treatment Name')
            if pd.notna(treatment_name) and str(treatment_name).strip():
                kategori_unik.add(str(treatment_name).strip())
                
        category_db_map = {}
        for cat_name in kategori_unik:
            category_obj, _ = ProductCategory.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name)}
            )
            category_db_map[cat_name.lower()] = category_obj

        products_to_create = []
        registered_products = set()

        # B. Produk dari File Master Items
        for idx, row in df_item_master.iterrows():
            item_name = str(row.get('Item Name', '')).strip()
            if not item_name or item_name == 'nan': continue
            
            retail_price = self.clean_price(row.get('Retail Price', '0'))
            is_addon = True if "MASKER" in item_name.upper() or "ADDITIONAL" in item_name.upper() else False
            description = row.get('Description')
            if pd.isna(description):
                description = ""

            treatment_name = row.get('Treatment Name')
            category_obj = None
            if pd.notna(treatment_name) and str(treatment_name).strip().lower() in category_db_map:
                category_obj = category_db_map[str(treatment_name).strip().lower()]

            duration_val = 0
            if "Duration_Minutes" in row and pd.notna(row["Duration_Minutes"]):
                try:
                    duration_val = int(row["Duration_Minutes"])
                except ValueError:
                    duration_val = 0
            elif "Duration" in row and pd.notna(row["Duration"]):
                duration_val = int(self.parse_duration_to_minutes(row["Duration"]))

            products_to_create.append(Product(
                erp_item_id=row.get('ID'),
                item_name=item_name,
                retail_price=retail_price,
                is_addon=is_addon,
                description=description,
                category=category_obj,
                duration=duration_val
            ))
            registered_products.add(item_name)

        # C. Produk Siluman (Ada di Transaksi tapi tidak ada di Master)
        for _, row in df_tx_items.iterrows():
            service_name = str(row.get('Service', '')).strip()
            if service_name and service_name != 'nan' and service_name not in registered_products:
                duration_val = 0
                if "Duration" in row and pd.notna(row["Duration"]):
                    duration_val = int(self.parse_duration_to_minutes(row["Duration"]))
                products_to_create.append(Product(
                    item_name=service_name,
                    retail_price=self.clean_price(row.get('Price', '0')),
                    is_addon=False,
                    duration=duration_val
                ))
                registered_products.add(service_name)

        # Eksekusi Insert Massal Produk
        Product.active_objects.bulk_create(products_to_create, ignore_conflicts=True)
        product_dict = {p.item_name: p for p in Product.active_objects.all()}

        # ==========================================
        # --- INSERT TABLE: CUSTOMER ---
        # ==========================================
        total_cust = len(df_cust)
        self.stdout.write(f"\n4. Menyimpan Master Customer ({total_cust} baris)...")
        customers_to_create = []
        
        for idx, row in df_cust.iterrows():
            raw_name = str(row.get('Name', '')).strip()
            if not raw_name or raw_name == 'nan': continue
            
            dob = row.get('Date of Birth')
            customers_to_create.append(Customer(
                erp_id=row['ID'], 
                name=raw_name,
                gender=self.parse_gender(row.get('Gender')),
                date_of_birth=dob if not pd.isna(dob) else None
            ))

        # Eksekusi Insert Massal Customer
        Customer.active_objects.bulk_create(customers_to_create, ignore_conflicts=True)
        customer_name_map = {c.name: c for c in Customer.active_objects.all()}

        # ==========================================
        # PERSIAPAN MEMORI: KAMUS STATUS & SCHEDULED DATE DARI HEADER
        # ==========================================
        self.stdout.write("\n-> Menyiapkan pemetaan Status & Waktu dari file Header...")
        header_status_map = {}
        header_time_lookup = {}
        df_tx_headers['dt'] = pd.to_datetime(df_tx_headers['Invoice Time'], errors='coerce')
        for _, row in df_tx_headers.iterrows():
            cust_name = str(row.get('Customer', '')).strip()
            inv_date = str(row.get('Invoice Date', '')).strip()
            status = str(row.get('Status', 'PAID')).strip().upper()
            
            # Logika Kunci 100% Asli
            if cust_name and inv_date:
                header_status_map[(cust_name, inv_date)] = status

            if pd.notna(row.get('dt')):
                aware_dt = timezone.make_aware(row['dt']) if timezone.is_naive(row['dt']) else row['dt']
                ref = str(row['Invoice#'])
                header_time_lookup[ref] = aware_dt
                if cust_name and inv_date:
                    header_time_lookup[(cust_name.lower(), inv_date)] = aware_dt

        # ==========================================
        # PERSIAPAN MEMORI: AKUMULASI TRANSAKSI & ITEM
        # ==========================================
        total_tx = len(df_tx_items)
        self.stdout.write(f"\n5. Membentuk Keranjang Transaksi & Item di Memori ({total_tx} baris)...")
        
        tx_accumulator = {}

        for idx, row in df_tx_items.iterrows():
            client_name = str(row.get('Client', '')).strip()
            loc_id = row.get('Branch_ID')
            service_name = str(row.get('Service', '')).strip()
            total_price = self.clean_price(row.get('Price', '0'))
            item_status = str(row.get('Status', 'COMPLETED')).strip().upper()
            item_ref_number = str(row.get('Ref #', '')).strip() 
            
            if client_name not in customer_name_map or loc_id not in branch_objs or not service_name or service_name == 'nan':
                continue
                
            customer_instance = customer_name_map[client_name]

            raw_date_str = str(row.get('Scheduled Date', ''))
            scheduled_date = parse_datetime(raw_date_str)
            
            if not scheduled_date and raw_date_str:
                scheduled_date = parse_datetime(f"{raw_date_str} 00:00:00")
                
            if scheduled_date and timezone.is_naive(scheduled_date):
                scheduled_date = timezone.make_aware(scheduled_date)

            if not scheduled_date: continue

            # Ambil Status Induk dari Kamus Header
            status_induk_asli = header_status_map.get((client_name, raw_date_str), 'UNKNOWN')

            # Tentukan scheduled_date transaksi induk menggunakan data header (jika ada)
            tx_scheduled_date = scheduled_date
            cust_name_key = customer_instance.name.lower().strip()
            tx_date_str = scheduled_date.strftime('%Y-%m-%d')
            if (cust_name_key, tx_date_str) in header_time_lookup:
                tx_scheduled_date = header_time_lookup[(cust_name_key, tx_date_str)]

            # Logika Grouping Transaksi 100% Asli (Customer ID + Tanggal)
            tx_key = (customer_instance.id, scheduled_date.date())

            if tx_key not in tx_accumulator:
                basket_id = f"BSK-{customer_instance.id}-{scheduled_date.strftime('%Y%m%d')}"
                
                tx_accumulator[tx_key] = {
                    'obj': Transaction(
                        ref_number=basket_id,
                        customer=customer_instance,
                        branch=branch_objs[loc_id],
                        scheduled_date=tx_scheduled_date,
                        total_price=total_price, 
                        status=status_induk_asli
                    ),
                    'items': []
                }
            else:
                # Logika Update Harga dan Status Induk 100% Asli
                tx_accumulator[tx_key]['obj'].total_price += total_price
                if tx_accumulator[tx_key]['obj'].status == 'UNKNOWN' and status_induk_asli != 'UNKNOWN':
                    tx_accumulator[tx_key]['obj'].status = status_induk_asli

            # Tentukan scheduled_date untuk TransactionItem
            raw_time_str = str(row.get('Time', '')).strip()
            item_scheduled_date = scheduled_date
            if raw_time_str and raw_time_str != 'nan':
                dt_str = f"{raw_date_str} {raw_time_str}"
                parsed_dt = parse_datetime(dt_str)
                if parsed_dt:
                    if timezone.is_naive(parsed_dt):
                        item_scheduled_date = timezone.make_aware(parsed_dt)
                    else:
                        item_scheduled_date = parsed_dt

            # Kumpulkan Item Sementara
            tx_accumulator[tx_key]['items'].append(TransactionItem(
                ref_number=item_ref_number, 
                product=product_dict[service_name],
                quantity=1,
                status=item_status,
                sale_price=total_price,
                duration=self.parse_duration_to_minutes(row.get('Duration', '')),
                scheduled_date=item_scheduled_date
            ))

        # ==========================================
        # --- INSERT TABLE: TRANSACTION ---
        # ==========================================
        self.stdout.write("\n6. Menyimpan Transaksi Utama (Transaction) secara Massal...")
        Transaction.active_objects.bulk_create([data['obj'] for data in tx_accumulator.values()], batch_size=2000)

        # Menarik kembali ID dari DB untuk disambungkan ke relasi Items
        saved_transactions = {tx.ref_number: tx for tx in Transaction.active_objects.all()}

        # ==========================================
        # --- INSERT TABLE: TRANSACTION ITEM ---
        # ==========================================
        self.stdout.write("\n7. Menyimpan Detail Item (TransactionItem) secara Massal...")
        final_items_to_create = []
        
        for data in tx_accumulator.values():
            tx_parent = saved_transactions[data['obj'].ref_number]
            for item_obj in data['items']:
                item_obj.transaction = tx_parent
                final_items_to_create.append(item_obj)

        TransactionItem.active_objects.bulk_create(final_items_to_create, batch_size=3000)

        self.stdout.write(self.style.SUCCESS("\n=== BINGO! Migrasi Bulk Insert Selesai & Keranjang Terbentuk ==="))

        self.stdout.write(self.style.NOTICE("\n=== Running downstream update commands... ==="))
        call_command('update_duration_on_items', no_input=True)
        call_command('update_product_normalization_variant', no_input=True)
        call_command('update_branch_products', no_input=True)
        self.stdout.write(self.style.SUCCESS("\n=== CONSOLIDATED DB IMPORT PIPELINE FINISHED ==="))