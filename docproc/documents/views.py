from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import Http404
from .models import Document
from .forms import DocumentUploadForm, DocumentEditForm
from .services.parser import parse_document
from .services.validation import validate_document
import os


@require_http_methods(['GET', 'POST'])
def upload_document(request):
    """
    Handle document file uploads.
    GET: Display upload form
    POST: Process file upload and save document
    
    After saving, attempts to parse and extract data from the document.
    """
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            document = form.save(commit=False)
            
            # Extract file type from filename extension
            ext = os.path.splitext(document.file.name)[1].lower().lstrip('.')
            document.file_type = ext
            
            # Save document first (required for file path access)
            document.save()
            
            # Parse and extract data from the document
            extracted_data = parse_document(document)
            
            # Update document with extracted data
            if extracted_data:
                document.supplier = extracted_data.get('supplier', '')
                document.document_number = extracted_data.get('document_number', '')
                document.subtotal = extracted_data.get('subtotal')
                document.tax = extracted_data.get('tax')
                document.total = extracted_data.get('total')
                document.currency = extracted_data.get('currency', 'USD')
                document.doc_type = extracted_data.get('doc_type', 'unknown')
                document.issue_date = extracted_data.get('issue_date')
                
                # Save updated document
                document.save()
            
            # Validate document (creates ValidationIssue records and updates status)
            validation_result = validate_document(document)
            
            # Redirect to dashboard after processing
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


@require_http_methods(['GET', 'POST'])
def document_detail(request, document_id):
    """
    Display document details and allow editing/validation.
    
    GET: Display document with validation issues
    POST: Save edits and re-validate
    """
    document = get_object_or_404(Document, id=document_id)
    session_key = f'document_{document.id}_original_data'

    def get_original_data(document):
        return {
            'supplier': document.supplier,
            'document_number': document.document_number,
            'issue_date': document.issue_date.isoformat() if document.issue_date else '',
            'due_date': document.due_date.isoformat() if document.due_date else '',
            'subtotal': document.subtotal,
            'tax': document.tax,
            'total': document.total,
        }

    original_data = request.session.get(session_key, get_original_data(document))
    
    if request.method == 'POST':
        if session_key not in request.session:
            request.session[session_key] = original_data
            request.session.modified = True

        form = DocumentEditForm(request.POST, instance=document)
        
        if form.is_valid():
            # Save updated document
            document = form.save()
            
            # Re-validate after changes
            validate_document(document)
            
            # Redirect to same page to show updated status
            return redirect('document_detail', document_id=document.id)
    else:
        form = DocumentEditForm(instance=document)
    
    # Get related data
    line_items = document.items.all()
    validation_issues = document.issues.all()
    
    # Check if document has any ERROR issues
    has_errors = validation_issues.filter(severity='error').exists()
    
    context = {
        'document': document,
        'form': form,
        'line_items': line_items,
        'validation_issues': validation_issues,
        'has_errors': has_errors,
        'original_data': original_data,
    }
    
    return render(request, 'documents/review.html', context)


@require_http_methods(['POST'])
def mark_as_validated(request, document_id):
    """
    Mark document as validated.
    
    Only allows if no ERROR level validation issues exist.
    """
    document = get_object_or_404(Document, id=document_id)
    
    # Check if document has any ERROR issues
    has_errors = document.issues.filter(severity='error').exists()
    
    if not has_errors:
        document.status = 'validated'
        document.save()
    
    # Redirect back to document detail
    return redirect('document_detail', document_id=document.id)


@require_http_methods(['POST'])
def reject_document(request, document_id):
    """
    Mark document as rejected.
    """
    document = get_object_or_404(Document, id=document_id)
    document.status = 'rejected'
    document.save()

    return redirect('dashboard')
