from django.db import models
from django.db.models import Count, Sum, Max, Min
from django.utils import timezone
from dateutil.relativedelta import relativedelta 

from babyspa_data.models.customers import Customer
from .base_model import BaseModel

# ==============================================================================
# 1. MODEL BARU: PENYIMPAN SKOR (Anak dari Customer)
# ==============================================================================
class CustomerScore(BaseModel):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='customer_score')
    
    # --- NILAI RIIL BEKU (DENORMALISASI) ---
    l_real = models.FloatField(default=0)
    r_real = models.FloatField(default=0)
    f_real = models.FloatField(default=0)
    m_real = models.FloatField(default=0)
    
    # --- NILAI TERNORMALISASI ---
    l_normalized = models.FloatField(default=0)
    r_normalized = models.FloatField(default=0)
    f_normalized = models.FloatField(default=0)
    m_normalized = models.FloatField(default=0)
    
    age = models.IntegerField(default=0, help_text="Usia bayi/anak dalam bulan saat skor dihitung")

    def freeze_score_values(self):
        """
        Fungsi ini dipanggil saat membuat skor baru untuk menghitung dan 
        menyimpan nilai mati (beku) dari riwayat transaksi saat itu juga.
        """
        stats = self.customer.transactions.filter(status='PAID').aggregate(
            first_date=Min('scheduled_date'),
            last_date=Max('scheduled_date'),
            freq=Count('id'),
            total_m=Sum('total_price')
        )

        if stats['first_date'] and stats['last_date']:
            self.l_real = (stats['last_date'] - stats['first_date']).days
        
        if stats['last_date']:
            self.r_real = (timezone.now() - stats['last_date']).days
            
        self.f_real = stats['freq'] or 0
        self.m_real = stats['total_m'] or 0

        # Hitung umur anak
        if self.customer.date_of_birth:
            last_tx = self.customer.transactions.filter(status='PAID').order_by('created_at').last()
            if last_tx and last_tx.created_at:
                diff = relativedelta(last_tx.created_at.date(), self.customer.date_of_birth)
                self.age = (diff.years * 12) + diff.months