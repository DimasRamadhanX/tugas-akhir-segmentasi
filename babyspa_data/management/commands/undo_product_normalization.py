from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from babyspa_data.models.product import Product

class Command(BaseCommand):
    help = 'Membatalkan proses normalisasi dengan mendeteksi produk master aktif secara spesifik'

    def handle(self, *args, **options):
        self.stdout.write("Memulai analisis data untuk UNDO normalisasi produk...")

        # 1. Filter produk master berdasarkan struktur relasi pasca-command
        master_virtual = Product.active_objects.filter(
            retail_price=0.0,
            master_product__isnull=True
        ).annotate(
            total_varian_terikat=Count('variants')
        ).filter(
            total_varian_terikat__gt=0 
        )

        total_master = master_virtual.count()

        # Jika tidak ada data, langsung hentikan proses
        if total_master == 0:
            self.stdout.write(self.style.WARNING("Tidak ada produk master hasil normalisasi yang ditemukan."))
            return

        # 2. Tampilkan daftar produk terlebih dahulu untuk ditinjau oleh pengguna
        self.stdout.write(self.style.WARNING(f"\n[!] Ditemukan {total_master} produk master aktif yang akan DIHAPUS:"))
        for master in master_virtual:
            self.stdout.write(
                f"    -> Master: '{master.item_name}' (Mengikat {master.total_varian_terikat} produk varian)"
            )
        
        self.stdout.write("\n")
        
        # 3. Minta Konfirmasi Interaktif (y/n)
        konfirmasi = input("Apakah Anda yakin ingin membatalkan normalisasi dan menghapus produk di atas? (y/n): ")

        if konfirmasi.strip().lower() != 'y':
            self.stdout.write(self.style.ERROR("\nProses dibatalkan oleh pengguna. Tidak ada perubahan pada database."))
            return

        # 4. Ambil daftar ID master untuk pengamanan kueri delete
        # Django terkadang membatasi .delete() langsung pada queryset yang memiliki .annotate()
        master_ids = list(master_virtual.values_list('id', flat=True))

        # 5. Jalankan eksekusi aman di dalam transaksi atomik setelah dikonfirmasi
        with transaction.atomic():
            self.stdout.write(f"\n[-] Mengeksekusi penghapusan massal terhadap {len(master_ids)} produk master...")
            
            # Tembak langsung berdasarkan ID yang sudah divalidasi
            Product.active_objects.filter(id__in=master_ids).delete()

        self.stdout.write(self.style.SUCCESS("="*50))
        self.stdout.write(self.style.SUCCESS("PROSES UNDO SELESAI!"))
        self.stdout.write(self.style.SUCCESS(f"Total produk master yang dihapus: {total_master}"))
        self.stdout.write(self.style.SUCCESS("Semua produk varian otomatis terlepas kembali menjadi NULL dengan aman."))
        self.stdout.write(self.style.SUCCESS("="*50))