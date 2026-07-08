from django.db import models

from babyspa_data.models.product import Product
from .base_model import BaseModel
from .customers import Customer
from .branch import Branch

class Transaction(BaseModel):
    ref_number = models.CharField(max_length=50, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    branch = models.ForeignKey(Branch, on_delete=models.RESTRICT, related_name='transactions')
    scheduled_date = models.DateTimeField()
    total_price = models.FloatField()
    status = models.CharField(max_length=50, default='PAID')

    def __str__(self):
        return self.ref_number

class TransactionItem(BaseModel):
    ref_number = models.CharField(max_length=50, null=True, blank=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    quantity = models.IntegerField(default=1)
    sale_price = models.FloatField(null=True, blank=True)  # Harga jual per item, bisa berbeda dari retail_price
    duration = models.FloatField(null=True, blank=True)  # Durasi layanan dalam menit, jika relevan
    status = models.CharField(max_length=50, default='COMPLETED')
    scheduled_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.item_name}"