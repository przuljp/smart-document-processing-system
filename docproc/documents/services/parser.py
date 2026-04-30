"""
Document parser service for extracting structured data from various file formats.

Supports: CSV, PDF, TXT
Returns extracted data as a dictionary with keys:
    - supplier
    - document_number
    - subtotal
    - tax
    - total
    - currency (optional)
"""

import csv
import re
import os
from typing import Dict, Any
from datetime import datetime



def parse_document(document) -> Dict[str, Any]:
    """
    Main parser function that detects file type and routes to appropriate parser.
    
    Args:
        document: Document instance with file field and file_type attribute
        
    Returns:
        Dictionary with extracted data, or empty dict if parsing fails
        {
            'supplier': str,
            'document_number': str,
            'subtotal': float,
            'tax': float,
            'total': float,
            'currency': str (optional)
        }
    """
    try:
        # Get file type from document
        file_type = document.file_type.lower() if document.file_type else ''
        
        # Get file path
        file_path = document.file.path
        
        # Route to appropriate parser
        if file_type == 'csv':
            return parse_csv(file_path, document=document)
        elif file_type == 'pdf':
            return parse_pdf(file_path)
        elif file_type == 'txt':
            return parse_txt(file_path)
        else:
            # Unsupported file type
            return {}
            
    except Exception as e:
        # Log error silently, return empty dict (do not crash)
        print(f"Error parsing document: {e}")
        return {}


def parse_csv(file_path: str, document=None) -> Dict[str, Any]:
    """
    Parse CSV file and extract financial data.
    
    Detects CSV type:
    1. LINE ITEMS CSV - Has columns: desc, qty, price, total
       - Creates LineItem objects
       - Calculates subtotal/total from line items
       - Sets document status to "review"
       
    2. STANDARD CSV - Has columns: supplier, document_number, subtotal, tax, total
       - Extracts first row as document metadata
    
    Args:
        file_path: Path to CSV file
        document: Document instance (required for line items CSV to create LineItems)
        
    Returns:
        Dictionary with extracted data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames is None:
                return {}
            
            # Detect CSV type based on headers
            fieldnames = [f.lower().strip() for f in reader.fieldnames]
            
            # Check if it's a line items CSV
            if _is_line_items_csv(fieldnames):
                # Reset file pointer and reopen
                pass  # We'll reopen in the helper function
            
        # Reopen file and detect type again
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = [f.lower().strip() for f in reader.fieldnames]
            
            if _is_line_items_csv(fieldnames):
                # Parse as line items CSV
                return parse_line_items_csv(file_path, document)
            else:
                # Parse as standard document CSV
                return parse_standard_csv(file_path)
        
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return {}


def parse_standard_csv(file_path: str) -> Dict[str, Any]:
    """
    Parse standard document-level CSV with supplier and financial metadata.
    
    Expected headers: supplier, document_number, subtotal, tax, total, currency
    Extracts first row of data.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Dictionary with extracted data
    """
    try:
        extracted_data = {}
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames is None:
                return {}
            
            # Read first row of data
            for row in reader:
                # Map CSV columns to our data structure
                extracted_data['supplier'] = row.get('supplier', '').strip()
                extracted_data['document_number'] = row.get('document_number', '').strip()
                extracted_data['subtotal'] = _parse_float(row.get('subtotal', ''))
                extracted_data['tax'] = _parse_float(row.get('tax', ''))
                extracted_data['total'] = _parse_float(row.get('total', ''))
                extracted_data['currency'] = row.get('currency', 'USD').strip()
                
                # Return first row of data
                break
        
        return extracted_data
        
    except Exception as e:
        print(f"Error parsing standard CSV: {e}")
        return {}


def parse_line_items_csv(file_path: str, document) -> Dict[str, Any]:
    """
    Parse line items CSV and create LineItem objects.
    
    Expected headers: desc, qty, price, total
    - Loops through ALL rows (not just first)
    - Creates LineItem for each row
    - Calculates subtotal and total from all rows
    - Sets document.status = "review" (missing supplier, dates, etc.)
    
    Args:
        file_path: Path to CSV file
        document: Document instance to link line items to
        
    Returns:
        Dictionary with extracted data: {subtotal, total}
    """
    try:
        line_items = []
        total_amount = 0.0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames is None:
                return {}
            
            # Process ALL rows as line items
            for row in reader:
                try:
                    description = row.get('desc', '').strip()
                    qty = _parse_float(row.get('qty', '0'))
                    unit_price = _parse_float(row.get('price', '0'))
                    row_total = _parse_float(row.get('total', '0'))
                    
                    # Skip empty rows
                    if not description:
                        continue
                    
                    # Create LineItem object
                    from documents.models import LineItem
                    line_item = LineItem(
                        document=document,
                        description=description,
                        quantity=qty if qty is not None else 0,
                        unit_price=unit_price if unit_price is not None else 0,
                        total=row_total if row_total is not None else 0,
                    )
                    line_items.append(line_item)
                    
                    # Sum up totals
                    if row_total is not None:
                        total_amount += row_total
                    
                except Exception as row_error:
                    print(f"Error processing line item row: {row_error}")
                    continue
            
            # Bulk create all line items
            if line_items:
                LineItem.objects.bulk_create(line_items)
        
        # Set document status to review (missing supplier, dates, etc.)
        document.status = 'review'
        
        # Return document-level data
        extracted_data = {
            'subtotal': total_amount,
            'total': total_amount,  # No tax for line items CSV
            'supplier': '',  # Will be filled manually in review
            'document_number': '',  # Will be filled manually in review
        }
        
        return extracted_data
        
    except Exception as e:
        print(f"Error parsing line items CSV: {e}")
        return {}


def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    Parse PDF file and extract financial data using regex patterns.
    
    Attempts to extract:
    - Supplier/Vendor name
    - Document/Invoice number
    - Subtotal, Tax, Total amounts
    - Currency
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Dictionary with extracted data
    """
    try:
        import pdfplumber
    except ImportError:
        print("pdfplumber not installed. Install with: pip install pdfplumber")
        return {}
    
    try:
        extracted_data = {}
        
        with pdfplumber.open(file_path) as pdf:
            # Extract text from all pages
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""
        
        # Extract supplier/vendor name (look for common patterns)
        supplier_match = re.search(
            r'(?:supplier|vendor|from|bill\s*from|invoiced\s*by)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['supplier'] = supplier_match.group(1).strip() if supplier_match else ''
        
        # Extract document number (match only 'Number:' pattern)
        doc_num_match = re.search(
            r'number[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['document_number'] = doc_num_match.group(1).strip() if doc_num_match else ''
        
        # Extract subtotal
        subtotal_match = re.search(
            r'subtotal[:\s]+[\$£€]?\s*([0-9,]+\.?\d*)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['subtotal'] = _parse_float(subtotal_match.group(1)) if subtotal_match else None
        
        # Extract tax
        tax_match = re.search(r'(?:tax|vat|gst)[^\n]*', full_text, re.IGNORECASE)
        if tax_match:
            numbers = re.findall(r'[\d.]+', tax_match.group())
            extracted_data['tax'] = _parse_float(numbers[-1]) if numbers else None
        else:
            extracted_data['tax'] = None

        # Extract total (invoice total, grand total, etc.)
        total_match = re.search(
            r'(?:^|\n)(?:grand\s*total|amount\s*due|\btotal\b)[:\s]+[\$£€]?\s*([0-9,]+\.?\d*)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['total'] = _parse_float(total_match.group(1)) if total_match else None
        
        # Extract currency (look for currency symbols or codes)
        currency_match = re.search(
            r'(?:currency|currency\s*code)[:\s]*([A-Z]{3})|[\$£€]',
            full_text,
            re.IGNORECASE
        )
        if currency_match:
            extracted_data['currency'] = currency_match.group(1) or _symbol_to_currency(currency_match.group(0))
        else:
            extracted_data['currency'] = 'USD'
        
        # Detect document type
        extracted_data['doc_type'] = _detect_document_type(full_text)
        
    
        # Extract issue date
        date_match = re.search(
            r'(?:date|issue\s*date)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )

        if date_match:
            raw_date = date_match.group(1).strip()

            try:
                extracted_data['issue_date'] = datetime.strptime(
                raw_date,
                "%Y-%m-%d"
                ).date()
            except ValueError:
                extracted_data['issue_date'] = None
        else:
            extracted_data['issue_date'] = None
        
        return extracted_data

            
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return {}


def parse_txt(file_path: str) -> Dict[str, Any]:
    try:
        extracted_data = {}

        # Read text file
        with open(file_path, 'r', encoding='utf-8') as txtfile:
            full_text = txtfile.read()

        # --------------------
        # Supplier
        # --------------------
        supplier_match = re.search(
            r'(?:from|supplier|vendor|bill\s*from|invoiced\s*by)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['supplier'] = supplier_match.group(1).strip() if supplier_match else ''

        # --------------------
        # Document number
        # --------------------
        doc_num_match = re.search(
            r'(?:^|\n)(?:invoice\s*number|number)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['document_number'] = doc_num_match.group(1).strip() if doc_num_match else ''

        # --------------------
        # Issue date
        # --------------------
        date_match = re.search(
            r'(?:date|issue\s*date)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )

        if date_match:
            raw_date = date_match.group(1).strip()
            try:
                extracted_data['issue_date'] = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except:
                extracted_data['issue_date'] = None
        else:
            extracted_data['issue_date'] = None

        # --------------------
        # Due date
        # --------------------
        due_match = re.search(
            r'(?:^|\n)\s*(?:payment\s*due|due\s*date|due)[:\s]+([^\n]+)',
            full_text,
            re.IGNORECASE
        )       

        if due_match:
            raw_due = due_match.group(1).strip()

            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
                try:
                    extracted_data['due_date'] = datetime.strptime(raw_due, fmt).date()
                    break
                except:
                    continue
            else:
                extracted_data['due_date'] = None
        else:
            extracted_data['due_date'] = None

        # --------------------
        # Subtotal
        # --------------------
        subtotal_match = re.search(
            r'subtotal[:\s]+[\$£€]?\s*([0-9,]+\.?\d*)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['subtotal'] = _parse_float(subtotal_match.group(1)) if subtotal_match else None

        # --------------------
        # Tax (uzima zadnji broj)
        # --------------------
        tax_match = re.search(r'(?:tax|vat|gst)[^\n]*', full_text, re.IGNORECASE)

        if tax_match:
            numbers = re.findall(r'[\d.]+', tax_match.group())
            extracted_data['tax'] = _parse_float(numbers[-1]) if numbers else None
        else:
            extracted_data['tax'] = None

        # --------------------
        # Total (ne hvata subtotal)
        # --------------------
        total_match = re.search(
            r'(?:^|\n)(?:grand\s*total|amount\s*due|\btotal\b)[:\s]+[\$£€]?\s*([0-9,]+\.?\d*)',
            full_text,
            re.IGNORECASE
        )
        extracted_data['total'] = _parse_float(total_match.group(1)) if total_match else None

        # --------------------
        # Currency
        # --------------------
        currency_match = re.search(
            r'(?:currency)[:\s]*([A-Z]{3})',
            full_text,
            re.IGNORECASE
        )

        if currency_match:
            extracted_data['currency'] = currency_match.group(1)
        else:
            symbol_match = re.search(r'[\$£€]', full_text)
            extracted_data['currency'] = _symbol_to_currency(symbol_match.group()) if symbol_match else 'USD'

        # --------------------
        # Document type
        # --------------------
        extracted_data['doc_type'] = _detect_document_type(full_text)

        return extracted_data

    except Exception as e:
        print(f"Error parsing TXT: {e}")
        return {}


# ============================================================================
# Helper Functions
# ============================================================================

def _is_line_items_csv(fieldnames: list) -> bool:
    """
    Detect if CSV is a line items file based on column headers.
    
    Line items CSV should have fields: desc, qty, price, total
    Standard CSV should have fields: supplier, document_number, subtotal, tax, total
    
    Args:
        fieldnames: List of column names (lowercase, stripped)
        
    Returns:
        True if CSV appears to be line items format
    """
    # Line items identifiers
    line_items_indicators = {'desc', 'qty', 'price', 'total'}
    
    # Standard CSV identifiers
    standard_csv_indicators = {'supplier', 'document_number', 'subtotal'}
    
    # Normalize fieldnames
    fieldnames_set = {f.lower().strip() for f in fieldnames}
    
    # Check for line items indicators
    has_line_items = line_items_indicators.issubset(fieldnames_set)
    
    # Check for standard CSV indicators
    has_standard_csv = any(ind in fieldnames_set for ind in standard_csv_indicators)
    
    # If it has all line items fields and NOT standard CSV fields, it's line items
    if has_line_items and not has_standard_csv:
        return True
    
    return False


def _detect_document_type(text: str) -> str:
    """
    Detect document type from text content.
    
    Checks for keywords:
    - "Invoice" → "invoice"
    - "Purchase Order" or "PO" → "purchase_order"
    - else → "unknown"
    
    Args:
        text: Full document text
        
    Returns:
        Document type: "invoice", "purchase_order", or "unknown"
    """
    text_lower = text.lower()
    
    # Check for invoice
    if 'invoice' in text_lower:
        return 'invoice'
    
    # Check for purchase order
    if 'purchase order' in text_lower or re.search(r'\bpo\b', text_lower):
        return 'purchase_order'
    
    # Default to unknown
    return 'unknown'


def _parse_float(value: str) -> float:
    """
    Convert string to float, handling common number formats.
    
    Handles:
    - Comma-separated thousands: "1,234.56"
    - European format: "1.234,56"
    - Currency symbols: "$1234"
    
    Args:
        value: String representation of number
        
    Returns:
        Float value, or None if conversion fails
    """
    if not value or not isinstance(value, str):
        return None
    
    try:
        # Remove whitespace
        value = value.strip()
        
        # Remove currency symbols
        value = re.sub(r'[\$£€]', '', value)
        
        # Handle comma as thousands separator (US format)
        if ',' in value and '.' in value:
            # US format: 1,234.56
            value = value.replace(',', '')
        elif ',' in value and value.count(',') == 1 and value.rfind(',') > value.rfind('.'):
            # European format with comma: 1.234,56 or 1234,56
            value = value.replace('.', '').replace(',', '.')
        elif ',' in value and '.' not in value:
            # Ambiguous, assume comma is thousands separator
            value = value.replace(',', '')
        
        return float(value)
        
    except (ValueError, AttributeError):
        return None


def _symbol_to_currency(symbol: str) -> str:
    """
    Convert currency symbol to currency code.
    
    Args:
        symbol: Currency symbol ($, £, €, etc.)
        
    Returns:
        ISO 4217 currency code
    """
    symbol_map = {
        '$': 'USD',
        '£': 'GBP',
        '€': 'EUR',
    }
    return symbol_map.get(symbol, 'USD')
