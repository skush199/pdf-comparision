"""
PDF Document Comparison Tool

Compares two identically-formatted PDF documents and highlights numerical differences.
Produces both a visual highlighted PDF and a JSON summary report.

Usage:
    python pdf_compare.py <pdf1_path> <pdf2_path> [output_pdf_path]

Example:
    python pdf_compare.py old_report.pdf new_report.pdf highlighted_diff.pdf
"""

import sys
import re
import json
import fitz
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from pathlib import Path


@dataclass
class NumberMatch:
    """Represents a number found in the PDF with its location."""
    value: str
    numeric_value: float
    page: int
    rect: fitz.Rect  # Bounding box coordinates
    line_number: int  # Approximate line number on page


@dataclass
class Difference:
    """Represents a difference found between two PDFs."""
    page: int
    line: int
    old_value: str
    new_value: str
    old_rect: fitz.Rect
    new_rect: fitz.Rect


def extract_numbers_from_page(page: fitz.Page, page_num: int) -> List[NumberMatch]:
    """
    Extract all numbers from a PDF page with their positions.
    
    Args:
        page: PyMuPDF page object
        page_num: Page number (0-indexed)
    
    Returns:
        List of NumberMatch objects with positions
    """
    numbers = []
    
    # Get text blocks with position information
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    
    # Pattern to match numbers: integers, decimals, negative numbers, currency
    # Handles formats like: 123, 1,234, 12.34, -45.67, 1,234.56
    number_pattern = re.compile(r'-?[\d,]+\.?\d*')
    
    line_counter = 0
    
    for block in blocks:
        if block["type"] != 0:  # Skip non-text blocks (images, etc.)
            continue
            
        for line in block.get("lines", []):
            line_counter += 1
            
            for span in line.get("spans", []):
                text = span["text"]
                span_rect = fitz.Rect(span["bbox"])
                
                # Find all numbers in this text span
                for match in number_pattern.finditer(text):
                    num_str = match.group()
                    
                    # Skip if it's just a comma, period, or empty
                    if not num_str or num_str in [',', '.', '-']:
                        continue
                    
                    # Clean and parse the number
                    clean_num = num_str.replace(',', '')
                    try:
                        numeric_val = float(clean_num)
                    except ValueError:
                        continue
                    
                    # Calculate approximate position within the span
                    # This gives us a rough bounding box for the number
                    char_width = span_rect.width / max(len(text), 1)
                    start_x = span_rect.x0 + (match.start() * char_width)
                    end_x = span_rect.x0 + (match.end() * char_width)
                    
                    num_rect = fitz.Rect(
                        start_x,
                        span_rect.y0,
                        end_x,
                        span_rect.y1
                    )
                    
                    numbers.append(NumberMatch(
                        value=num_str,
                        numeric_value=numeric_val,
                        page=page_num,
                        rect=num_rect,
                        line_number=line_counter
                    ))
    
    return numbers


def extract_all_numbers(pdf_path: str) -> List[NumberMatch]:
    """
    Extract all numbers from a PDF document.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        List of all NumberMatch objects from the entire document
    """
    all_numbers = []
    
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        numbers = extract_numbers_from_page(page, page_num)
        all_numbers.extend(numbers)
    
    doc.close()
    
    return all_numbers


def compare_numbers(
    numbers1: List[NumberMatch], 
    numbers2: List[NumberMatch],
    tolerance: float = 0.0001
) -> List[Difference]:
    """
    Compare two lists of numbers and find differences.
    
    Assumes both documents have the same structure, so numbers are aligned
    by their position in the extraction sequence.
    
    Args:
        numbers1: Numbers from first PDF (old/baseline)
        numbers2: Numbers from second PDF (new)
        tolerance: Floating point comparison tolerance
    
    Returns:
        List of Difference objects
    """
    differences = []
    
    # Compare by position - assumes identical structure
    min_len = min(len(numbers1), len(numbers2))
    
    for i in range(min_len):
        n1 = numbers1[i]
        n2 = numbers2[i]
        
        # Compare numeric values with tolerance
        if abs(n1.numeric_value - n2.numeric_value) > tolerance:
            differences.append(Difference(
                page=n1.page,
                line=n1.line_number,
                old_value=n1.value,
                new_value=n2.value,
                old_rect=n1.rect,
                new_rect=n2.rect
            ))
    
    # Handle case where one PDF has more numbers than the other
    if len(numbers1) != len(numbers2):
        print(f"Warning: PDFs have different number counts ({len(numbers1)} vs {len(numbers2)})")
        
        # Report extra numbers in PDF1
        for i in range(min_len, len(numbers1)):
            n = numbers1[i]
            differences.append(Difference(
                page=n.page,
                line=n.line_number,
                old_value=n.value,
                new_value="<missing>",
                old_rect=n.rect,
                new_rect=fitz.Rect()
            ))
        
        # Report extra numbers in PDF2
        for i in range(min_len, len(numbers2)):
            n = numbers2[i]
            differences.append(Difference(
                page=n.page,
                line=n.line_number,
                old_value="<missing>",
                new_value=n.value,
                old_rect=fitz.Rect(),
                new_rect=n.rect
            ))
    
    return differences


def create_highlighted_pdf(
    pdf1_path: str,
    pdf2_path: str,
    differences: List[Difference],
    output_path: str
) -> None:
    """
    Create a side-by-side comparison PDF with differences highlighted.
    
    Args:
        pdf1_path: Path to first (old) PDF
        pdf2_path: Path to second (new) PDF
        differences: List of differences found
        output_path: Path for output highlighted PDF
    """
    doc1 = fitz.open(pdf1_path)
    doc2 = fitz.open(pdf2_path)
    
    # Create output document
    output_doc = fitz.open()
    
    # Get maximum page count
    max_pages = max(len(doc1), len(doc2))
    
    # Group differences by page for efficient highlighting
    diffs_by_page: Dict[int, List[Difference]] = {}
    for diff in differences:
        if diff.page not in diffs_by_page:
            diffs_by_page[diff.page] = []
        diffs_by_page[diff.page].append(diff)
    
    for page_num in range(max_pages):
        # Get pages (or create blank if one PDF is shorter)
        page1 = doc1[page_num] if page_num < len(doc1) else None
        page2 = doc2[page_num] if page_num < len(doc2) else None
        
        # Calculate dimensions for side-by-side layout
        width1 = page1.rect.width if page1 else 612
        height1 = page1.rect.height if page1 else 792
        width2 = page2.rect.width if page2 else 612
        height2 = page2.rect.height if page2 else 792
        
        # Create new page that fits both pages side by side
        new_width = width1 + width2 + 20  # 20px gap between pages
        new_height = max(height1, height2)
        new_page = output_doc.new_page(width=new_width, height=new_height)
        
        # Insert first page on the left
        if page1:
            new_page.show_pdf_page(
                fitz.Rect(0, 0, width1, height1),
                doc1,
                page_num
            )
        
        # Insert second page on the right
        if page2:
            new_page.show_pdf_page(
                fitz.Rect(width1 + 20, 0, width1 + 20 + width2, height2),
                doc2,
                page_num
            )
        
        # Draw highlights for differences on this page
        page_diffs = diffs_by_page.get(page_num, [])
        
        for diff in page_diffs:
            # Highlight in first (old) PDF - RED
            if diff.old_rect.is_valid and not diff.old_rect.is_empty:
                highlight_rect1 = fitz.Rect(
                    diff.old_rect.x0 - 2,
                    diff.old_rect.y0 - 2,
                    diff.old_rect.x1 + 2,
                    diff.old_rect.y1 + 2
                )
                new_page.draw_rect(highlight_rect1, color=(1, 0, 0), width=2)
            
            # Highlight in second (new) PDF - RED (offset to right side)
            if diff.new_rect.is_valid and not diff.new_rect.is_empty:
                highlight_rect2 = fitz.Rect(
                    diff.new_rect.x0 + width1 + 20 - 2,
                    diff.new_rect.y0 - 2,
                    diff.new_rect.x1 + width1 + 20 + 2,
                    diff.new_rect.y1 + 2
                )
                new_page.draw_rect(highlight_rect2, color=(1, 0, 0), width=2)
        
        # Add labels at top
        new_page.insert_text(
            (10, 15),
            "OLD (Baseline)",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 0.8)
        )
        new_page.insert_text(
            (width1 + 30, 15),
            "NEW (Comparison)",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 0.8)
        )
    
    # Save output
    output_doc.save(output_path)
    output_doc.close()
    doc1.close()
    doc2.close()
    
    print(f"Highlighted PDF saved to: {output_path}")


def generate_report(differences: List[Difference], output_pdf_path: str) -> Dict:
    """
    Generate a JSON summary report of the comparison.
    
    Args:
        differences: List of differences found
        output_pdf_path: Path to the generated diff PDF
    
    Returns:
        Dictionary containing the comparison report
    """
    report = {
        "status": "OK" if len(differences) == 0 else "Fail",
        "total_differences": len(differences),
        "differences": [],
        "diff_pdf": output_pdf_path
    }
    
    for diff in differences:
        report["differences"].append({
            "page": diff.page + 1,  # Convert to 1-indexed for readability
            "line": diff.line,
            "old": diff.old_value,
            "new": diff.new_value
        })
    
    return report


def main(pdf1_path: str, pdf2_path: str, output_path: Optional[str] = None) -> Dict:
    """
    Main entry point for PDF comparison.
    
    Args:
        pdf1_path: Path to first (old/baseline) PDF
        pdf2_path: Path to second (new) PDF
        output_path: Optional path for highlighted output PDF
    
    Returns:
        Comparison report as a dictionary
    """
    # Set default output path
    if output_path is None:
        output_path = "highlighted_diff.pdf"
    
    # Validate input files exist
    if not Path(pdf1_path).exists():
        raise FileNotFoundError(f"First PDF not found: {pdf1_path}")
    if not Path(pdf2_path).exists():
        raise FileNotFoundError(f"Second PDF not found: {pdf2_path}")
    
    print(f"Comparing PDFs:")
    print(f"  Old: {pdf1_path}")
    print(f"  New: {pdf2_path}")
    print()
    
    # Step 1: Extract numbers from both PDFs
    print("Extracting numbers from PDF 1...")
    numbers1 = extract_all_numbers(pdf1_path)
    print(f"  Found {len(numbers1)} numbers")
    
    print("Extracting numbers from PDF 2...")
    numbers2 = extract_all_numbers(pdf2_path)
    print(f"  Found {len(numbers2)} numbers")
    print()
    
    # Step 2: Compare numbers
    print("Comparing numbers...")
    differences = compare_numbers(numbers1, numbers2)
    print(f"  Found {len(differences)} differences")
    print()
    
    # Step 3: Create highlighted output PDF
    print("Generating highlighted comparison PDF...")
    create_highlighted_pdf(pdf1_path, pdf2_path, differences, output_path)
    print()
    
    # Step 4: Generate report
    report = generate_report(differences, output_path)
    
    # Print report
    print("=" * 60)
    print("COMPARISON REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print("=" * 60)
    
    return report


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) < 3:
        print(__doc__)
        print("Error: Please provide two PDF files to compare.")
        print("Usage: python pdf_compare.py <pdf1> <pdf2> [output.pdf]")
        sys.exit(1)
    
    pdf1 = sys.argv[1]
    pdf2 = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else "highlighted_diff.pdf"
    
    try:
        result = main(pdf1, pdf2, output)
        
        # Exit with appropriate code
        sys.exit(0 if result["status"] == "OK" else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)
