from django.contrib import admin
from .models import TodoItem, IfcFile

# Register your models here.
admin.site.register(TodoItem) 
admin.site.register(IfcFile)
