import pandas as pd
from django.db import transaction
from babyspa_data.models.customers import Customer
from babyspa_data.models.cluster_lrfm import ClusterLRFM, LRFMReference
from babyspa_data.models.customer_segment import CustomerSegment
from babyspa_data.models.customer_score import CustomerScore 

class LRFMBuilder:
    def __init__(self, k_value):
        self.k_value = k_value

    def _cleanup_old_data(self):
        # Menggunakan active_objects untuk soft delete segmentasi lama khusus K target ini
        CustomerSegment.active_objects.filter(cluster_lrfm__k_value=self.k_value).delete()

    def _determine_symbol_from_boolean(self, row):
        l = "↑" if row.get('is_length_above_uni', True) else "↓"
        f = "↑" if row.get('is_frequency_above_uni', True) else "↓"
        m = "↑" if row.get('is_monetary_above_uni', True) else "↓"
        r = "↓" if row.get('is_recency_above_uni', False) else "↑"
        return f"{l}{r}{f}{m}"

    def save_clusters(self, centroid_df):
        cluster_col = 'cluster' if 'cluster' in centroid_df.columns else f'cluster_k_{self.k_value}'
        cluster_objects = {}
        
        with transaction.atomic():
            ClusterLRFM.active_objects.filter(k_value=self.k_value).delete()
            for _, row in centroid_df.iterrows():
                cluster_num = row.get(cluster_col)
                if cluster_num is None or pd.isna(cluster_num):
                    continue
                    
                c_id_raw = int(cluster_num)
                symbol = self._determine_symbol_from_boolean(row)
                
                ref_obj = LRFMReference.active_objects.filter(symbol=symbol).first()
                if not ref_obj:
                    ref_obj = LRFMReference.active_objects.first()

                cluster_obj = ClusterLRFM.active_objects.create(
                    cluster_id=str(c_id_raw),
                    k_value=self.k_value,
                    mean_length=row.get('real_length', 0.0),
                    mean_recency=row.get('real_recency', 0.0),
                    mean_frequency=row.get('real_frequency', 0.0),
                    mean_monetary=row.get('real_monetary', 0.0),
                    lrfm_reference=ref_obj
                )
                cluster_objects[c_id_raw] = cluster_obj
        return cluster_objects

    def save_customer_segments(self, df_lrfm_final, cluster_map):
        cluster_col = 'cluster' if 'cluster' in df_lrfm_final.columns else f'cluster_k_{self.k_value}'
        print(f"🔄 INFO: Memproses mapping menggunakan kolom DataFrame: '{cluster_col}'")

        # 1. Tarik semua ID customer aktif ke memori dalam bentuk set
        valid_customer_ids = set(
            Customer.active_objects.filter(
                id__in=df_lrfm_final['customer_id'].dropna().tolist()
            ).values_list('id', flat=True)
        )

        # ======================================================================
        # PENGAMAN DUPLIKASI: Deteksi siapa saja yang sudah punya skor di database
        # ======================================================================
        existing_score_customer_ids = set(
            CustomerScore.active_objects.filter(
                customer_id__in=list(valid_customer_ids)
            ).values_list('customer_id', flat=True)
        )

        segments_to_create = []
        scores_to_create = [] 
        
        # 2. Iterasi data murni di memori Python
        for _, row in df_lrfm_final.iterrows():
            c_id = row.get('customer_id')
            
            if c_id not in valid_customer_ids:
                continue
                
            cluster_num = row.get(cluster_col)
            if cluster_num is None or pd.isna(cluster_num):
                continue
                
            cluster_obj = cluster_map.get(int(cluster_num))
            
            if cluster_obj:
                raw_age = row.get('age')
                age_value = 0 if pd.isna(raw_age) or raw_age is None else int(raw_age)
                
                # Ekstraksi Variabel
                l_real_val = float(row.get('real_length', 0.0)) if not pd.isna(row.get('real_length')) else 0.0
                r_real_val = float(row.get('real_recency', 0.0)) if not pd.isna(row.get('real_recency')) else 0.0
                f_real_val = float(row.get('real_frequency', 0.0)) if not pd.isna(row.get('real_frequency')) else 0.0
                m_real_val = float(row.get('real_monetary', 0.0)) if not pd.isna(row.get('real_monetary')) else 0.0
                
                l_norm_val = float(row.get('length', 0.0)) if not pd.isna(row.get('length')) else 0.0
                r_norm_val = float(row.get('recency', 0.0)) if not pd.isna(row.get('recency')) else 0.0
                f_norm_val = float(row.get('frequency', 0.0)) if not pd.isna(row.get('frequency')) else 0.0
                m_norm_val = float(row.get('monetary', 0.0)) if not pd.isna(row.get('monetary')) else 0.0
                
                clv_val = float(row.get('CLV', 0.0)) if not pd.isna(row.get('CLV')) else 0.0
                is_churn_val = bool(row.get('is_churn', False))

                # --- SIMPAN KE CUSTOMER SEGMENT (Selalu dibuat per skenario K) ---
                segments_to_create.append(
                    CustomerSegment(
                        customer_id=c_id,
                        cluster_lrfm=cluster_obj,
                        clv_score=clv_val,
                        is_churn=is_churn_val,
                        age=age_value
                    )
                )
                
                # --- SIMPAN KE CUSTOMER SCORE (Hanya dibuat jika belum ada di database) ---
                if c_id not in existing_score_customer_ids:
                    scores_to_create.append(
                        CustomerScore(
                            customer_id=c_id,
                            l_real=l_real_val,
                            r_real=r_real_val,
                            f_real=f_real_val,
                            m_real=m_real_val,
                            l_normalized=l_norm_val,
                            r_normalized=r_norm_val,
                            f_normalized=f_norm_val,
                            m_normalized=m_norm_val,
                            age=age_value
                        )
                    )
                    # Masukkan ke set pencatat agar tidak menduplikasi jika ada ID ganda di DataFrame
                    existing_score_customer_ids.add(c_id)

        # 3. Jalankan transaksi massal ke database
        if segments_to_create:
            with transaction.atomic():
                self._cleanup_old_data()
                
                # Bulk create untuk segmentasi
                CustomerSegment.bulk_create_base(segments_to_create)
                
                # Bulk create untuk skor (Hanya memasukkan data baru yang belum ada)
                if scores_to_create:
                    if hasattr(CustomerScore, 'bulk_create_base'):
                        CustomerScore.bulk_create_base(scores_to_create)
                    else:
                        CustomerScore.objects.bulk_create(scores_to_create)
                    
            print(f"🚀 Bulk Insert Sukses: {len(segments_to_create)} segmen berhasil disimpan. {len(scores_to_create)} data skor baru ditambahkan.")
        else:
            print("❌ Gagal: Tidak ada objek segmen yang lolos kualifikasi sinkronisasi.")