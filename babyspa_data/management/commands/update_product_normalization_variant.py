import re
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db import transaction
from babyspa_data.models.product import Product

class Command(BaseCommand):
    help = 'Mendeteksi varian produk daerah secara ketat (anti-kata-kebalik), membuat Master Product, dan merelasikannya'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help='Bypass interactive confirmation',
        )

    def hitung_kemiripan_spesifik(self, str1, str2):
        s1_lower = str1.lower().strip()
        s2_lower = str2.lower().strip()
        
        # =====================================================================
        # FILTER 1: Deteksi Eksklusivitas Kata "Bundling"
        # =====================================================================
        if ('bundling' in s1_lower) != ('bundling' in s2_lower):
            return 0.10
            
        # =====================================================================
        # FILTER 2: Syarat Karakteristik Layanan (Light, Lite, Bright)
        # =====================================================================
        set_karakteristik = {'light', 'lite', 'bright'}
        has_char1 = [w for w in set_karakteristik if w in s1_lower]
        has_char2 = [w for w in set_karakteristik if w in s2_lower]
        if has_char1 != has_char2:
            return 0.10

        # =====================================================================
        # FILTER 3: Eksklusivitas Jenis Tindakan Medis/Terapi (Nebu & Massage)
        # =====================================================================
        if ('nebu' in s1_lower) != ('nebu' in s2_lower):
            return 0.10
        if ('massage' in s1_lower) != ('massage' in s2_lower):
            return 0.10

        # =====================================================================
        # FILTER 4: Segmen Umur (Kid/Kids vs Baby)
        # =====================================================================
        is_kid1 = ('kid' in s1_lower or 'kids' in s1_lower)
        is_kid2 = ('kid' in s2_lower or 'kids' in s2_lower)
        is_baby1 = ('baby' in s1_lower)
        is_baby2 = ('baby' in s2_lower)
        if (is_kid1 != is_kid2) or (is_baby1 != is_baby2):
            return 0.10

        # =====================================================================
        # FILTER 5: Ekstrak Semua Angka (Validasi Urutan/Tingkatan Paket)
        # =====================================================================
        angka1 = re.findall(r'\d+', s1_lower)
        angka2 = re.findall(r'\d+', s2_lower)
        if angka1 != angka2:
            return 0.10

        # =====================================================================
        # PENANGANAN JITU: ANTI-KATA-KEBALIK (Token Set Intersection)
        # =====================================================================
        target_daerah = {'solo baru', 'solo', 'sby', 'surabaya', 'gresik', 'jogja', 'sunny'}
        
        words1 = {w for w in s1_lower.split() if w not in target_daerah}
        words2 = {w for w in s2_lower.split() if w not in target_daerah}
        
        words1_norm = {w[:-1] if w.endswith('s') and len(w) > 2 else w for w in words1}
        words2_norm = {w[:-1] if w.endswith('s') and len(w) > 2 else w for w in words2}
        
        if words1_norm == words2_norm:
            return 0.99

        # =====================================================================
        # FILTER 6: Kedekatan Urutan Teks (Fuzzy Sequence Matching)
        # =====================================================================
        base_score = SequenceMatcher(None, s1_lower, s2_lower).ratio()

        # FILTER 7: Bonus Substring Penanda Daerah
        if any(daerah in s1_lower for daerah in target_daerah) or any(daerah in s2_lower for daerah in target_daerah):
            base_score += 0.15
            
        return min(base_score, 0.99)

    def get_sequential_intersection(self, name1, name2):
        words1 = name1.split()
        words2 = name2.split()
        matcher = SequenceMatcher(None, words1, words2)
        common_words = []
        for block in matcher.get_matching_blocks():
            common_words.extend(words1[block.a : block.a + block.size])
        return " ".join(common_words).strip()

    def handle(self, *args, **options):
        self.stdout.write("Memulai analisis kemiripan varian produk...")
        
        kandidat_produk = list(Product.active_objects.filter(master_product__isnull=True).exclude(retail_price=0))
        
        processed_ids = set()
        rencana_normalisasi = []
        threshold = 0.85 

        for i, p1 in enumerate(kandidat_produk):
            if p1.id in processed_ids:
                continue
                
            varian_ditemukan = []
            for p2 in kandidat_produk[i+1:]:
                if p2.id in processed_ids:
                    continue
                    
                if p1.is_addon != p2.is_addon:
                    continue

                skor = self.hitung_kemiripan_spesifik(p1.item_name, p2.item_name)
                if skor >= threshold:
                    varian_ditemukan.append(p2)
            
            if varian_ditemukan:
                nama_master = self.get_sequential_intersection(p1.item_name, varian_ditemukan[0].item_name)
                if not nama_master:
                    nama_master = p1.item_name
                
                semua_varian = [p1] + varian_ditemukan
                rencana_normalisasi.append({
                    'nama_master': nama_master,
                    'is_addon': p1.is_addon,
                    'daftar_anak': semua_varian
                })
                for var in semua_varian:
                    processed_ids.add(var.id)

        if not rencana_normalisasi:
            self.stdout.write(self.style.WARNING("Tidak ada varian produk yang memenuhi ambang batas kemiripan."))
            return

        # Tampilkan Preview Rencana Relasi (Induk -> Anak)
        self.stdout.write(self.style.WARNING(f"\n[!] SIMULASI NORMALISASI (Terdeteksi {len(rencana_normalisasi)} Kelompok Produk Master):"))
        self.stdout.write("-" * 75)
        for idx, rencana in enumerate(rencana_normalisasi, 1):
            tipe_addon = "[ADDON]" if rencana['is_addon'] else "[UTAMA]"
            self.stdout.write(self.style.SUCCESS(f"{idx}. 🌟 INDUK VIRTUAL {tipe_addon}: '{rencana['nama_master']}'"))
            for anak in rencana['daftar_anak']:
                self.stdout.write(f"   └── 👶 Anak Cabang: '{anak.item_name}' (Harga: {anak.retail_price})")
            self.stdout.write("-" * 75)

        self.stdout.write("\n")

        # Konfirmasi Interaktif Eksekusi
        if options.get('no_input'):
            konfirmasi = 'y'
        else:
            konfirmasi = input("Apakah simulasi pengelompokan produk di atas sudah benar? (y/n): ")
            
        if konfirmasi.strip().lower() != 'y':
            self.stdout.write(self.style.ERROR("\nProses dibatalkan oleh pengguna. Tidak ada data yang dimasukkan ke database."))
            return

        master_created_count = 0
        variant_linked_count = 0

        with transaction.atomic():
            self.stdout.write(f"\n[-] Memproses penyimpanan dan pembuatan relasi di database...")
            for rencana in rencana_normalisasi:
                master_prod, created = Product.active_objects.get_or_create(
                    item_name=rencana['nama_master'],
                    retail_price=0.0,
                    is_addon=rencana['is_addon'],
                    master_product=None
                )
                if created:
                    master_created_count += 1
                
                for var in rencana['daftar_anak']:
                    var.master_product = master_prod
                    var.save(update_fields=['master_product', 'updated_at'])
                    variant_linked_count += 1

        self.stdout.write(self.style.SUCCESS("="*50))
        self.stdout.write(self.style.SUCCESS(f"PROSES SINKRONISASI SELESAI!"))
        self.stdout.write(self.style.SUCCESS(f"Total Master Product baru dibuat : {master_created_count}"))
        self.stdout.write(self.style.SUCCESS(f"Total Varian Cabang terhubung    : {variant_linked_count}"))
        self.stdout.write(self.style.SUCCESS("="*50))