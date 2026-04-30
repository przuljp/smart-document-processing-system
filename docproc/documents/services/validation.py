"""
Document validation service for checking data quality and consistency.

Validates:
1. Required fields (supplier, document_number, issue_date)
2. Total calculations (subtotal + tax = total)
3. Line item calculations (quantity * unit_price = total)
4. Duplicate document numbers
"""

from typing import List, Dict
from ..models import Document, LineItem, ValidationIssue


# Tolerance for float comparisons (e.g., 0.01 = 1 cent)
FLOAT_TOLERANCE = 0.01


def validate_document(document: Document) -> Dict[str, any]:
    """
    Validate a document and create ValidationIssue records for any problems.
    
    Checks:
    - Missing required fields
    - Total calculations
    - Line item calculations
    - Duplicate document numbers
    
    Updates document.status:
    - "validated" if no issues
    - "review" if any issues found
    
    Args:
        document: Document instance to validate
        
    Returns:
        Dictionary with validation results:
        {
            'is_valid': bool,
            'issues': List[Dict] with issue details,
            'issue_count': int
        }
    """
    try:
        # Clear existing validation issues
        document.issues.all().delete()
        
        # Collect all issues
        issues = []
        
        # Validate required fields
        issues.extend(_validate_required_fields(document))
        
        # Validate totals
        issues.extend(_validate_totals(document))
        
        # Validate line items
        issues.extend(_validate_line_items(document))
        
        # Validate duplicates
        issues.extend(_validate_duplicate_document_number(document))
        
        # Create ValidationIssue records for each issue
        for issue in issues:
            ValidationIssue.objects.create(
                document=document,
                field=issue['field'],
                message=issue['message'],
                severity=issue.get('severity', 'error')
            )
        
        # Update document status
        if issues:
            document.status = 'review'
        else:
            document.status = 'validated'
        
        document.save()
        
        # Return validation results
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'issue_count': len(issues)
        }
        
    except Exception as e:
        print(f"Error validating document: {e}")
        return {
            'is_valid': False,
            'issues': [{'field': 'validation', 'message': str(e)}],
            'issue_count': 1
        }


# ============================================================================
# Validation Functions
# ============================================================================

def _validate_required_fields(document: Document) -> List[Dict]:
    """
    Check for missing required fields.
    
    Required fields:
    - supplier
    - document_number
    - issue_date
    
    Args:
        document: Document to validate
        
    Returns:
        List of issues found
    """
    issues = []
    
    # Check supplier
    if not document.supplier or not document.supplier.strip():
        issues.append({
            'field': 'supplier',
            'message': 'Supplier is required',
            'severity': 'error'
        })
    
    # Check document_number
    if not document.document_number or not document.document_number.strip():
        issues.append({
            'field': 'document_number',
            'message': 'Document number is required',
            'severity': 'error'
        })
    
    # Check issue_date
    if not document.issue_date:
        issues.append({
            'field': 'issue_date',
            'message': 'Issue date is required',
            'severity': 'error'
        })
    
    return issues


def _validate_totals(document: Document) -> List[Dict]:
    """
    Validate that subtotal + tax = total.
    
    Allows small tolerance for float rounding errors.
    
    Args:
        document: Document to validate
        
    Returns:
        List of issues found
    """
    issues = []
    
    # Skip if any required field is missing
    if (document.subtotal is None or 
        document.tax is None or 
        document.total is None):
        return issues
    
    # Calculate expected total
    expected_total = document.subtotal + document.tax
    
    # Check if total matches (with tolerance)
    if not _floats_equal(expected_total, document.total):
        issues.append({
            'field': 'total',
            'message': (
                f'Total mismatch: subtotal ({document.subtotal}) + '
                f'tax ({document.tax}) = {expected_total}, '
                f'but total is {document.total}'
            ),
            'severity': 'error'
        })
    
    return issues


def _validate_line_items(document: Document) -> List[Dict]:
    """
    Validate line items: quantity * unit_price should equal total.
    
    Args:
        document: Document to validate
        
    Returns:
        List of issues found
    """
    issues = []
    
    # Get all line items for this document
    line_items = document.items.all()
    
    for item in line_items:
        # Skip if fields are None
        if (item.quantity is None or 
            item.unit_price is None or 
            item.total is None):
            continue
        
        # Calculate expected total
        expected_total = item.quantity * item.unit_price
        
        # Check if total matches (with tolerance)
        if not _floats_equal(expected_total, item.total):
            issues.append({
                'field': f'line_item_{item.id}',
                'message': (
                    f'Line item "{item.description}" has incorrect total: '
                    f'{item.quantity} × ${item.unit_price} = ${expected_total}, '
                    f'but total is ${item.total}'
                ),
                'severity': 'warning'
            })
    
    return issues


def _validate_duplicate_document_number(document: Document) -> List[Dict]:
    """
    Check if document_number already exists in another document.
    
    Args:
        document: Document to validate
        
    Returns:
        List of issues found
    """
    issues = []
    
    # Skip if document_number is empty
    if not document.document_number or not document.document_number.strip():
        return issues
    
    # Check for duplicates (excluding current document)
    duplicate_count = Document.objects.filter(
        document_number=document.document_number.strip()
    ).exclude(id=document.id).count()
    
    if duplicate_count > 0:
        issues.append({
            'field': 'document_number',
            'message': (
                f'Document number "{document.document_number}" '
                f'already exists in {duplicate_count} other document(s)'
            ),
            'severity': 'warning'
        })
    
    return issues


# ============================================================================
# Helper Functions
# ============================================================================

def _floats_equal(a: float, b: float, tolerance: float = FLOAT_TOLERANCE) -> bool:
    """
    Compare two floats with tolerance for rounding errors.
    
    Args:
        a: First value
        b: Second value
        tolerance: Acceptable difference (default 0.01)
        
    Returns:
        True if floats are equal within tolerance
    """
    if a is None or b is None:
        return False
    
    return abs(a - b) <= tolerance
