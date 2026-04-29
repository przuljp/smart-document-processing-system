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
                    'accept': '.pdf,.csv,.txt,.png,.jpg,.jpeg,.xlsx,.xls',
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
        allowed_extensions = ['.pdf', '.csv', '.txt', '.png', '.jpg', '.jpeg', '.xlsx', '.xls']
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(
                f'File type "{ext}" is not allowed. Allowed types: {", ".join(allowed_extensions)}'
            )
        
        return file
