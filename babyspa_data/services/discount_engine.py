import pandas as pd
from babyspa_data.models import CustomerSegment, ClusterLRFM

class DiscountEngine:
    def __init__(self, k_value=3):
        self.k_value = k_value

    def calculate_individual_discount(self, customer_id):
        """
        Menghitung diskon adaptif untuk satu customer berdasarkan posisinya di klaster.
        Rumus: Disc_min + ((CLV - CLV_min) / (CLV_max - CLV_min)) * (Disc_max - Disc_min)
        """
        # 1. Ambil data segmen customer
        segment = CustomerSegment.active_objects.filter(
            customer_id=customer_id,
            cluster_lrfm__k_value=self.k_value
        ).select_related('cluster_lrfm').first()

        if not segment or not segment.cluster_lrfm:
            return 0.0

        cluster = segment.cluster_lrfm
        
        # 2. Ambil boundary CLV di dalam klaster yang sama
        all_clv_in_cluster = CustomerSegment.active_objects.filter(
            cluster_lrfm=cluster
        ).values_list('clv_score', flat=True)

        if not all_clv_in_cluster:
            return cluster.min_discount_percent

        clv_min = min(all_clv_in_cluster)
        clv_max = max(all_clv_in_cluster)
        clv_user = segment.clv_score

        # 3. Hitung posisi relatif (0 sampai 1)
        # Jika semua CLV sama, berikan nilai tengah atau minimum
        if clv_max == clv_min:
            relative_position = 0.5 
        else:
            relative_position = (clv_user - clv_min) / (clv_max - clv_min)

        # 4. Interpolasi ke rentang diskon klaster
        disc_min = cluster.min_discount_percent
        disc_max = cluster.max_discount_percent
        
        calculated_discount = disc_min + (relative_position * (disc_max - disc_min))
        
        return round(calculated_discount, 2)

    def calculating_disc_notebook(self, df_lrfm_final):
        cluster_col = f'cluster_k_{self.k_value}'
        
        # 1. Ambil config dari DB
        clusters = ClusterLRFM.active_objects.filter(k_value=self.k_value)
        cluster_config = {c.cluster_id: c for c in clusters}

        default_config = {
            0: {'min': 0, 'max': 5},
            1: {'min': 15, 'max': 25},
            2: {'min': 10, 'max': 20}
        }

        # 2. OPTIMASI UTAMA: Hitung batas boundary CLV per klaster sekali jalan
        cluster_bounds = df_lrfm_final.groupby(cluster_col)['CLV'].agg(['min', 'max']).to_dict('index')

        # 3. Bangun list dict dengan mapping cepat untuk menghindari slicing inside loop
        results = []
        for _, row in df_lrfm_final.iterrows():
            c_id = int(row[cluster_col])
            clv_user = row['CLV']
            
            # Ambil batas CLV dari dictionary hasil groupby (O(1) lookup)
            bounds = cluster_bounds.get(c_id, {'min': clv_user, 'max': clv_user})
            c_min_clv = bounds['min']
            c_max_clv = bounds['max']
            
            # Ambil nilai konfigurasi diskon
            conf = cluster_config.get(c_id)
            if conf:
                d_min = conf.min_discount_percent
                d_max = conf.max_discount_percent
            else:
                cfg = default_config.get(c_id, {'min': 0, 'max': 0})
                d_min = cfg['min']
                d_max = cfg['max']
            
            # Kalkulasi posisi relatif
            if c_max_clv == c_min_clv:
                pos = 0.5
            else:
                pos = (clv_user - c_min_clv) / (c_max_clv - c_min_clv)
            
            final_disc = d_min + (pos * (d_max - d_min))
            
            results.append({
                'customer_id': row['customer_id'],
                'cluster': str(c_id),
                'clv_score': clv_user,
                'min_cluster_disc': d_min,
                'max_cluster_disc': d_max,
                'adaptive_discount_percent': round(float(final_disc), 2)
            })

        return pd.DataFrame(results)