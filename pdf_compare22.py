"""
PDF Document Comparison Tool with OCR Support

Compares two identically-formatted PDF documents and highlights numerical differences.
Supports both selectable text PDFs and image-based PDFs (scanned/Japanese text) via Google Vision OCR.
Produces both a visual highlighted PDF and a JSON summary report.

Usage:
    python pdf_compare22.py <pdf1_path> <pdf2_path> [output_pdf_path] [--user-type org|byok]

Example:
    python pdf_compare22.py old_report.pdf new_report.pdf highlighted_diff.pdf --user-type org
"""

import sys
import re
import json
import io
import os
import fitz
import pdfplumber
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure stdout for UTF-8 encoding (important for Japanese text on Windows)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

# Try to import Google Cloud Vision (optional dependency for OCR)
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    print("Warning: google-cloud-vision not installed. OCR features will be disabled.")


@dataclass
class NumberMatch:
    """Represents a number found in the PDF with its location."""
    value: str
    numeric_value: float
    page: int
    rect: fitz.Rect  # Bounding box coordinates
    line_number: int  # Approximate line number on page
    source: str = "text"  # "text" or "ocr" to track extraction source


@dataclass
class Difference:
    """Represents a difference found between two PDFs."""
    page: int
    line: int
    old_value: str
    new_value: str
    old_rect: fitz.Rect
    new_rect: fitz.Rect
    source: str = "text"  # "text" or "ocr"


class GoogleVisionOCRProcessor:
    """Handles OCR processing using Google Cloud Vision API."""
    
    def __init__(self, user_type: str = "org"):
        """
        Initialize the OCR processor with appropriate credentials.
        
        Args:
            user_type: "org" to use GOOGLE_APPLICATION_CREDENTIALS from .env,
                      "byok" to use default application credentials
        """
        self.client = None
        self.user_type = user_type
        
        if not VISION_AVAILABLE:
            print("⚠️ Google Cloud Vision not available. OCR will be skipped.")
            return
            
        try:
            if user_type == "org":
                service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not service_account_path:
                    print("⚠️ GOOGLE_APPLICATION_CREDENTIALS not set in .env")
                    return
                if not os.path.exists(service_account_path):
                    print(f"⚠️ Service account file not found: {service_account_path}")
                    return
                credentials = service_account.Credentials.from_service_account_file(service_account_path)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                print("✅ OCR initialized with organization credentials")
            elif user_type == "byok":
                self.client = vision.ImageAnnotatorClient()
                print("✅ OCR initialized with default credentials")
            else:
                print("❌ Invalid user type. Use 'org' or 'byok'.")
        except Exception as e:
            print(f"⚠️ Failed to initialize Google Vision client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OCR is available and properly initialized."""
        return self.client is not None
    
    def looks_like_cid_encoded(self, text: str) -> bool:
        """Detects (cid:XX) patterns indicating CID-encoded garbage."""
        return "(cid:" in text.lower()
    
    def ocr_image_bytes(self, image_bytes: bytes, language_hints: List[str] = None) -> str:
        """
        Call Google Vision OCR on image bytes.
        
        Args:
            image_bytes: PNG/JPEG image data
            language_hints: Language hints for OCR (default: Japanese + English)
            
        Returns:
            Extracted text or empty string on failure
        """
        if not self.client:
            return ""
            
        if language_hints is None:
            language_hints = ["ja", "en"]
            
        try:
            image = vision.Image(content=image_bytes)
            image_context = vision.ImageContext(language_hints=language_hints)
            response = self.client.document_text_detection(image=image, image_context=image_context)
            
            if response.error.message:
                print(f"⚠️ Google Vision OCR error: {response.error.message}")
                return ""
                
            annotation = response.full_text_annotation
            if annotation and annotation.text:
                return annotation.text.strip()
        except Exception as e:
            print(f"⚠️ OCR processing error: {e}")
            
        return ""
    
    def ocr_image_with_boxes(
        self, 
        image_bytes: bytes, 
        image_width: int,
        image_height: int,
        language_hints: List[str] = None
    ) -> List[Dict]:
        """
        Call Google Vision OCR and return words with their bounding boxes.
        
        Args:
            image_bytes: PNG/JPEG image data
            image_width: Width of the image in pixels
            image_height: Height of the image in pixels
            language_hints: Language hints for OCR (default: Japanese + English)
            
        Returns:
            List of dicts with 'text' and 'bbox' (normalized 0-1 coordinates)
        """
        if not self.client:
            return []
            
        if language_hints is None:
            language_hints = ["ja", "en"]
            
        words_with_boxes = []
        
        try:
            image = vision.Image(content=image_bytes)
            image_context = vision.ImageContext(language_hints=language_hints)
            response = self.client.document_text_detection(image=image, image_context=image_context)
            
            if response.error.message:
                print(f"⚠️ Google Vision OCR error: {response.error.message}")
                return []
            
            # Extract word-level bounding boxes from the response
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            # Get the word text
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            
                            # Get bounding box vertices
                            vertices = word.bounding_box.vertices
                            if len(vertices) >= 4:
                                # Get min/max coordinates
                                x_coords = [v.x for v in vertices]
                                y_coords = [v.y for v in vertices]
                                
                                # Normalize to 0-1 range based on image dimensions
                                x0 = min(x_coords) / max(image_width, 1)
                                x1 = max(x_coords) / max(image_width, 1)
                                y0 = min(y_coords) / max(image_height, 1)
                                y1 = max(y_coords) / max(image_height, 1)
                                
                                words_with_boxes.append({
                                    'text': word_text,
                                    'bbox': (x0, y0, x1, y1)  # Normalized coordinates
                                })
                                
        except Exception as e:
            print(f"⚠️ OCR processing error: {e}")
            
        return words_with_boxes
    
    def clamp_bbox_to_page(self, bbox: Tuple, page_bbox: Tuple) -> Optional[Tuple]:
        """Ensure the bbox is safely inside the page bbox."""
        x0, top, x1, bottom = bbox
        page_x0, page_top, page_x1, page_bottom = page_bbox
        
        x0 = max(page_x0, min(x0, page_x1))
        x1 = max(page_x0, min(x1, page_x1))
        top = max(page_top, min(top, page_bottom))
        bottom = max(page_top, min(bottom, page_bottom))
        
        if x0 >= x1 or top >= bottom:
            return None
        return (x0, top, x1, bottom)


def extract_numbers_from_text(
    text: str, 
    page_num: int, 
    page_rect: fitz.Rect, 
    base_line: int = 0,
    source: str = "text"
) -> List[NumberMatch]:
    """
    Extract numbers from text string with estimated positions.
    
    Used for OCR-extracted text where exact positions are not available.
    Estimates bounding boxes based on text position within the region.
    
    Args:
        text: The text to extract numbers from
        page_num: Page number (0-indexed)
        page_rect: The bounding rectangle for the region (coordinates are used as offset)
        base_line: Starting line number
        source: Source of the text ("text" or "ocr")
        
    Returns:
        List of NumberMatch objects
    """
    numbers = []
    
    # Pattern to match numbers: integers, decimals, negative numbers, currency
    number_pattern = re.compile(r'-?[\d,]+\.?\d*')
    
    lines = text.split('\n')
    # Use the region dimensions for relative positioning
    region_width = page_rect.width
    region_height = page_rect.height
    # Use the region's top-left corner as offset
    offset_x = page_rect.x0
    offset_y = page_rect.y0
    
    for line_idx, line in enumerate(lines):
        if not line.strip():
            continue
            
        # Estimate Y position based on line number within the region
        relative_y = (line_idx / max(len(lines), 1)) * region_height
        line_height = region_height / max(len(lines), 1)
        
        for match in number_pattern.finditer(line):
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
            
            # Estimate X position based on character position within the region
            char_width = region_width / max(len(line), 1)
            relative_start_x = match.start() * char_width
            relative_end_x = match.end() * char_width
            
            # Create bounding box with proper page offset
            num_rect = fitz.Rect(
                offset_x + relative_start_x,
                offset_y + relative_y,
                offset_x + relative_end_x,
                offset_y + relative_y + line_height
            )
            
            numbers.append(NumberMatch(
                value=num_str,
                numeric_value=numeric_val,
                page=page_num,
                rect=num_rect,
                line_number=base_line + line_idx + 1,
                source=source
            ))
    
    return numbers


def extract_numbers_from_ocr_words(
    words_with_boxes: List[Dict],
    page_num: int,
    region_rect: fitz.Rect,
    base_line: int = 0
) -> List[NumberMatch]:
    """
    Extract numbers from OCR words with their actual bounding boxes.
    
    This uses the word-level bounding boxes from Google Vision OCR,
    mapped to PDF coordinates using the region's position.
    
    Args:
        words_with_boxes: List of dicts with 'text' and 'bbox' (normalized 0-1 coords)
        page_num: Page number (0-indexed)
        region_rect: The bounding rectangle of the image region on the PDF page
        base_line: Starting line number
        
    Returns:
        List of NumberMatch objects with accurate bounding boxes
    """
    numbers = []
    
    # IMPORTANT: Sort words by spatial position to ensure consistent ordering
    # Sort by Y-position (top to bottom), then by X-position (left to right)
    # Use a tolerance for Y to group words on the same line
    def sort_key(word):
        bbox = word['bbox']
        y_center = (bbox[1] + bbox[3]) / 2
        x_center = (bbox[0] + bbox[2]) / 2
        # Round Y to group words on the same line (tolerance of 0.02 = ~2% of page height)
        y_row = round(y_center, 2)
        return (y_row, x_center)
    
    sorted_words = sorted(words_with_boxes, key=sort_key)
    
    # Patterns to match different types of numeric content:
    # 1. Pure numbers with optional decimals and commas: 123, 1,234.56, -45.67
    # 2. Date-like patterns: 2026-01-21, 01/21/2026
    # 3. Reference numbers: 0142, 0001
    number_pattern = re.compile(r'^-?[\d,]+\.?\d*$')
    date_pattern = re.compile(r'^\d{4}[-/]\d{2}[-/]\d{2}$|^\d{2}[-/]\d{2}[-/]\d{4}$')
    
    # Region dimensions and offset
    region_width = region_rect.width
    region_height = region_rect.height
    offset_x = region_rect.x0
    offset_y = region_rect.y0
    
    line_counter = base_line
    last_y = -1
    
    for word_data in sorted_words:  # Use sorted words for consistent ordering
        word_text = word_data['text']
        norm_bbox = word_data['bbox']  # (x0, y0, x1, y1) normalized 0-1
        
        # Remove currency symbols and clean the text
        clean_text = word_text.replace('¥', '').replace('$', '').replace('€', '').replace('£', '').strip()
        
        # Skip empty text
        if not clean_text:
            continue
        
        # Track line changes for line_number based on Y position
        current_y = norm_bbox[1]
        if last_y < 0 or abs(current_y - last_y) > 0.03:
            line_counter += 1
            last_y = current_y
        
        # Map normalized coordinates to PDF coordinates
        pdf_x0 = offset_x + (norm_bbox[0] * region_width)
        pdf_y0 = offset_y + (norm_bbox[1] * region_height)
        pdf_x1 = offset_x + (norm_bbox[2] * region_width)
        pdf_y1 = offset_y + (norm_bbox[3] * region_height)
        num_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
        
        # Check if this is a date pattern (e.g., 2026-01-21)
        if date_pattern.match(clean_text):
            # For dates, store the full date for comparison
            date_nums = re.findall(r'\d+', clean_text)
            if len(date_nums) == 3:
                try:
                    numeric_val = float(''.join(date_nums))
                    numbers.append(NumberMatch(
                        value=clean_text,
                        numeric_value=numeric_val,
                        page=page_num,
                        rect=num_rect,
                        line_number=line_counter,
                        source="ocr"
                    ))
                except ValueError:
                    pass
            continue
        
        # Check if this is a pure number (123, 1,234.56, -45.67)
        if number_pattern.match(clean_text):
            try:
                numeric_val = float(clean_text.replace(',', ''))
                # Skip all-zero patterns (likely OCR noise from Japanese/other text)
                if clean_text.replace(',', '').replace('.', '').replace('0', '') == '':
                    continue
                if clean_text not in [',', '.', '-']:
                    numbers.append(NumberMatch(
                        value=clean_text,
                        numeric_value=numeric_val,
                        page=page_num,
                        rect=num_rect,
                        line_number=line_counter,
                        source="ocr"
                    ))
            except ValueError:
                pass
            continue
        
        # For composite words (e.g., "INS-INV-2026-5101", "POL-EN-2026-884201")
        # Extract ALL numeric parts and create entries for significant ones
        num_parts = re.findall(r'\d+', clean_text)
        for num_part in num_parts:
            # Skip very short numbers (1-2 digits) from composite words as they're likely noise
            # unless the word only has one number
            if len(num_part) < 3 and len(num_parts) > 1:
                continue
            
            try:
                numeric_val = float(num_part)
                numbers.append(NumberMatch(
                    value=num_part,
                    numeric_value=numeric_val,
                    page=page_num,
                    rect=num_rect,
                    line_number=line_counter,
                    source="ocr"
                ))
            except ValueError:
                pass
    
    return numbers


def extract_numbers_from_page(page: fitz.Page, page_num: int) -> Tuple[List[NumberMatch], bool]:
    """
    Extract all numbers from a PDF page with their positions.
    
    Args:
        page: PyMuPDF page object
        page_num: Page number (0-indexed)
    
    Returns:
        Tuple of (List of NumberMatch objects, bool indicating if text was found)
    """
    numbers = []
    has_selectable_text = False
    
    # Get text blocks with position information
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    
    # Pattern to match numbers: integers, decimals, negative numbers, currency
    number_pattern = re.compile(r'-?[\d,]+\.?\d*')
    
    line_counter = 0
    
    for block in blocks:
        if block["type"] != 0:  # Skip non-text blocks (images, etc.)
            continue
            
        for line in block.get("lines", []):
            line_counter += 1
            
            for span in line.get("spans", []):
                text = span["text"]
                
                # Check if we have real selectable text
                if text.strip() and "(cid:" not in text.lower():
                    has_selectable_text = True
                
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
                        line_number=line_counter,
                        source="text"
                    ))
    
    return numbers, has_selectable_text


def extract_all_numbers(
    pdf_path: str, 
    use_ocr: bool = True, 
    user_type: str = "org"
) -> Tuple[List[NumberMatch], int]:
    """
    Extract all numbers from a PDF document, using OCR for non-selectable text.
    
    Args:
        pdf_path: Path to the PDF file
        use_ocr: Whether to use OCR for non-selectable pages
        user_type: "org" or "byok" for credential handling
    
    Returns:
        Tuple of (List of all NumberMatch objects, count of pages using OCR)
    """
    all_numbers = []
    ocr_pages_count = 0
    
    # Initialize OCR processor if needed
    ocr_processor = None
    if use_ocr:
        ocr_processor = GoogleVisionOCRProcessor(user_type)
    
    doc = fitz.open(pdf_path)
    
    # Also open with pdfplumber for image extraction (needed for OCR)
    pdfplumber_doc = None
    if use_ocr and ocr_processor and ocr_processor.is_available():
        try:
            pdfplumber_doc = pdfplumber.open(pdf_path)
        except Exception as e:
            print(f"⚠️ Could not open PDF with pdfplumber: {e}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"\n📄 Processing Page {page_num + 1}/{len(doc)}")
        
        # Try to extract numbers from selectable text first
        numbers, has_selectable_text = extract_numbers_from_page(page, page_num)
        
        # Check if we need OCR
        needs_ocr = False
        ocr_applied = False
        
        if not has_selectable_text:
            # No selectable text found - need full page OCR
            needs_ocr = True
            print(f"  ⚠️ No selectable text found on page {page_num + 1}")
        elif len(numbers) == 0:
            # Has text but no numbers - might be CID-encoded or images
            raw_text = page.get_text()
            if ocr_processor and ocr_processor.looks_like_cid_encoded(raw_text):
                needs_ocr = True
                print(f"  ⚠️ CID-encoded text detected on page {page_num + 1}")
        else:
            print(f"  ✅ Found {len(numbers)} numbers from selectable text")
        
        # Perform OCR if needed and available
        if needs_ocr and ocr_processor and ocr_processor.is_available() and pdfplumber_doc:
            print(f"  🔍 Performing full-page OCR on page {page_num + 1}...")
            
            try:
                plumber_page = pdfplumber_doc.pages[page_num]
                
                # Convert page to image for OCR
                page_image = plumber_page.to_image(resolution=300)
                img_bytes = io.BytesIO()
                page_image.save(img_bytes, format="PNG")
                
                # Get image dimensions for coordinate mapping
                page_width_pts = float(plumber_page.width)
                page_height_pts = float(plumber_page.height)
                scale_factor = 300 / 72.0
                img_width_px = int(page_width_pts * scale_factor)
                img_height_px = int(page_height_pts * scale_factor)
                
                # Use word-level bounding boxes for accurate positioning
                words_with_boxes = ocr_processor.ocr_image_with_boxes(
                    img_bytes.getvalue(),
                    img_width_px,
                    img_height_px
                )
                
                if words_with_boxes:
                    print(f"  ✅ OCR extracted {len(words_with_boxes)} words")
                    
                    # Create page rect for coordinate mapping
                    page_rect = fitz.Rect(0, 0, page_width_pts, page_height_pts)
                    
                    # Extract numbers with accurate bounding boxes
                    ocr_numbers = extract_numbers_from_ocr_words(
                        words_with_boxes,
                        page_num,
                        page_rect,
                        base_line=0
                    )
                    
                    if ocr_numbers:
                        print(f"  ✅ Found {len(ocr_numbers)} numbers from OCR")
                        # Replace any existing numbers with OCR results for this page
                        numbers = ocr_numbers
                        ocr_applied = True
                else:
                    print(f"  ⚠️ OCR returned no words")
                    
            except Exception as e:
                print(f"  ⚠️ OCR failed on page {page_num + 1}: {e}")
        
        # Also check for embedded images that might contain numbers
        elif has_selectable_text and pdfplumber_doc and ocr_processor and ocr_processor.is_available():
            try:
                plumber_page = pdfplumber_doc.pages[page_num]
                if plumber_page.images:
                    print(f"  🔍 Found {len(plumber_page.images)} embedded image(s), checking for numbers...")
                    
                    page_bbox = (0.0, 0.0, float(plumber_page.width), float(plumber_page.height))
                    
                    for img_idx, img in enumerate(plumber_page.images):
                        try:
                            raw_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                            safe_bbox = ocr_processor.clamp_bbox_to_page(raw_bbox, page_bbox)
                            
                            if not safe_bbox:
                                continue
                            
                            # Get the cropped image with known dimensions
                            cropped = plumber_page.crop(safe_bbox).to_image(resolution=300)
                            img_bytes = io.BytesIO()
                            cropped.save(img_bytes, format="PNG")
                            
                            # Get image dimensions for coordinate mapping
                            # pdfplumber's to_image at 300 DPI scales the region
                            region_width_pts = safe_bbox[2] - safe_bbox[0]
                            region_height_pts = safe_bbox[3] - safe_bbox[1]
                            # At 300 DPI, the image is scaled by 300/72 = 4.167x
                            scale_factor = 300 / 72.0
                            img_width_px = int(region_width_pts * scale_factor)
                            img_height_px = int(region_height_pts * scale_factor)
                            
                            # Use the new method that returns word-level bounding boxes
                            words_with_boxes = ocr_processor.ocr_image_with_boxes(
                                img_bytes.getvalue(),
                                img_width_px,
                                img_height_px
                            )
                            
                            if words_with_boxes:
                                # Create a rect for the image region on the PDF
                                img_rect = fitz.Rect(
                                    safe_bbox[0], safe_bbox[1], 
                                    safe_bbox[2], safe_bbox[3]
                                )
                                
                                # Extract numbers using accurate bounding boxes
                                img_numbers = extract_numbers_from_ocr_words(
                                    words_with_boxes,
                                    page_num,
                                    img_rect,
                                    base_line=len(numbers)
                                )
                                
                                if img_numbers:
                                    print(f"    ✅ Found {len(img_numbers)} numbers in image {img_idx + 1}")
                                    numbers.extend(img_numbers)
                                    ocr_applied = True
                                    
                        except Exception as e:
                            print(f"    ⚠️ Error processing image {img_idx + 1}: {e}")
                            
            except Exception as e:
                print(f"  ⚠️ Error checking embedded images: {e}")
        
        if ocr_applied:
            ocr_pages_count += 1
        
        all_numbers.extend(numbers)
    
    total_pages = len(doc)
    doc.close()
    if pdfplumber_doc:
        pdfplumber_doc.close()
    
    print(f"\n📊 OCR was applied on {ocr_pages_count} out of {total_pages} pages")
    
    return all_numbers, ocr_pages_count


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
            # Determine source - if either used OCR, mark as OCR
            source = "ocr" if (n1.source == "ocr" or n2.source == "ocr") else "text"
            
            differences.append(Difference(
                page=n1.page,
                line=n1.line_number,
                old_value=n1.value,
                new_value=n2.value,
                old_rect=n1.rect,
                new_rect=n2.rect,
                source=source
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
                new_rect=fitz.Rect(),
                source=n.source
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
                new_rect=n.rect,
                source=n.source
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
            # Use different color for OCR-detected differences (orange) vs text (red)
            color = (1, 0.5, 0) if diff.source == "ocr" else (1, 0, 0)
            
            # Highlight in first (old) PDF
            if diff.old_rect.is_valid and not diff.old_rect.is_empty:
                highlight_rect1 = fitz.Rect(
                    diff.old_rect.x0 - 2,
                    diff.old_rect.y0 - 2,
                    diff.old_rect.x1 + 2,
                    diff.old_rect.y1 + 2
                )
                new_page.draw_rect(highlight_rect1, color=color, width=2)
            
            # Highlight in second (new) PDF (offset to right side)
            if diff.new_rect.is_valid and not diff.new_rect.is_empty:
                highlight_rect2 = fitz.Rect(
                    diff.new_rect.x0 + width1 + 20 - 2,
                    diff.new_rect.y0 - 2,
                    diff.new_rect.x1 + width1 + 20 + 2,
                    diff.new_rect.y1 + 2
                )
                new_page.draw_rect(highlight_rect2, color=color, width=2)
        
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


def generate_report(
    differences: List[Difference], 
    output_pdf_path: str,
    ocr_pages_pdf1: int = 0,
    ocr_pages_pdf2: int = 0
) -> Dict:
    """
    Generate a JSON summary report of the comparison.
    
    Args:
        differences: List of differences found
        output_pdf_path: Path to the generated diff PDF
        ocr_pages_pdf1: Number of pages using OCR in PDF1
        ocr_pages_pdf2: Number of pages using OCR in PDF2
    
    Returns:
        Dictionary containing the comparison report
    """
    report = {
        "status": "OK" if len(differences) == 0 else "Fail",
        "total_differences": len(differences),
        "ocr_used": {
            "pdf1_ocr_pages": ocr_pages_pdf1,
            "pdf2_ocr_pages": ocr_pages_pdf2
        },
        "differences": [],
        "diff_pdf": output_pdf_path
    }
    
    for diff in differences:
        report["differences"].append({
            "page": diff.page + 1,  # Convert to 1-indexed for readability
            "line": diff.line,
            "old": diff.old_value,
            "new": diff.new_value,
            "source": diff.source  # "text" or "ocr"
        })
    
    return report


def main(
    pdf1_path: str, 
    pdf2_path: str, 
    output_path: Optional[str] = None,
    use_ocr: bool = True,
    user_type: str = "org"
) -> Dict:
    """
    Main entry point for PDF comparison.
    
    Args:
        pdf1_path: Path to first (old/baseline) PDF
        pdf2_path: Path to second (new) PDF
        output_path: Optional path for highlighted output PDF.
                    If None, auto-generates in the same folder as pdf1.
        use_ocr: Whether to use OCR for non-selectable text
        user_type: "org" or "byok" for credential handling
    
    Returns:
        Comparison report as a dictionary
    """
    # Set default output path - save in the same directory as the first PDF
    if output_path is None:
        input_dir = Path(pdf1_path).parent
        output_path = str(input_dir / "comparison_result.pdf")
    elif not os.path.isabs(output_path):
        # If relative path provided, make it relative to the input PDF's directory
        input_dir = Path(pdf1_path).parent
        output_path = str(input_dir / output_path)
    
    # Validate input files exist
    if not Path(pdf1_path).exists():
        raise FileNotFoundError(f"First PDF not found: {pdf1_path}")
    if not Path(pdf2_path).exists():
        raise FileNotFoundError(f"Second PDF not found: {pdf2_path}")
    
    print(f"Comparing PDFs:")
    print(f"  Old: {pdf1_path}")
    print(f"  New: {pdf2_path}")
    print(f"  OCR Enabled: {use_ocr}")
    print(f"  User Type: {user_type}")
    print()
    
    # Step 1: Extract numbers from both PDFs
    print("=" * 50)
    print("Extracting numbers from PDF 1...")
    print("=" * 50)
    numbers1, ocr_pages1 = extract_all_numbers(pdf1_path, use_ocr, user_type)
    print(f"\n  Total: Found {len(numbers1)} numbers")
    
    print()
    print("=" * 50)
    print("Extracting numbers from PDF 2...")
    print("=" * 50)
    numbers2, ocr_pages2 = extract_all_numbers(pdf2_path, use_ocr, user_type)
    print(f"\n  Total: Found {len(numbers2)} numbers")
    print()
    
    # Step 2: Compare numbers
    print("Comparing numbers...")
    differences = compare_numbers(numbers1, numbers2)
    print(f"  Found {len(differences)} differences")
    
    # Count OCR-sourced differences
    ocr_diffs = sum(1 for d in differences if d.source == "ocr")
    if ocr_diffs > 0:
        print(f"  ({ocr_diffs} differences detected via OCR)")
    print()
    
    # Step 3: Create highlighted output PDF
    print("Generating highlighted comparison PDF...")
    create_highlighted_pdf(pdf1_path, pdf2_path, differences, output_path)
    print()
    
    # Step 4: Generate report
    report = generate_report(differences, output_path, ocr_pages1, ocr_pages2)
    
    # Save JSON report to the same folder as output PDF
    json_report_path = str(Path(output_path).with_suffix('.json'))
    with open(json_report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"JSON report saved to: {json_report_path}")
    
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
        print("Usage: python pdf_compare22.py <pdf1> <pdf2> [output.pdf] [--user-type org|byok]")
        sys.exit(1)
    
    pdf1 = sys.argv[1]
    pdf2 = sys.argv[2]
    
    # Parse remaining arguments
    output = "highlighted_diff.pdf"
    user_type = "org"
    use_ocr = True
    
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--user-type" and i + 1 < len(sys.argv):
            user_type = sys.argv[i + 1]
            i += 2
        elif arg == "--no-ocr":
            use_ocr = False
            i += 1
        elif arg == "--ocr":
            use_ocr = True
            i += 1
        elif not arg.startswith("--"):
            output = arg
            i += 1
        else:
            i += 1
    
    try:
        result = main(pdf1, pdf2, output, use_ocr, user_type)
        
        # Exit with appropriate code
        sys.exit(0 if result["status"] == "OK" else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
