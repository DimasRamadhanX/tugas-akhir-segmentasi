import pandas as pd
import numpy as np
from sklearn.preprocessing import PowerTransformer, StandardScaler, MinMaxScaler

class Preprocess:
    def __init__(self):
        """
        Inisialisasi transformer untuk Yeo-Johnson dan Z-Scale.
        """
        self.yeo_johnson_scaler = PowerTransformer(method='yeo-johnson', standardize=False)
        self.z_scaler = StandardScaler()

    def _get_target_cols(self, df, columns):
        """
        Helper untuk menentukan kolom target: menggunakan list manual 
        atau deteksi otomatis kolom numerik.
        """
        if columns is not None:
            # Memastikan kolom yang diminta memang ada di DataFrame
            return [c for c in columns if c in df.columns]
        return df.select_dtypes(include=[np.number]).columns.tolist()

    def transform_yeo_johnson(self, df, columns=None):
        """
        Melakukan transformasi Yeo-Johnson untuk menangani skewness data.
        Input: DataFrame & List Kolom (Optional) | Output: DataFrame
        """
        df_transformed = df.copy()
        target_cols = self._get_target_cols(df_transformed, columns)
        
        if target_cols:
            # Fit dan Transform pada kolom yang ditargetkan[cite: 1]
            data_transformed = self.yeo_johnson_scaler.fit_transform(df_transformed[target_cols])
            df_transformed[target_cols] = data_transformed
            
        return df_transformed

    def transform_z_scale(self, df, columns=None):
        """
        Melakukan transformasi Z-Scale (Standardization) agar mean=0 dan std=1.[cite: 1]
        Input: DataFrame & List Kolom (Optional) | Output: DataFrame
        """
        df_transformed = df.copy()
        target_cols = self._get_target_cols(df_transformed, columns)
        
        if target_cols:
            # Fit dan Transform pada kolom yang ditargetkan[cite: 1]
            data_scaled = self.z_scaler.fit_transform(df_transformed[target_cols])
            df_transformed[target_cols] = data_scaled
            
        return df_transformed
    
    def min_max_scale(self, df, columns=None):
        """
        Melakukan transformasi Min-Max Scaling untuk mengubah skala data ke rentang [0, 1].
        Input: DataFrame & List Kolom (Optional) | Output: DataFrame
        """
        df_transformed = df.copy()
        target_cols = self._get_target_cols(df_transformed, columns)
        
        if target_cols:
            # Fit dan Transform pada kolom yang ditargetkan
            scaler = MinMaxScaler(0,1)
            data_scaled = scaler.fit_transform(df_transformed[target_cols])
            df_transformed[target_cols] = data_scaled
            
            return df_transformed