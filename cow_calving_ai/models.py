from django.db import models


# Example model for the cow_calving_ai app
class CalvingEvent(models.Model):
    cow_id = models.CharField(max_length=50)
    observed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cow_id} @ {self.observed_at}"

