import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.db import transaction
from babyspa_data.models.transactions import Transaction, TransactionItem

class Command(BaseCommand):
    help = 'Update scheduled_date Header dan Item secara atomik menggunakan data CSV'

    # Konfigurasi Path (Bisa dipindah ke settings jika perlu)
    PATH_HEADER = 'data/raw/master_transaction_headers.csv'
    PATH_ITEM = 'data/raw/master_transaction_items.csv'

    @transaction.atomic
    def handle(self, *args, **options):
        """
        Entry point utama dengan dekorator atomic untuk menjamin integritas data.
        Jika salah satu bagian gagal, seluruh transaksi akan di-rollback.
        """
        count_h = self._update_headers()
        count_i = self._update_items()

        self.stdout.write(self.style.SUCCESS(
            f"Selesai!\n"
            f"- Header diperbarui: {count_h}\n"
            f"- Item diperbarui: {count_i}"
        ))

    def _update_headers(self):
        """Logika internal untuk memperbarui tabel Transaction."""
        self.stdout.write("Memproses Header dari CSV...")
        df = pd.read_csv(self.PATH_HEADER)
        
        # '31 Dec 2022 12:48' langsung dikonversi
        df['dt'] = pd.to_datetime(df['Invoice Time'], errors='coerce')
        
        count = 0
        for _, row in df.dropna(subset=['dt']).iterrows():
            ref = str(row['Invoice#'])
            aware_dt = make_aware(row['dt'])
            
            # Penggunaan .update() lebih cepat karena langsung ke SQL
            updated = Transaction.active_objects.filter(ref_number=ref).update(scheduled_date=aware_dt)
            count += updated
            
        return count

    def _update_items(self):
        """Logika internal untuk memperbarui tabel TransactionItem."""
        self.stdout.write("Memproses Item dari CSV...")
        df = pd.read_csv(self.PATH_ITEM)
        
        # Gabungkan tanggal dan jam
        df['full_dt_str'] = df['Scheduled Date'].astype(str) + ' ' + df['Time'].astype(str)
        df['dt'] = pd.to_datetime(df['full_dt_str'], errors='coerce')
        
        count = 0
        for _, row in df.dropna(subset=['dt']).iterrows():
            ref = str(row['Ref #'])
            aware_dt = make_aware(row['dt'])
            
            updated = TransactionItem.active_objects.filter(ref_number=ref).update(scheduled_date=aware_dt)
            count += updated
            
        return count