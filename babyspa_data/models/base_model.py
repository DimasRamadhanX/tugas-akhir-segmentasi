import uuid
from django.db import models
from django.utils import timezone

# ==========================================
# 1. BASE MODEL & MANAGERS (CORE)
# ==========================================

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self, hard=False, user_id=None):
        if hard:
            return super().delete()
        
        update_kwargs = {'deleted_at': timezone.now()}
        if user_id and hasattr(self.model, 'deleted_by'):
            update_kwargs['deleted_by'] = user_id
            
        return self.update(**update_kwargs)

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

class ActiveManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

class DeadManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).dead()

class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    # Manager
    objects = AllObjectsManager()   
    active_objects = ActiveManager() 
    dead_objects = DeadManager()     
    class Meta:
        abstract = True
        
    @classmethod
    def bulk_create_base(cls, objs):
        now = timezone.now()
        for obj in objs:
            if not obj.id: obj.id = uuid.uuid4()
            obj.created_at = now
            obj.updated_at = now
        return cls.active_objects.bulk_create(objs)

    @classmethod
    def bulk_update_base(cls, objs, fields):
        now = timezone.now()
        for obj in objs:
            obj.updated_at = now
        
        update_fields = list(set(fields) | {'updated_at'})
        return cls.active_objects.bulk_update(objs, update_fields)

    def delete(self, hard=False, user_id=None, **kwargs):
        if hard:
            return super().delete(**kwargs)
        
        self.deleted_at = timezone.now()
        if user_id and hasattr(self, 'deleted_by'):
            self.deleted_by = user_id
        self.save()

    def restore(self):
        self.deleted_at = None
        if hasattr(self, 'deleted_by'):
            self.deleted_by = None
        self.save()

    @property
    def is_active(self):
        return self.deleted_at is None