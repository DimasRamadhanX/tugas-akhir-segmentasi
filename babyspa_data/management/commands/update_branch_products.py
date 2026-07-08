import re
from django.core.management.base import BaseCommand
from django.db import transaction
from babyspa_data.models import Product, Branch, TransactionItem

class Command(BaseCommand):
    help = 'Populasi M2M branches pada Product dengan Investigasi Silang Transaksi khusus Solo/Solo Baru.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help='Bypass interactive confirmation',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Menginisialisasi data master cabang..."))
        
        branches = Branch.objects.all()
        if not branches.exists():
            self.stdout.write(self.style.ERROR("Eror: Data Cabang tidak ditemukan!"))
            return

        # Mapping nama cabang untuk pencocokan instan
        branch_map = {}
        for b in branches:
            name_lower = b.branch_name.lower().strip()
            branch_map[name_lower] = b
            if 'surabaya' in name_lower or 'sby' in name_lower:
                branch_map['surabaya'] = b
                branch_map['sby'] = b
            if 'solo baru' in name_lower:
                branch_map['solo baru'] = b
            elif 'solo' in name_lower: # Dipastikan terpisah dengan Solo Baru
                branch_map['solo'] = b
            if 'yogyakarta' in name_lower or 'jogja' in name_lower:
                branch_map['jogja'] = b
            if 'gresik' in name_lower:
                branch_map['gresik'] = b

        db_products = Product.active_objects.all()
        proposed_tree = {}
        execution_map = {}

        self.stdout.write(f"[-] Menganalisis relasi untuk {db_products.count()} produk...")

        for product in db_products:
            item_name_lower = product.item_name.lower().strip()
            matched_branches = set()
            butuh_investigasi_solo = False

            # --- STRATEGI 1: CEK SUBSTRING NAMA CONTROLLER ---
            if 'solo baru' in item_name_lower:
                if 'solo baru' in branch_map:
                    matched_branches.add(branch_map['solo baru'])
                    butuh_investigasi_solo = True # Investigasi apakah juga dijual di Solo biasa
            elif 'solo' in item_name_lower:
                if 'solo' in branch_map:
                    matched_branches.add(branch_map['solo'])
                    butuh_investigasi_solo = True # Investigasi apakah juga dijual di Solo Baru

            elif 'jogja' in item_name_lower or 'yogyakarta' in item_name_lower:
                if 'jogja' in branch_map:
                    matched_branches.add(branch_map['jogja'])
            elif 'gresik' in item_name_lower:
                if 'gresik' in branch_map:
                    matched_branches.add(branch_map['gresik'])
            elif 'sby' in item_name_lower or 'surabaya' in item_name_lower:
                if 'surabaya' in branch_map:
                    matched_branches.add(branch_map['surabaya'])

            # --- MODUL INVESTIGASI SILANG TRANSAKSI (KHUSUS KASUS SOLO & SOLO BARU) ---
            if butuh_investigasi_solo:
                # Ambil histori cabang dari transaksi produk ini
                tx_solo_branch_ids = TransactionItem.active_objects.filter(
                    product_id=product.id
                ).values_list('transaction__branch_id', flat=True).distinct()

                for b_id in tx_solo_branch_ids:
                    b_obj = next((x for x in branches if x.id == b_id), None)
                    if b_obj:
                        b_name_lower = b_obj.branch_name.lower()
                        # Jika produk 'Solo' tapi pernah ditransaksikan di 'Solo Baru', atau sebaliknya, include!
                        if 'solo' in b_name_lower:
                            matched_branches.add(b_obj)

            # --- STRATEGI 2: FALLBACK UTUH (Untuk produk non-daerah seperti Masker Nebu) ---
            if not matched_branches:
                tx_branch_ids = TransactionItem.active_objects.filter(
                    product_id=product.id
                ).values_list('transaction__branch_id', flat=True).distinct()
                
                for b_id in tx_branch_ids:
                    b_obj = next((x for x in branches if x.id == b_id), None)
                    if b_obj:
                        matched_branches.add(b_obj)

            if matched_branches:
                execution_map[product] = matched_branches
                proposed_tree[product.item_name] = [b.branch_name for b in matched_branches]

        # ==============================================================================
        # 3. TREE VIEW CONFIRMATION SCREEN
        # ==============================================================================
        self.stdout.write("\n" + "="*80)
        self.stdout.write(" RANCANGAN TREE VIEW RELASI PRODUK -> CABANG (MANY-TO-MANY)")
        self.stdout.write("="*80)
        
        if not proposed_tree:
            self.stdout.write(self.style.WARNING("Tidak ada rancangan relasi baru yang dideteksi."))
            return

        for p_name, b_list in proposed_tree.items():
            self.stdout.write(f"🌲 {p_name}")
            for b_name in b_list:
                self.stdout.write(f"    └── 🏛️ {b_name}")
        
        self.stdout.write("="*80)
        
        if options.get('no_input'):
            confirm = 'y'
        else:
            confirm = input(f"\nApakah kamu setuju untuk mempopulasikan {len(execution_map)} data relasi di atas ke tabel pivot? (y/n): ")
        
        if confirm.lower().strip() != 'y':
            self.stdout.write(self.style.ERROR("🚨 Eksekusi dibatalkan oleh pengguna."))
            return

        # ==============================================================================
        # 4. EXECUTION ATOMIC MANY-TO-MANY PIVOT
        # ==============================================================================
        updated_count = 0
        with transaction.atomic():
            for product, branch_set in execution_map.items():
                for branch in branch_set:
                    if not product.branches.filter(id=branch.id).exists():
                        product.branches.add(branch)
                        updated_count += 1

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(" PROSES SINKRONISASI INVESTIGASI SELESAI!"))
        self.stdout.write(self.style.SUCCESS(f" Total baris relasi baru berhasil di-insert ke pivot: {updated_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))