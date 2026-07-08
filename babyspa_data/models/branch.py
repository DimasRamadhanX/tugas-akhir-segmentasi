from django.db import models
from .base_model import BaseModel

class Branch(BaseModel):
    location_id = models.IntegerField(unique=True, help_text="Contoh: 4807")
    branch_name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)