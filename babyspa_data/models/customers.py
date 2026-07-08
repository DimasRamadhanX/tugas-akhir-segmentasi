from django.db import models
from .base_model import BaseModel

class Customer(BaseModel):
    erp_id = models.IntegerField(unique=True, help_text="ID asli dari API Zenwel")
    name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.BooleanField(null=True, blank=True, help_text="True untuk laki-laki, False untuk perempuan, null jika tidak diketahui")