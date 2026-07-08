from django.db import models
from .base_model import BaseModel

class AHPConfiguration(BaseModel):
    CONTEXT_CHOICES = [
        ('LRFM', 'Customer Segmentation (LRFM)'),
        ('PRODUCT', 'Product Scoring (RFM/P)'),
    ]
    
    name = models.CharField(max_length=100, help_text="Contoh: Bobot Expert AHP 2024")
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES)
    
    # Bobot (Gunakan FloatField)
    w_length = models.FloatField(default=0, null=True, blank=True, help_text="Hanya untuk LRFM")
    w_recency = models.FloatField()
    w_frequency = models.FloatField()
    w_monetary = models.FloatField()
    
    def __str__(self):
        return f"[{self.context}] {self.name}"