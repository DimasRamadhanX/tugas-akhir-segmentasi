import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

from babyspa_data.models.cluster_lrfm import ClusterLRFM
from babyspa_data.models.lrfm_reference import LRFMReference
from babyspa_data.models.ahp_configuration import AHPConfiguration

class Clustering:
    def __init__(self, df, clustering_columns):
        self.df = df
        self.cluster_cols = clustering_columns

    def evaluate_optimal_k(self, min_k=2, max_k=10):
        k_values = range(min_k, max_k + 1)
        silhouette_scores = []
        davies_bouldin_scores = []

        for k in k_values:
            kmeans = KMeans(n_clusters=k, init='k-means++', n_init='auto', random_state=42)
            labels = kmeans.fit_predict(self.df[self.cluster_cols])
            
            silhouette_scores.append(silhouette_score(self.df[self.cluster_cols], labels))
            davies_bouldin_scores.append(davies_bouldin_score(self.df[self.cluster_cols], labels))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        ax1.plot(k_values, silhouette_scores, marker='o', color='tab:blue', linewidth=2)
        ax1.set_title('Silhouette Score (Lebih Tinggi Lebih Baik)', fontsize=12)
        ax1.set_xlabel('Jumlah Klaster (k)', fontsize=10)
        ax1.set_ylabel('Score', fontsize=10)
        ax1.set_xticks(k_values)
        ax1.grid(True, linestyle='--', alpha=0.6)

        ax2.plot(k_values, davies_bouldin_scores, marker='s', color='tab:red', linewidth=2)
        ax2.set_title('Davies-Bouldin Index (Lebih Rendah Lebih Baik)', fontsize=12)
        ax2.set_xlabel('Jumlah Klaster (k)', fontsize=10)
        ax2.set_ylabel('Index', fontsize=10)
        ax2.set_xticks(k_values)
        ax2.grid(True, linestyle='--', alpha=0.6)

        plt.tight_layout()
        plt.show()

        return pd.DataFrame({
            'k': k_values,
            'silhouette': silhouette_scores,
            'davies_bouldin': davies_bouldin_scores
        })

    def perform_kmeans(self, optimal_k):
        kmeans = KMeans(n_clusters=optimal_k, init='k-means++', n_init='auto', random_state=42)
        labels = kmeans.fit_predict(self.df[self.cluster_cols])
        
        df_clustered = self.df.copy()
        df_clustered['cluster_id'] = labels 
        
        return df_clustered, kmeans

    def save_clusters_to_db(self, df_clustered, real_columns_map, ahp_context_name='LRFM', reference_mapping=None):
        if reference_mapping is None:
            raise ValueError("Mapping LRFMReference harus disediakan.")

        ahp_config = AHPConfiguration.active_objects.filter(context=ahp_context_name).first()

        # 1. Soft-Delete otomatis via active_objects.all().delete() bawaan manager kamu
        lama_count = ClusterLRFM.active_objects.count()
        if lama_count > 0:
            ClusterLRFM.active_objects.all().delete()
            print(f"{lama_count} data centroid klaster lama berhasil di-soft delete.")

        real_cols = [real_columns_map['L'], real_columns_map['R'], real_columns_map['F'], real_columns_map['M']]
        cluster_means = df_clustered.groupby('cluster_id')[real_cols].mean().reset_index()

        # 2. Ambil referensi sekaligus untuk mengoptimasi query (O(1) cache lookup)
        required_ref_ids = [ref_id for ref_id in reference_mapping.values() if ref_id]
        references_cache = LRFMReference.active_objects.in_bulk(required_ref_ids)

        # 3. Kumpulkan instansiasi model baru
        new_clusters = []
        for index, row in cluster_means.iterrows():
            c_id = int(row['cluster_id'])
            ref_id = reference_mapping.get(c_id)
            lrfm_ref = references_cache.get(ref_id)
            
            if not lrfm_ref: 
                continue 

            new_clusters.append(ClusterLRFM(
                cluster_id=c_id,
                mean_length=row[real_columns_map['L']],
                mean_recency=row[real_columns_map['R']],
                mean_frequency=row[real_columns_map['F']],
                mean_monetary=row[real_columns_map['M']],
                lrfm_reference=lrfm_ref,
                ahp_config=ahp_config
            ))
        
        # 4. Simpan massal menggunakan metode kustom bulk_create_base dari BaseModel-mu
        if new_clusters:
            ClusterLRFM.bulk_create_base(new_clusters)
            
        print("Data centroid baru berhasil disimpan.")