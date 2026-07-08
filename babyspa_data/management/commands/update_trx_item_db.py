import os
import re
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db import transaction
from babyspa_data.models import TransactionItem

class Command(BaseCommand):
    help = 'Memperbarui sale_price, duration (menit), dan scheduled_date pada TransactionItem'

    def clean_price(self, price_str):
        if pd.isna(price_str) or price_str == "":
            return 0.0
        if isinstance(price_str, (int, float)):
            return float(price_str)
        if isinstance(price_str, str):
            price_str = price_str.replace('.', '').replace(',', '.')
        try:
            return float(price_str)
        except ValueError:
            return 0.0

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
        csv_path = os.path.join(raw_dir, "master_transaction_items.csv")
        
        self.stdout.write(f"1. Membaca file {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("File tidak ditemukan!"))
            return

        self.stdout.write("2. Memuat data TransactionItem dari database ke memori...")
        # Dictionary lookup O(1) agar cepat. Menggunakan ref_number sebagai kunci.
        items_db = {item.ref_number: item for item in TransactionItem.active_objects.all() if item.ref_number}
        items_to_update = []

        self.stdout.write("3. Memproses perhitungan dan pencocokan data...")
        for _, row in df.iterrows():
            ref_num = str(row.get('Ref #', '')).strip()
            
            if not ref_num or ref_num not in items_db:
                continue

            item_obj = items_db[ref_num]
            needs_update = False

            # --- A. Pemrosesan Harga Jual ---
            sale_price = self.clean_price(row.get('Price', '0'))
            if item_obj.sale_price != sale_price:
                item_obj.sale_price = sale_price
                needs_update = True

            # --- B. Pemrosesan Durasi ke Menit ---
            duration_minutes = self.parse_duration_to_minutes(row.get('Duration', ''))
            if item_obj.duration != duration_minutes:
                item_obj.duration = duration_minutes
                needs_update = True

            # --- C. Pemrosesan Tanggal & Waktu ---
            raw_date = str(row.get('Scheduled Date', '')).strip()
            raw_time = str(row.get('Time', '')).strip()
            
            if raw_date and raw_date != 'nan':
                # Gabungkan tanggal dan waktu
                dt_str = f"{raw_date} {raw_time}" if raw_time and raw_time != 'nan' else f"{raw_date} 00:00:00"
                scheduled_date = parse_datetime(dt_str)
                
                if scheduled_date:
                    if timezone.is_naive(scheduled_date):
                        scheduled_date = timezone.make_aware(scheduled_date)
                    
                    if item_obj.scheduled_date != scheduled_date:
                        item_obj.scheduled_date = scheduled_date
                        needs_update = True

            # Jika ada perubahan pada salah satu kolom, masukkan ke antrean update
            if needs_update:
                items_to_update.append(item_obj)

        # 4. EKSEKUSI BULK UPDATE
        if items_to_update:
            total_update = len(items_to_update)
            self.stdout.write(f"\n4. Mengeksekusi pembaruan untuk {total_update} baris TransactionItem...")
            
            # Hanya memperbarui 3 kolom ini agar hemat memori
            TransactionItem.active_objects.bulk_update(
                items_to_update, 
                ['sale_price', 'duration', 'scheduled_date'], 
                batch_size=3000
            )
            
            self.stdout.write(self.style.SUCCESS(f"=== BINGO! Berhasil memperbarui {total_update} data ==="))
        else:
            self.stdout.write(self.style.WARNING("\n=== Tidak ada data yang perlu diperbarui ==="))