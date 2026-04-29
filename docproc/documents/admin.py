from django.contrib import admin
from .models import Document, LineItem, ValidationIssue

admin.site.register(Document)
admin.site.register(LineItem)
admin.site.register(ValidationIssue)