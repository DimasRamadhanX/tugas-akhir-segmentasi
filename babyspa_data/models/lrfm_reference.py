from django.db import models
from .base_model import BaseModel

class LRFMReference(BaseModel):
    symbol = models.CharField(max_length=10, unique=True, help_text="Contoh: ↑↑↑↑")
    group_name = models.CharField(max_length=100) # Core Loyal Customer
    main_category = models.CharField(max_length=100) # Pelanggan Inti
    description = models.TextField(null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.symbol} - {self.group_name}"