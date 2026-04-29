from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from .models import Document
from .forms import DocumentUploadForm


@require_http_methods(['GET', 'POST'])
def upload_document(request):
    """
    Handle document file uploads.
    GET: Display upload form
    POST: Process file upload and save document
    """
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            document = form.save(commit=False)
            # Extract file type from filename extension
            import os
            ext = os.path.splitext(document.file.name)[1].lower().lstrip('.')
            document.file_type = ext
            document.save()
            
            # Redirect to dashboard after successful upload
            return redirect('dashboard')
        else:
            # Form has errors, re-render with error messages
            context = {'form': form}
            return render(request, 'documents/upload.html', context)
    
    # GET request - display form
    form = DocumentUploadForm()
    context = {'form': form}
    return render(request, 'documents/upload.html', context)


def dashboard(request):
    """
    Display dashboard with list of uploaded documents.
    """
    documents = Document.objects.all().order_by('-uploaded_at')
    
    context = {
        'documents': documents,
        'total_count': documents.count(),
    }
    return render(request, 'documents/dashboard.html', context)
