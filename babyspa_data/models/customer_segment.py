from django.db import models
from django.db.models import Count, Sum, Max, Min
from django.utils import timezone
from dateutil.relativedelta import relativedelta 

from babyspa_data.models.customers import Customer
from .base_model import BaseModel
from .cluster_lrfm import ClusterLRFM

class CustomerSegment(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_segment')
    clv_score = models.FloatField()
    is_churn = models.BooleanField(default=False)
    
    # --- FIELD BARU UNTUK MENYIMPAN NILAI RIIL (DENORMALISASI) ---
    l_real = models.FloatField(default=0, help_text="Durasi hubungan pelanggan (hari), dihitung dari tanggal transaksi pertama hingga terakhir). KEMUNGKINAN DEPRECATED")
    r_real = models.FloatField(default=0, help_text="Hari sejak kunjungan terakhir,  KEMUNGKINAN DEPRECATED")
    f_real = models.FloatField(default=0, help_text="Jumlah total kunjungan,  KEMUNGKINAN DEPRECATED")
    m_real = models.FloatField(default=0, help_text="Total pengeluaran pelanggan,  KEMUNGKINAN DEPRECATED")

    # --- FIELD BARU UNTUK MENYIMPAN NILAI TERNORMALISASI ---
    l_normalized = models.FloatField(default=0, help_text="Nilai L yang sudah ternormalisasi, siap untuk digunakan dalam algoritma clustering,  KEMUNGKINAN DEPRECATED")
    r_normalized = models.FloatField(default=0, help_text="Nilai R yang sudah ternormalisasi,  KEMUNGKINAN DEPRECATED")
    f_normalized = models.FloatField(default=0, help_text="Nilai F yang sudah ternormalisasi,  KEMUNGKINAN DEPRECATED")
    m_normalized = models.FloatField(default=0, help_text="Nilai M yang sudah ternormalisasi,  KEMUNGKINAN DEPRECATEDs")

    age = models.IntegerField(default=0, help_text="Usia bayi/anak dalam bulan, dihitung dari tanggal lahir dan transaksi terbaru")
    
    # Hubungkan ke hasil klaster
    cluster_lrfm = models.ForeignKey(ClusterLRFM, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_segments')
    
    # --- Pre-calculation Aggregation ---
    def _get_transaction_stats(self):
        """Internal helper untuk mengambil data agregat transaksi."""
        return self.customer.transactions.filter(status='PAID').aggregate(
            first_date=Min('scheduled_date'),
            last_date=Max('scheduled_date'),
            freq=Count('id'),
            total_m=Sum('total_price')
        )

    # --- Getters (Properties) ---

    @property
    def length(self):
        """L: Durasi hubungan pelanggan (hari)."""
        stats = self._get_transaction_stats()
        if stats['first_date'] and stats['last_date']:
            return (stats['last_date'] - stats['first_date']).days
        return 0

    @property
    def recency(self):
        """R: Hari sejak kunjungan terakhir."""
        stats = self._get_transaction_stats()
        if stats['last_date']:
            return (timezone.now() - stats['last_date']).days
        return 0

    @property
    def frequency(self):
        """F: Jumlah total kunjungan."""
        stats = self._get_transaction_stats()
        return stats['freq'] or 0

    @property
    def monetary(self):
        """M: Total pengeluaran pelanggan."""
        stats = self._get_transaction_stats()
        return stats['total_m'] or 0

    @property
    def age_month(self):
        """Age: Usia bayi/anak dalam hitungan bulan berdasarkan tanggal pembuatan transaksi terbaru."""
        # 1. Validasi jika data tanggal lahir customer tidak tersedia
        if not self.customer.date_of_birth:
            return 0
        
        # 2. Ambil transaksi PAID terbaru berdasarkan urutan created_at tertinggi
        # Catatan: ganti 'transactions' dengan nama related_name yang Anda miliki di model Customer
        last_transaction = self.customer.transactions.filter(status='PAID').order_by('created_at').last()
        
        # 3. Jika belum memiliki transaksi PAID sama sekali, kembalikan 0
        if not last_transaction or not last_transaction.created_at:
            return 0
            
        # 4. Ambil nilai date dari created_at (dan bersihkan komponen waktu/timezone)
        last_transaction_date = last_transaction.created_at.date()
            
        # 4. Hitung selisih bulan secara akurat
        diff = relativedelta(last_transaction_date, self.customer.date_of_birth)
        
        return (diff.years * 12) + diff.months

    def __str__(self):
        symbol = self.cluster_lrfm.lrfm_reference.symbol if self.cluster_lrfm else "Unclustered"
        return f"{symbol} - {self.customer.name}"