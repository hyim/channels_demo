from django.db import models


class ObservableStatus(models.Model):

    is_alive = models.BooleanField(default=True)
