from django.db import models


class CalvingEvent(models.Model):
    """Stores a simple calving observation captured by the AI assistant flow."""

    cow_id = models.CharField(max_length=50)
    observed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-observed_at"]
        verbose_name = "calving event"
        verbose_name_plural = "calving events"

    def __str__(self):
        return f"{self.cow_id} @ {self.observed_at}"

