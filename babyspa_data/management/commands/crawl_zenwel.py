import os
import time
import requests
import pandas as pd
from io import StringIO
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Crawling data Customer, Transaction Header, dan Items dari API Zenwel'

    def handle(self, *args, **options):
        # --- KONFIGURASI UTAMA ---
        self.HEADERS = {
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImY0YmQwZDBhYjYyZDYzZWZlZTU0ODZhNmFjNWU3NWI4MWEyZjhiNDBkY2QzOWQxM2U2YmMwZjljMGVkNmJhMjVhOTc1ZjA5NTA4MzNhNmJlIn0.eyJhdWQiOiIyIiwianRpIjoiZjRiZDBkMGFiNjJkNjNlZmVlNTQ4NmE2YWM1ZTc1YjgxYTJmOGI0MGRjZDM5ZDEzZTZiYzBmOWMwZWQ2YmEyNWE5NzVmMDk1MDgzM2E2YmUiLCJpYXQiOjE3NzIxOTU3NTEsIm5iZiI6MTc3MjE5NTc1MSwiZXhwIjoyMDg3NzI4NTUxLCJzdWIiOiIxMzMwNSIsInNjb3BlcyI6W10sIm5lZWRfY2hvb3NlX2xvY2F0aW9uIjpudWxsLCJsb2dpbl9wZXJzb25uZWwiOm51bGx9.w_bii-S4F3CxY0CGqlpJah9RaYwH0Mqy8FJKwWLoaspBUnMj0Dj47TRZ7C-STmUhFGQ37tMJonLM9KWkCU6WugaMWXHbvGl5reDtlRNb6j6iF_jn0HAWNVwuIwoM1XIvQZz7Ry03qEghLIdGGnRy0bnq5FgyLqRVtXtNUv7Nrmd84W448IKsOjPWtzQKTtooanS8vNYmj0w73M73t4T_djiV5sh3ZDOB-M9bGkrIbIiCYV8IabUTlhBtREtzHISGBeJ0tb3uIk2wIlj31XUWG5Ds_vHU2hmlj7eFhiog0wc7MBlB1fRS8Z2jDqaCJzgnOVci6oeLmTP7RHnw09qHT7lwElsfDY63tmB8308vWVUG9f6E7pmDkrvbIziqNQacSbjvGamckCDAlODbXRpG1QgKP_QQl8sw3YhlEX95gCP_pxaLVqYizwK0sCFOsLo06uqAh_M4QIa4xtCKYpQLrUeGQ5dr_X5pJyP4yVu9lsxoCfGFVf1fsTtNAnTxpOX3Db6L9XMdAVChZ2IKmM5u9uWMvZBWWOk4Sfp34MF_4RlbDcCmviA1dWqviU3ehWHFAbdWXf_HOIWHQY9_gOGt66KQ-mm-PwowcXlt24gdwU_wPJz0qzTSZNGgeqf6ufO-ZseWfdQouYJxfYXl67XnSG-1N-XIPZyCqRw62hjtcUo",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        self.LOCATIONS = {
            4807: "Solo_Manahan",
            4883: "Jogja_Maguwo",
            12482: "Jogja_Bausasran",
            12483: "Solo_Baru",
            13158: "Gresik"
        }
        
        self.RAW_DIR = os.path.join("data", "raw")
        os.makedirs(self.RAW_DIR, exist_ok=True)

        self.stdout.write(self.style.SUCCESS("Memulai proses crawling Zenwel..."))
        
        # Eksekusi fungsi fetch secara berurutan
        self.items_fetch()
        self.customers_fetch()
        self.transaction_header_fetch() # <--- BARU: Ambil Invoice Header
        self.transaction_item_fetch()   # <--- UBAH NAMA: Ambil Invoice Items
        
        self.stdout.write(self.style.SUCCESS("Seluruh proses crawling selesai!"))

    def items_fetch(self):
        self.stdout.write(self.style.WARNING("\n--- Mengambil Data Master Item/Service ---"))
        base_url = "https://api-dash.zenwel.com/api/admin/v1/id/service/export"
        params = {'type': 'csv'}
        
        try:
            res = requests.get(base_url, headers=self.HEADERS, params=params)
            if res.status_code == 200:
                df = pd.read_csv(StringIO(res.text))
                save_path = os.path.join(self.RAW_DIR, "master_items.csv")
                df.to_csv(save_path, index=False)
                self.stdout.write(self.style.SUCCESS(f"  -> Master Item sukses ditarik ({len(df)} baris)"))
            else:
                self.stdout.write(self.style.ERROR(f"  -> Gagal tarik item: Status {res.status_code}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  -> Error Item Fetch: {str(e)}"))
        
        time.sleep(1.5)

    def customers_fetch(self):
        self.stdout.write(self.style.WARNING("\n--- Mengambil Data Master Customer ---"))
        base_url = "https://api-dash.zenwel.com/api/admin/v1/id/customer/export"
        all_customers = []

        for p_val in range(1, 6):
            params = {
                'page': 1, 'per_page': 5000, 'sort_column': 'id', 
                'sort_type': 'desc', 'show_minors': 0, 'show_waiver': 0,
                'type': 'csv', 'p': p_val
            }
            try:
                res = requests.get(base_url, headers=self.HEADERS, params=params)
                if res.status_code == 200:
                    df = pd.read_csv(StringIO(res.text))
                    all_customers.append(df)
                    self.stdout.write(f"  -> Customer Batch p={p_val} sukses ({len(df)} baris)")
                else:
                    self.stdout.write(self.style.ERROR(f"  -> Gagal p={p_val}: Status {res.status_code}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Error p={p_val}: {str(e)}"))
            time.sleep(1.5)

        if all_customers:
            master_df = pd.concat(all_customers, ignore_index=True)
            master_df.drop_duplicates(subset=['ID'], inplace=True)
            master_df.to_csv(os.path.join(self.RAW_DIR, "master_customers.csv"), index=False)

    def transaction_header_fetch(self):
        self.stdout.write(self.style.WARNING("\n--- Mengambil Data Transaction Header (Invoice) ---"))
        # Endpoint baru yang Anda temukan
        base_url = "https://api-dash.zenwel.com/api/admin/v1/id/sales/export"
        all_headers = []

        for loc_id, loc_name in self.LOCATIONS.items():
            for year in range(2021, 2027):
                params = {
                    'start_date': f'{year}-01-01', 'end_date': f'{year}-12-31',
                    'location_id': loc_id, 'type': 'csv', 'per_page': 10000
                }
                try:
                    res = requests.get(base_url, headers=self.HEADERS, params=params)
                    if res.status_code == 200:
                        df = pd.read_csv(StringIO(res.text))
                        df['Branch_ID'] = loc_id
                        df['Branch_Name'] = loc_name
                        all_headers.append(df)
                        self.stdout.write(f"  -> Invoice Header {loc_name} ({year}) sukses ({len(df)} baris)")
                    else:
                        self.stdout.write(self.style.ERROR(f"  -> Gagal {loc_name} ({year}): Status {res.status_code}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  -> Error {loc_name} ({year}): {str(e)}"))
                time.sleep(1.5)

        if all_headers:
            master_header_df = pd.concat(all_headers, ignore_index=True)
            # Akan otomatis overwrite CSV jika sudah ada
            master_header_df.to_csv(os.path.join(self.RAW_DIR, "master_transaction_headers.csv"), index=False)

    def transaction_item_fetch(self):
        self.stdout.write(self.style.WARNING("\n--- Mengambil Data Transaction Items (Appointment) ---"))
        base_url = "https://api-dash.zenwel.com/api/admin/v1/id/sales/appointment/export"
        all_items = []

        for loc_id, loc_name in self.LOCATIONS.items():
            for year in range(2021, 2027):
                params = {
                    'start_date': f'{year}-01-01', 'end_date': f'{year}-12-31',
                    'location_id': loc_id, 'type': 'csv', 'per_page': 10000
                }
                try:
                    res = requests.get(base_url, headers=self.HEADERS, params=params)
                    if res.status_code == 200:
                        df = pd.read_csv(StringIO(res.text))
                        df['Branch_ID'] = loc_id
                        df['Branch_Name'] = loc_name
                        all_items.append(df)
                        self.stdout.write(f"  -> Transaction Items {loc_name} ({year}) sukses ({len(df)} baris)")
                    else:
                        self.stdout.write(self.style.ERROR(f"  -> Gagal {loc_name} ({year}): Status {res.status_code}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  -> Error {loc_name} ({year}): {str(e)}"))
                time.sleep(1.5)

        if all_items:
            master_items_df = pd.concat(all_items, ignore_index=True)
            # Akan otomatis overwrite CSV jika sudah ada
            master_items_df.to_csv(os.path.join(self.RAW_DIR, "master_transaction_items.csv"), index=False)