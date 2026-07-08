from django.db import models
from .base_model import BaseModel
from .lrfm_reference import LRFMReference
from .ahp_configuration import AHPConfiguration

class ClusterLRFM(BaseModel):
    # ID Klaster murni dari K-Means (0, 1, 2, 3)
    cluster_id = models.IntegerField()
    k_value = models.IntegerField(help_text="Nilai K yang digunakan saat pembentukan klaster ini.", null=True, blank=True)
    
    # Rata-rata (Mean) klaster ini untuk perbandingan Grand Mean
    mean_length = models.FloatField(help_text="Rata-rata Length (L) untuk klaster ini REAL.")
    mean_recency = models.FloatField(help_text="Rata-rata Recency (R) untuk klaster ini REAL.")
    mean_frequency = models.FloatField(help_text="Rata-rata Frequency (F) untuk klaster ini REAL.")
    mean_monetary = models.FloatField(help_text="Rata-rata Monetary (M) untuk klaster ini REAL.")
    
    min_discount_percent = models.FloatField(default=0, help_text="Batas bawah diskon (%)", null=True, blank=True)
    max_discount_percent = models.FloatField(default=0, help_text="Batas atas diskon (%)", null=True, blank=True)
    
    # Mapping ke simbol dan nama grup di LRFMReference
    lrfm_reference = models.ForeignKey(
        LRFMReference, 
        on_delete=models.PROTECT,
        related_name='clusters'
    )
    
    # Bobot AHP yang digunakan saat pembentukan klaster ini
    ahp_config = models.ForeignKey(
        AHPConfiguration, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'context': 'LRFM'}
    )

    def __str__(self):
        return f"Cluster {self.cluster_id} ({self.lrfm_reference.symbol})"