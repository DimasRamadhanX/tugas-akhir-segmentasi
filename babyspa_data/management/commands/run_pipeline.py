from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Pipeline untuk memperbarui/normalisasi data tanpa melakukan truncate (penghapusan data)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== Running pipeline update commands... ==="))

        # Mendefinisikan daftar perintah beserta argumen tambahannya (kwargs)
        pipeline_commands = [
            ('update_gender_db', {}),
            ('update_product_categories', {}),
            ('update_product_description', {}),
            ('update_duration_on_items', {'no_input': True}),
            ('update_product_normalization_variant', {'no_input': True}),
            ('update_branch_products', {'no_input': True}),
            ('update_trx_item_db', {}),
            ('update_schedule_db', {}),
        ]

        for cmd_name, cmd_kwargs in pipeline_commands:
            self.stdout.write(f"Mengeksekusi: {cmd_name}...")
            try:
                # Unpacking dictionary (**cmd_kwargs) ke dalam argumen fungsi
                call_command(cmd_name, **cmd_kwargs)
            except Exception as e:
                # Menghentikan pipeline dan memberikan pesan error yang jelas jika ada kegagalan
                raise CommandError(f"Pipeline berhenti! Gagal saat menjalankan '{cmd_name}'. Error: {e}")

        self.stdout.write(self.style.SUCCESS("=== PIPELINE PEMBARUAN SELESAI TANPA TRUNCATE ==="))