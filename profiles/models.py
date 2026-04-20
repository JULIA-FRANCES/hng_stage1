import uuid
from django.db import models

try:
    from uuid_extensions import uuid7
except ImportError:
    uuid7 = uuid.uuid4

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True)
    gender = models.CharField(max_length=50)
    gender_probability = models.FloatField()
    sample_size = models.IntegerField(null=True, blank=True)
    age = models.IntegerField()
    age_group = models.CharField(max_length=50)
    country_id = models.CharField(max_length=2)
    country_name = models.CharField(max_length=255, null=True, blank=True)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profiles_profile'

    def __str__(self):
        return self.name