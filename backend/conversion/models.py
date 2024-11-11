from django.db import models

# Create your models here.

class TodoItem(models.Model):
    title = models.CharField(max_length = 200)
    completed = models.BooleanField(default = False)


class IfcFile(models.Model):
    ifc_file = models.FileField(null = True)
