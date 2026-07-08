import pandas as pd
import numpy as np
from django.db import transaction
from babyspa_data.models.product import Product, ProductScore
from babyspa_data.models.ahp_configuration import AHPConfiguration

class TopNProductSAW:
    def __init__(self, config_name="Analisis Skripsi Baby Spa 2026 - Product", top_n=10):
        self.config_name = config_name
        self.top_n = top_n
        self.config = self._get_config()
        self.weights = self._set_weights()

    def _get_config(self):
        try:
            return AHPConfiguration.active_objects.get(name=self.config_name, context='PRODUCT')
        except AHPConfiguration.DoesNotExist:
            raise ValueError(f"Config '{self.config_name}' tidak ditemukan.")

    def _set_weights(self):
        return {
            'r': self.config.w_recency,
            'f': self.config.w_frequency,
            'm': self.config.w_monetary
        }

    def _min_max_normalization(self, series, is_benefit=True):
        if series.empty or series.max() == series.min(): return 0.0
        if is_benefit:
            return (series - series.min()) / (series.max() - series.min())
        else:
            return (series.max() - series) / (series.max() - series.min())

    def run_calculation(self, df_rfm_p):
        df = df_rfm_p.copy()
        if 'product_id' not in df.columns:
            df = df.reset_index().rename(columns={df.index.name if df.index.name else 'index': 'product_id'})

        df['r_norm'] = self._min_max_normalization(df['recency'], is_benefit=False)
        df['f_norm'] = self._min_max_normalization(df['frequency'], is_benefit=True)
        df['m_norm'] = self._min_max_normalization(df['monetary'], is_benefit=True)

        df['total_score'] = (df['r_norm'] * self.weights['r']) + \
                           (df['f_norm'] * self.weights['f']) + \
                           (df['m_norm'] * self.weights['m'])

        df = df.sort_values(by='total_score', ascending=False).reset_index(drop=True)
        df['rank'] = df.index + 1
        df['is_top_n'] = df['rank'] <= self.top_n
        return df

    def sync_to_db(self, df_scored, cluster_obj=None, product_mapping=None):
        """
        cluster_obj: Instance dari ClusterLRFM atau None untuk Global.
        product_mapping: Dictionary {variant_id: master_id} untuk duplikasi skor kedaerah.
        """
        df_valid = df_scored.dropna(subset=['product_id'])
        count_synced = 0
        
        # Jaga-jaga jika mapping tidak dimasukkan, set ke dictionary kosong
        if product_mapping is None:
            product_mapping = {}
            
        with transaction.atomic():
            # Soft delete skor lama untuk kombinasi config & cluster ini
            ProductScore.active_objects.filter(ahp_config=self.config, cluster_id=cluster_obj).delete()

            for _, row in df_valid.iterrows():
                try:
                    p_id = row['product_id']
                    if p_id is None or pd.isna(p_id): continue
                    
                    # ==========================================
                    # 1. SIMPAN SKOR UNTUK ID MASTER
                    # ==========================================
                    product_instance = Product.active_objects.get(id=p_id)
                    
                    score_obj, _ = ProductScore.active_objects.update_or_create(
                        product=product_instance,
                        ahp_config=self.config,
                        cluster_id=cluster_obj, 
                        defaults={
                            'name': row.get('item_name', None), # Memasukkan nama produk yang sudah di-condensed
                            'r_normalized': row['r_norm'],
                            'f_normalized': row['f_norm'],
                            'm_normalized': row['m_norm'],
                            'total_saw_score': row['total_score'],
                            'rank': row['rank'],
                            'is_top_n': row['is_top_n'],
                            'deleted_at': None
                        }
                    )
                    # Relasi 2 Arah: Update skor ke master produk
                    product_instance.score = score_obj
                    product_instance.save()
                    count_synced += 1
                    
                    # ==========================================
                    # 2. GANDAKAN SKOR UNTUK ID VARIAN DAERAH
                    # ==========================================
                    for variant_id, master_id in product_mapping.items():
                        if master_id == p_id:
                            try:
                                variant_instance = Product.active_objects.get(id=variant_id)
                                
                                var_score_obj, _ = ProductScore.active_objects.update_or_create(
                                    product=variant_instance,
                                    ahp_config=self.config,
                                    cluster_id=cluster_obj,
                                    defaults={
                                        'name': row.get('item_name', None),
                                        'r_normalized': row['r_norm'],
                                        'f_normalized': row['f_norm'],
                                        'm_normalized': row['m_norm'],
                                        'total_saw_score': row['total_score'],
                                        'rank': row['rank'],
                                        'is_top_n': row['is_top_n'],
                                        'deleted_at': None
                                    }
                                )
                                # Relasi 2 Arah: Update skor ke varian produk
                                variant_instance.score = var_score_obj
                                variant_instance.save()
                                count_synced += 1
                            except Product.DoesNotExist:
                                continue

                except (Product.DoesNotExist, ValueError, TypeError):
                    continue
        
        return count_synced