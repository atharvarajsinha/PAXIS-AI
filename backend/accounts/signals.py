from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LearnerProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_learner_profile(sender, instance, created, **kwargs):
    if created:
        LearnerProfile.objects.get_or_create(user=instance)
