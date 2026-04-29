from django.db import models


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('review', 'Needs Review'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
    ]

    TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('purchase_order', 'Purchase Order'),
        ('unknown', 'Unknown'),
    ]

    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # metadata
    file_type = models.CharField(max_length=10, blank=True)  # pdf, csv, txt, image
    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='unknown')

    # extracted data
    supplier = models.CharField(max_length=255, blank=True)
    document_number = models.CharField(max_length=100, blank=True)

    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=10, blank=True)

    subtotal = models.FloatField(null=True, blank=True)
    tax = models.FloatField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')

    def __str__(self):
        return self.document_number or f"Document {self.id}"


class LineItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='items')

    description = models.CharField(max_length=255)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    total = models.FloatField()

    def __str__(self):
        return f"{self.description} ({self.document_id})"


class ValidationIssue(models.Model):
    SEVERITY_CHOICES = [
        ('error', 'Error'),
        ('warning', 'Warning'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='issues')

    field = models.CharField(max_length=100)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='error')

    def __str__(self):
        return f"{self.field}: {self.message[:30]}"