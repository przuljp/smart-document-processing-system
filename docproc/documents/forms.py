from django import forms
from .models import Document


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading document files"""

    class Meta:
        model = Document
        fields = ['file']
        widgets = {
            'file': forms.FileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.pdf,.csv,.txt',
                    'required': True,
                }
            ),
        }
        labels = {
            'file': 'Select Document',
        }

    def clean_file(self):
        """Validate file upload"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError('Please select a file to upload.')
        
        # Check file size (5MB limit)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size exceeds 5MB limit.')
        
        # Get file extension
        import os
        ext = os.path.splitext(file.name)[1].lower()
        allowed_extensions = ['.pdf', '.csv', '.txt']
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'File type "{ext}" is not allowed. Allowed types: {", ".join(allowed_extensions)}'
            )
        
        return file


class DocumentEditForm(forms.ModelForm):
    """Form for editing document details"""

    class Meta:
        model = Document
        fields = [
            'supplier',
            'document_number',
            'issue_date',
            'due_date',
            'subtotal',
            'tax',
            'total',
        ]
        widgets = {
            'supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Supplier name',
            }),
            'document_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Invoice/PO number',
            }),
            'issue_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'subtotal': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
            }),
        }
        labels = {
            'supplier': 'Supplier Name',
            'document_number': 'Document Number',
            'issue_date': 'Issue Date',
            'due_date': 'Due Date',
            'subtotal': 'Subtotal',
            'tax': 'Tax',
            'total': 'Total',
        }
