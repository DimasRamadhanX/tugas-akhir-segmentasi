import pandas as pd
from sklearn.preprocessing import MinMaxScaler

class CLVBuilder:
    def __init__(self, ahp_weights):
        """
        Inisialisasi CLVBuilder dengan bobot AHP.
        :param ahp_weights: Dictionary bobot, contoh: {'w_length': 0.15, ...}
        """
        self.ahp_weights = ahp_weights
        self.minmax_scaler = MinMaxScaler()
        
    def calculate_clv(self, df_scaled):
        """
        Melakukan Min-Max Scaling pada dataframe input untuk menanggulangi nilai minus,
        lalu menghitung skor CLV dengan metode Simple Additive Weighting (SAW).
        """
        df_result = df_scaled.copy()
        
        # Kolom yang akan diproses
        cols = ['length', 'recency', 'frequency', 'monetary']
        
        # 1. Terapkan Min-Max Scaler sekaligus ke 4 kolom
        # Ini menggantikan penulisan satu-satu (length_normalized, recency_normalized, dst)
        df_result[['length_norm', 'recency_norm', 'frequency_norm', 'monetary_norm']] = \
            self.minmax_scaler.fit_transform(df_result[cols])
        
        # 2. Perhitungan CLV dengan bobot AHP
        df_result['CLV'] = (
            (df_result['recency_norm'] * self.ahp_weights['w_recency']) +
            (df_result['frequency_norm'] * self.ahp_weights['w_frequency']) +
            (df_result['monetary_norm'] * self.ahp_weights['w_monetary']) +
            (df_result['length_norm'] * self.ahp_weights['w_length'])
        )
        
        # Opsional: Hapus kolom _norm jika Anda hanya ingin menyimpan nilai CLV akhir
        df_result.drop(columns=['length_norm', 'recency_norm', 'frequency_norm', 'monetary_norm'], inplace=True)
        
        return df_result