import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- FUNGSI BANTUAN GLOBAL ---
def mask_customer_name(name):
    if pd.isna(name):
        return name
    name = str(name).strip()
    if len(name) <= 2:
        return name
    return f"{name[0]}***{name[-1]}"
def clean_price( price_str):
    if pd.isna(price_str) or price_str == "":
        return 0.0
    if isinstance(price_str, str):
        price_str = price_str.replace('.', '').replace(',', '.')
    try:
        return float(price_str)
    except ValueError:
        return 0.0


class RawDataExplorer:
    """
    Service class untuk eksplorasi deskriptif pada data mentah.
    Mendukung data Numerik, Kategorikal, dan Datetime.
    """
    
    def __init__(self, df: pd.DataFrame, dataset_name: str = "Dataset"):
        self.df = df
        self.dataset_name = dataset_name
        sns.set_style("whitegrid")
        
    def get_head(self, n: int = 5) -> pd.DataFrame:
        print(f"=== Head of {self.dataset_name} ===")
        return self.df.head(n)

    def get_basic_info(self) -> pd.DataFrame:
        print(f"=== Basic Info: {self.dataset_name} ===")
        print(f"Total Baris: {self.df.shape[0]} | Total Kolom: {self.df.shape[1]}")
        print(f"Jumlah Duplikat (Baris): {self.df.duplicated().sum()}\n")
        
        return pd.DataFrame({
            'Tipe Data': self.df.dtypes,
            'Total Non-Null': self.df.notnull().sum(),
            'Total Null': self.df.isnull().sum(),
            'Persentase Null (%)': (self.df.isnull().sum() / len(self.df) * 100).round(2)
        })

    def get_categorical_summary(self, cols: list = None):
        if cols is None:
            # Ambil hanya object dan category, abaikan datetime
            cols = self.df.select_dtypes(include=['object', 'category']).columns

        print(f"=== Categorical Summary: {self.dataset_name} ===")
        for col in cols:
            print(f"\nKolom: {col} | Unique Values: {self.df[col].nunique()}")
            print(self.df[col].value_counts().head(10))
            print("-" * 30)

    # ---------------------------------------------------------
    # FUNGSI BANTUAN FILTER KOLOM
    # ---------------------------------------------------------
    def get_numeric_cols(self) -> list:
        """
        Mengambil kolom int/float secara otomatis.
        Mengabaikan kolom ID, No, dan Mobile, namun tetap menyertakan kolom 'Total Invoice'.
        """
        num_cols = self.df.select_dtypes(include=['number']).columns.tolist()
        
        # Kata kunci yang ingin dibuang (Blacklist)
        blacklist = ['id', 'invoice', 'no', 'mobile number','phone', 'contact', 'block reason', 'reason']
        
        # Kata kunci pengecualian yang harus tetap ada (Whitelist)
        whitelist = ['total invoice']
        
        return [
            c for c in num_cols 
            if not any(x in c.lower() for x in blacklist) 
            or any(x in c.lower() for x in whitelist)
        ]
        
    def get_datetime_cols(self) -> list:
        """Mengambil semua kolom berjenis datetime."""
        return self.df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()

    # ---------------------------------------------------------
    # ANALISIS NUMERIK
    # ---------------------------------------------------------
    def diagnose_outliers(self, cols: list, show_plot: bool = True) -> pd.DataFrame:
        report_data = []

        for col in cols:
            if col not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
                
            series = self.df[col].dropna()
            n = len(series)
            if n == 0: continue

            skew, kurt = series.skew(), series.kurtosis()
            p50, p99, p100 = series.median(), series.quantile(0.99), series.max()
            Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
            
            upper_fence = Q3 + (1.5 * (Q3 - Q1))
            outlier_pct_iqr = (series[series > upper_fence].count() / n) * 100
            gap_ratio = p100 / p99 if p99 != 0 else 0

            if gap_ratio > 2 or skew > 3:
                severity, rec = "EXTREME", "Praproses Lanjut Dibutuhkan"
            elif gap_ratio > 1.2 or skew > 1:
                severity, rec = "HIGH", "Saran Winsor (0.99)"
            else:
                severity, rec = "LOW", "Aman / Optional"

            report_data.append({
                'Fitur': col, 'Skewness': round(skew, 2), 'Kurtosis': round(kurt, 2),
                'Outlier_IQR (%)': f"{round(outlier_pct_iqr, 1)}%", 'Median (P50)': round(p50, 2),
                'P99': round(p99, 2), 'Max (P100)': round(p100, 2),
                'Gap Max/P99': round(gap_ratio, 2) if p99 != 0 else "Infinite",
                'Severity': severity, 'Rekomendasi': rec
            })

        df_report = pd.DataFrame(report_data)

        if show_plot and not df_report.empty:
            plt.figure(figsize=(15, 5))
            for i, col in enumerate(df_report['Fitur']):
                plt.subplot(1, len(df_report['Fitur']), i+1)
                sns.boxplot(y=self.df[col], color='skyblue')
                plt.title(f'{col}\nSkew: {self.df[col].skew():.2f}')
                plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()

        return df_report

    def plot_distributions(self, cols: list):
        valid_cols = [c for c in cols if c in self.df.columns and pd.api.types.is_numeric_dtype(self.df[c])]
        n_cols = len(valid_cols)
        if n_cols == 0: return

        fig, axes = plt.subplots(1, n_cols, figsize=(5 * n_cols, 5))
        if n_cols == 1: axes = [axes]

        for i, col in enumerate(valid_cols):
            sns.histplot(self.df[col].dropna(), kde=True, ax=axes[i], color='teal')
            axes[i].set_title(f'Distribusi Numerik {col}')
            axes[i].set_ylabel('Frekuensi')

        plt.tight_layout()
        plt.show()

    # ---------------------------------------------------------
    # ANALISIS DATETIME (BARU)
    # ---------------------------------------------------------
    def get_datetime_summary(self, cols: list = None):
        """Menampilkan informasi rentang waktu (Min, Max, Span)."""
        if cols is None:
            cols = self.get_datetime_cols()

        if not cols:
            return

        print(f"=== Datetime Summary: {self.dataset_name} ===")
        for col in cols:
            valid_data = self.df[col].dropna()
            if valid_data.empty: continue
            
            print(f"\nKolom: {col}")
            print(f"  Tgl Paling Awal (Min) : {valid_data.min()}")
            print(f"  Tgl Paling Akhir (Max): {valid_data.max()}")
            print(f"  Rentang Waktu         : {valid_data.max() - valid_data.min()}")
            print("-" * 40)

    def plot_datetime_distributions(self, cols: list):
        """Menampilkan histogram pergerakan data berdasarkan waktu."""
        valid_cols = [c for c in cols if c in self.df.columns and pd.api.types.is_datetime64_any_dtype(self.df[c])]
        n_cols = len(valid_cols)
        if n_cols == 0: return

        fig, axes = plt.subplots(1, n_cols, figsize=(6 * n_cols, 4))
        if n_cols == 1: axes = [axes]

        for i, col in enumerate(valid_cols):
            # Menggunakan bins otomatis untuk membagi waktu dengan rapi
            sns.histplot(self.df[col].dropna(), kde=False, ax=axes[i], color='coral', bins=30)
            axes[i].set_title(f'Sebaran Waktu: {col}')
            axes[i].set_ylabel('Frekuensi Transaksi')
            axes[i].tick_params(axis='x', rotation=45) # Miringkan teks tanggal agar tidak bertumpuk

        plt.tight_layout()
        plt.show()