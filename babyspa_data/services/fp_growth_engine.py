import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from django.db import transaction as db_transaction
from django.db.models import Q
from babyspa_data.models.transactions import TransactionItem
from babyspa_data.models.product import Product, ProductRecommendation, ProductScore
from babyspa_data.models.cluster_lrfm import ClusterLRFM

class FPGrowthEngine:
    def __init__(self, min_support=0.01, min_threshold=1.0):
        self.min_support = min_support
        self.min_threshold = min_threshold

    # PERUBAHAN 1: Menambahkan customer_list=None di parameter
    def get_basket_data(self, cluster_obj=None, customer_list=None, id_mapping=None, name_mapping=None):
        # 1. Tentukan status valid (PAID & UNKNOWN)
        status_list = ['PAID', 'UNKNOWN', 'paid', 'unknown']
        
        # 2. Ambil data dengan detail jam
        queryset = TransactionItem.active_objects.filter(
            transaction__status__in=status_list
        ).select_related('transaction', 'product')

        # 3. Filter berdasarkan klaster jika ada (Logika K-Means Lama)
        if cluster_obj:
            from babyspa_data.models.customer_segment import CustomerSegment
            customer_ids = CustomerSegment.active_objects.filter(
                cluster_lrfm=cluster_obj
            ).values_list('customer_id', flat=True)
            queryset = queryset.filter(transaction__customer_id__in=customer_ids)
            
        # PERUBAHAN 2: Filter berdasarkan list customer jika tidak ada cluster_obj (Logika DBSCAN Baru)
        elif customer_list is not None:
            queryset = queryset.filter(transaction__customer_id__in=customer_list)

        # 4. Ambil transaction_id, jam detail, id produk, dan nama produk
        data = list(queryset.values(
            'transaction_id', 
            'scheduled_date',
            'product_id', 
            'product__item_name'
        ))
        
        df = pd.DataFrame(data)
        
        if df.empty: 
            return None

        # =============================================================
        # IMPLEMENTASI FILTER MAPPING & CONDENSED NAME
        # =============================================================
        if id_mapping:
            # Timpa ID Varian menjadi ID Master
            df['product_id'] = df['product_id'].replace(id_mapping)
            
            # Terapkan nama condensed jika ada di name_mapping
            if name_mapping:
                df['product__item_name'] = df['product_id'].map(name_mapping).fillna(df['product__item_name'])
                
            # Mencegah 1 transaksi memiliki produk kembar akibat peleburan ID cabang
            df = df.drop_duplicates(subset=['transaction_id', 'product_id'])

        # Ubah ke format string agar bisa digabungkan sebagai Key Session
        df['session_key'] = (
            df['transaction_id'].astype(str) + "_" + 
            df['scheduled_date'].dt.strftime('%Y-%m-%d %H:%M')
        )

        # 5. Kelompokkan produk berdasarkan kunci sesi tersebut
        basket = df.groupby('session_key')['product__item_name'].apply(list).tolist()
        
        # 6. Filter: FP-Growth hanya bisa memproses basket dengan > 1 item
        clean_basket = [items for items in basket if len(set(items)) > 1]
        
        return clean_basket
    
    # PERUBAHAN 3: Menambahkan customer_list=None di parameter
    def run_fp_growth(self, cluster_obj=None, customer_list=None, id_mapping=None, name_mapping=None):
        """Menjalankan FP-Growth dan menyimpan/mengembalikan rules."""
        
        # PERUBAHAN 4: Meneruskan customer_list ke get_basket_data
        basket = self.get_basket_data(cluster_obj, customer_list, id_mapping, name_mapping)
        if not basket:
            print("Data transaksi kosong atau tidak memenuhi syarat.")
            return None

        # 1. Encoding Data
        te = TransactionEncoder()
        te_ary = te.fit(basket).transform(basket)
        df_encoded = pd.DataFrame(te_ary, columns=te.columns_)

        # 2. FP-Growth Algoritma
        frequent_itemsets = fpgrowth(df_encoded, min_support=self.min_support, use_colnames=True)
        if frequent_itemsets.empty:
            print("Tidak ditemukan frequent itemsets.")
            return None

        # 3. Generate Association Rules (Fokus pada Lift)
        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=self.min_threshold)
        
        # Sort berdasarkan lift tertinggi
        rules = rules.sort_values('lift', ascending=False).reset_index(drop=True)
        
        return rules

    def save_to_db(self, rules, cluster_obj=None):
        """Menyimpan hasil ke model ProductRecommendation."""
        # Validasi awal
        if rules is None or rules.empty or cluster_obj is None:
            print("Penyimpanan dibatalkan: Data rules kosong atau cluster_obj tidak ditemukan.")
            return

        with db_transaction.atomic():
            # 1. Bersihkan data lama untuk klaster spesifik ini
            ProductRecommendation.active_objects.filter(cluster_lrfm=cluster_obj).delete()
            
            saved_count = 0
            for index, row in rules.iterrows():
                # 2. Ambil daftar nama dari frozenset
                ant_names = list(row['antecedents'])
                cons_names = list(row['consequents'])
                
                # 3. Cari objek Product di DB
                # PENGAMANAN: Cari berdasarkan nama asli (item_name) ATAU nama yang sudah di-condensed (score__name)
                products_ant = Product.active_objects.filter(
                    Q(item_name__in=ant_names) | Q(score__name__in=ant_names)
                ).distinct()
                
                products_cons = Product.active_objects.filter(
                    Q(item_name__in=cons_names) | Q(score__name__in=cons_names)
                ).distinct()
                
                # VALIDASI:
                if products_ant.exists() and products_cons.exists():
                    # 4. Buat objek utama
                    recommendation = ProductRecommendation.active_objects.create(
                        cluster_lrfm=cluster_obj,
                        support=row['support'],
                        confidence=row['confidence'],
                        lift=row['lift'],
                        rank_n=index + 1
                    )
                    
                    # 5. Hubungkan relasi Many-to-Many
                    recommendation.antecedent.set(products_ant)
                    recommendation.consequent.set(products_cons)
                    saved_count += 1
            
            print(f"Berhasil mensinkronisasi {saved_count} rules untuk klaster {cluster_obj.cluster_id}.")

    def visualize_rules(self, rules, title="Association Rules Network"):
        """Visualisasi Network Graph yang bersih dan teratur."""
        if rules is None or rules.empty:
            return

        G = nx.DiGraph()
        for _, row in rules.iterrows():
            # Mengambil item pertama untuk label yang bersih
            ant = list(row['antecedents'])[0]
            cons = list(row['consequents'])[0]
            G.add_edge(ant, cons, weight=row['lift'])

        # Ukuran figure yang pas untuk laporan
        plt.figure(figsize=(10, 8))
        
        # Menggunakan k (jarak antar node) yang lebih besar agar tidak tumpang tindih
        pos = nx.spring_layout(G, k=2.0, seed=42) 
        
        # Gambar elemen grafik
        nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='skyblue', alpha=0.7)
        nx.draw_networkx_edges(G, pos, width=1.5, edge_color='gray', arrowsize=20, alpha=0.5)
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif', font_weight='bold')
        
        plt.title(title, pad=20, fontsize=14)
        plt.axis('off')
        plt.tight_layout()
        plt.show()
        
    def run_filtered_analysis_by_k(self, k_value, id_mapping=None, name_mapping=None):
        """
        Menjalankan analisis FP-Growth secara iteratif untuk semua klaster 
        pada nilai K tertentu dengan filtrasi Top-5 Produk.
        """
        clusters = ClusterLRFM.active_objects.filter(k_value=k_value).order_by('cluster_id')
        
        if not clusters.exists():
            return None

        all_results = {}

        for cluster in clusters:
            # Ambil Top-5 Produk (SAW-AHP) menggunakan kolom 'name' (yang menampung nama generik/condensed)
            top_products = ProductScore.active_objects.filter(
                cluster_id=cluster
            ).order_by('rank')[:5].values_list('name', flat=True)
            
            top_products_list = list(top_products)
            if not top_products_list:
                continue

            rules = self.run_fp_growth(cluster_obj=cluster, id_mapping=id_mapping, name_mapping=name_mapping)
            
            if rules is not None and not rules.empty:
                # FILTRASI: Fokus pada Consequents yang ada di Top-5
                filtered_rules = rules[rules['consequents'].apply(
                    lambda x: any(item in top_products_list for item in x)
                )].copy()

                if not filtered_rules.empty:
                    # Simpan rules ke dictionary untuk dikembalikan
                    all_results[cluster.cluster_id] = filtered_rules
        
        return all_results