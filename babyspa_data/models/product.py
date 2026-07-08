from django.db import models
from .base_model import BaseModel
from .ahp_configuration import AHPConfiguration
from .cluster_lrfm import ClusterLRFM
from  babyspa_data.models import Branch

class ProductCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    
class Product(BaseModel):
    erp_item_id = models.IntegerField(unique=True, null=True, blank=True)
    item_name = models.CharField(max_length=255)
    retail_price = models.FloatField()
    is_addon = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    duration = models.IntegerField(help_text="Durasi dalam satuan menit", null=True, blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Kategori taksonomi layanan atau barang dari produk ini."
    )
    description = models.TextField(
        null=True, 
        blank=True, 
        help_text="Deskripsi produk, bisa digunakan untuk analisis teks lebih lanjut, mungkin NLP."
    )
    master_product = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL,
        null=True, blank=True, 
        related_name='variants', 
        help_text="Jika produk ini adalah varian berdasakan cabang, hubungkan ke produk utama. Jika tidak, biarkan kosong."
    )
    branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='branch_products',
        help_text="Cabang-cabang tempat produk ini tersedia. Jika produk ini aktif di beberapa cabang sekaligus, pilih cabang terkait."
    )

class ProductScore(BaseModel):
    """Penyimpanan hasil akhir kalkulasi SAW-AHP."""
    name=models.CharField(max_length=255, help_text="Nama unik untuk skor ini, misal 'Global' atau 'Cluster 1'",null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='score')
    
    # Skor RFM yang sudah dinormalisasi untuk transparansi hasil
    r_normalized = models.FloatField(default=0)
    f_normalized = models.FloatField(default=0)
    m_normalized = models.FloatField(default=0)
    
    total_saw_score = models.FloatField()
    rank = models.IntegerField() 
    is_top_n = models.BooleanField(default=False)
    
    cluster_id = models.ForeignKey(
        ClusterLRFM,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Cluster LRFM yang paling cocok untuk produk ini berdasarkan skor RFM_P-nya."
    )
    
    # Referensi bobot yang digunakan saat perhitungan ini dilakukan
    ahp_config = models.ForeignKey(AHPConfiguration, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['rank']

class ProductRecommendation(BaseModel):
    """Hasil Market Basket Analysis (FP-Growth)."""
    antecedent = models.ManyToManyField(Product, related_name='trigger')
    consequent = models.ManyToManyField(Product, related_name='target')
    
    # Hubungkan ke Cluster agar rekomendasi relevan per segmen
    cluster_lrfm = models.ForeignKey(
        ClusterLRFM, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    # Metrik asosiasi untuk validasi hasil MBA
    support = models.FloatField()
    confidence = models.FloatField()
    lift = models.FloatField()
    rank_n = models.IntegerField() 

