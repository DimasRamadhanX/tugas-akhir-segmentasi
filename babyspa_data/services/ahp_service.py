import hashlib
import os
import re
import numpy as np
import pandas as pd
from scipy.stats import gmean
from django.conf import settings
from babyspa_data.models import AHPConfiguration

class AHPService:
    # Tabel Random Index (RI) Saaty
    RI_TABLE = {
        1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 
        6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49
    }

    def __init__(self, batch_name="Default Batch"):
        self.batch_name = batch_name
        self.default_csv_path = os.path.join(settings.BASE_DIR, 'data', 'raw', 'AHP_2.csv')

    def _anonymize_data(self, df):
        """Menyamarkan data sensitif menggunakan hashing SHA-256."""
        def mask_string(val):
            if pd.isna(val) or str(val).strip() == "": 
                return "Anonymous"
            return hashlib.sha256(str(val).encode()).hexdigest()[:8].upper()
        
        sensitive_cols = ['Nama pengguna', 'Inisial Nama', 'Email']
        for col in sensitive_cols:
            if col in df.columns:
                df[col] = df[col].apply(mask_string)
        return df

    def _scale_converter(self, val):
        """
        Konversi Likert ke skala perbandingan.
        Skala 1-5 digunakan untuk menjaga konsistensi (transitivitas) jawaban pakar.
        """
        label_to_saaty = {
            'Sangat Setuju': 5.0, 
            'Setuju': 4.0, 
            'Cukup Setuju': 3.0, 
            'Agak Setuju': 2.0,
            'Netral': 1.0, 
            'Agak Tidak Setuju': 1/2, 
            'Cukup Tidak Setuju': 1/3,
            'Tidak Setuju': 1/4, 
            'Sangat Tidak Setuju': 1/5
        }
        
        if isinstance(val, str):
            val = val.strip()
            if val in label_to_saaty:
                return label_to_saaty[val]
                
        try:
            val = float(val)
            return val if val >= 1 else 1.0
        except (ValueError, TypeError):
            return 1.0

    def calculate_full_metrics(self, all_responses, criteria_names):
        """
        Melakukan perhitungan AHP.
        Jika ada banyak responden, otomatis digabung menggunakan Geometric Mean.
        """
        n = len(criteria_names)
        if not all_responses:
            return None
            
        # 1. Konversi teks/angka menjadi nilai skala matriks
        cleaned_data = [[self._scale_converter(v) for v in resp] for resp in all_responses]
        
        # 2. Agregasi multi-responden dengan Geometric Mean
        geom_mean_vals = gmean(cleaned_data, axis=0)
        
        # 3. Bentuk Matriks Perbandingan Berpasangan (Pairwise Comparison Matrix)
        matrix = np.ones((n, n))
        idx = 0
        for i in range(n):
            for j in range(i + 1, n):
                val = geom_mean_vals[idx]
                matrix[i, j] = val
                matrix[j, i] = 1 / val
                idx += 1
                
        # 4. Normalisasi kolom dan hitung Bobot Prioritas (Eigenvector)
        col_sums = matrix.sum(axis=0)
        norm_matrix = matrix / col_sums
        weights = norm_matrix.mean(axis=1)
        
        # 5. Uji Konsistensi (Consistency Ratio / CR)
        weighted_sum_vector = np.dot(matrix, weights)
        lambda_max = np.mean(weighted_sum_vector / weights)
        
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        ri = self.RI_TABLE.get(n, 1.49)
        cr = ci / ri if ri > 0 else 0
        
        return {
            'matrix': matrix.tolist(),
            'weights': dict(zip(criteria_names, [round(w, 4) for w in weights.tolist()])),
            'cr': round(cr, 4),
            'is_consistent': cr < 0.2,
            'n_respondents': len(all_responses)
        }

    def _clean_text_for_mapping(self, text):
        """Membersihkan spasi ganda, whitespace berlebih, dan karakter \xa0."""
        if not isinstance(text, str):
            return text
        text = text.replace('\xa0', ' ').strip()
        return re.sub(r'\s+', ' ', text)

    def run(self, custom_path=None):
        """Fungsi utama untuk membaca CSV, memproses data, dan menyimpan ke Database."""
        path = custom_path or self.default_csv_path
        if not os.path.exists(path):
            return {"error": f"File {path} tidak ditemukan"}
            
        df = pd.read_csv(path)
        
        # Hapus baris yang kosong semua (misal ada sisa format di ujung file CSV)
        df = df.dropna(how='all')
        df = self._anonymize_data(df)
        
        # Bersihkan header kolom CSV
        df.columns = [self._clean_text_for_mapping(col) for col in df.columns]
        
        # Kamus Mapping Pertanyaan Form -> Variabel Singkat
        raw_mapping = {
            'Seberapa setuju Anda bahwa Lama Hubungan (L) pelanggan lebih penting daripada Kunjungan Terakhir (R)?': 'L_R',
            'Seberapa setuju Anda bahwa Lama Hubungan (L) pelanggan lebih penting daripada Frekuensi Kedatangan (F)?': 'L_F',
            'Seberapa setuju Anda bahwa Lama Hubungan (L) pelanggan lebih penting daripada Total Uang yang Dihabiskan (M)?': 'L_M',
            'Seberapa setuju Anda bahwa Kunjungan Terakhir (R) lebih menandakan pelanggan aktif daripada Total Kunjungan (F)?': 'R_F',
            'Seberapa setuju Anda bahwa Kunjungan Terakhir (R) lebih penting diprioritaskan daripada Nilai Transaksi Besar (M)?': 'R_M',
            'Seberapa setuju Anda bahwa Frekuensi Kedatangan (F) lebih berharga daripada Besarnya Nominal Sekali Transaksi (M)?': 'F_M',
            'Seberapa setuju Anda bahwa jasa yang Baru Saja Laku (R) lebih sukses dibanding jasa yang Sering Diulang (F)?': 'P_R_F',
            'Seberapa setuju Anda bahwa jasa yang Sedang Tren (R) lebih penting dipromosikan dibanding jasa Penyumbang Omzet (M)?': 'P_R_M',
            # Versi Lama
            'Seberapa setuju Anda bahwa jasa Murah tapi Laku Keras (F) lebih berharga dibanding jasa Mahal tapi Jarang Laku (M)?': 'P_F_M',
            # Versi Baru
            'Seberapa setuju Anda bahwa Jasa Berulang (F) lebih berharga dibanding jasa Mahal tapi Jarang Laku (M)?': 'P_F_M',
        }
        
        # Bersihkan kunci kamus dan terapkan rename kolom
        cleaned_mapping = {self._clean_text_for_mapping(k): v for k, v in raw_mapping.items()}
        df = df.rename(columns=cleaned_mapping)
        
        results = {}
        summary_data = []

        # --- PROSES LRFM ---
        lrfm_cols = ['L_R', 'L_F', 'L_M', 'R_F', 'R_M', 'F_M']
        if all(col in df.columns for col in lrfm_cols):
            metrics = self.calculate_full_metrics(df[lrfm_cols].values.tolist(), ['L', 'R', 'F', 'M'])
            results['lrfm'] = metrics
            if metrics:
                w = metrics['weights']
                summary_data.append({
                    'Kategori': 'LRFM',
                    'Bobot L': w.get('L', '-'), 'Bobot R': w.get('R', '-'),
                    'Bobot F': w.get('F', '-'), 'Bobot M': w.get('M', '-'),
                    'CR': metrics['cr'], 'Konsisten': metrics['is_consistent'],
                    'Responden': metrics['n_respondents']
                })
                # Simpan ke Database hanya jika konsisten (CR < 0.1)
                if metrics['is_consistent']:
                    AHPConfiguration.active_objects.update_or_create(
                        context='LRFM', name=f"{self.batch_name} - LRFM",
                        defaults={'w_length': w['L'], 'w_recency': w['R'], 'w_frequency': w['F'], 'w_monetary': w['M']}
                    )
        else:
            missing = [c for c in lrfm_cols if c not in df.columns]
            results['debug_lrfm'] = f"Gagal deteksi LRFM. Hilang: {missing}"
        
        # --- PROSES RFM/PRODUK ---
        rfm_p_cols = ['P_R_F', 'P_R_M', 'P_F_M']
        if all(col in df.columns for col in rfm_p_cols):
            metrics = self.calculate_full_metrics(df[rfm_p_cols].values.tolist(), ['R', 'F', 'M'])
            results['rfm_p'] = metrics
            if metrics:
                w = metrics['weights']
                summary_data.append({
                    'Kategori': 'Produk (RFM/P)',
                    'Bobot L': '-', 'Bobot R': w.get('R', '-'),
                    'Bobot F': w.get('F', '-'), 'Bobot M': w.get('M', '-'),
                    'CR': metrics['cr'], 'Konsisten': metrics['is_consistent'],
                    'Responden': metrics['n_respondents']
                })
                if metrics['is_consistent']:
                    AHPConfiguration.active_objects.update_or_create(
                        context='PRODUCT', name=f"{self.batch_name} - Product",
                        defaults={'w_length': 0, 'w_recency': w['R'], 'w_frequency': w['F'], 'w_monetary': w['M']}
                    )
        else:
            missing = [c for c in rfm_p_cols if c not in df.columns]
            results['debug_rfmp'] = f"Gagal deteksi Produk. Hilang: {missing}"

        # Kompilasi hasil untuk preview
        if summary_data:
            results['summary_df'] = pd.DataFrame(summary_data)

        results['detected_columns'] = list(df.columns)
        return results

    def print_preview(self, custom_path=None):
        """Mencetak ringkasan hasil AHP ke terminal."""
        hasil = self.run(custom_path)
        
        if 'error' in hasil:
            print(f"🚨 ERROR: {hasil['error']}")
            return hasil

        if 'summary_df' in hasil:
            print(f"\n=== PREVIEW HASIL AHP: {self.batch_name} ===")
            print(hasil['summary_df'].to_string(index=False))
            print("=========================================\n")
        
        if 'debug_lrfm' in hasil: 
            print(f"⚠️ {hasil['debug_lrfm']}")
        if 'debug_rfmp' in hasil: 
            print(f"⚠️ {hasil['debug_rfmp']}")
        
        return hasil