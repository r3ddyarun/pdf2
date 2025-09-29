"""
PDF processing service using PyMuPDF for content detection and redaction
"""

import logging
import re
import time
import traceback
import io
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import fitz  # PyMuPDF
from app.models import RedactionBlock, RedactionReason
from app.config import settings

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF processing service for content detection and redaction"""
    
    def __init__(self):
        # Regular expressions for different content types
        self.patterns = {
            RedactionReason.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            RedactionReason.SSN: re.compile(
                r'\b\d{3}-?\d{2}-?\d{4}\b'
            ),
            RedactionReason.CREDIT_CARD: re.compile(
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
            ),
            RedactionReason.PHONE_NUMBER: re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            ),
            RedactionReason.DATE_OF_BIRTH: re.compile(
                r'\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b'
            ),
            RedactionReason.ACCOUNT_NUMBER: re.compile(
                r'\b\d{8,}\b'  # 8+ digit numbers (could be account numbers)
            )
        }
    
    def detect_content(self, text: str) -> List[Tuple[str, RedactionReason, float]]:
        """Detect sensitive content in text"""
        detected_items = []
        
        for reason, pattern in self.patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                # Calculate confidence based on pattern strength
                logger.info(f"Detected content: {match.group()}")
                confidence = self._calculate_confidence(reason, match.group())
                detected_items.append((match.group(), reason, confidence))
        
        return detected_items
    
    def _calculate_confidence(self, reason: RedactionReason, text: str) -> float:
        """Calculate confidence score for detected content"""
        base_confidence = {
            RedactionReason.EMAIL: 0.95,
            RedactionReason.SSN: 0.90,
            RedactionReason.CREDIT_CARD: 0.85,
            RedactionReason.PHONE_NUMBER: 0.80,
            RedactionReason.DATE_OF_BIRTH: 0.75,
            RedactionReason.ACCOUNT_NUMBER: 0.70,
            RedactionReason.ADDRESS: 0.60,
            RedactionReason.NAME: 0.50,
            RedactionReason.CUSTOM: 0.50
        }
        
        confidence = base_confidence.get(reason, 0.50)
        
        # Adjust confidence based on text characteristics
        if reason == RedactionReason.CREDIT_CARD:
            # Luhn algorithm check for credit cards
            if self._is_valid_credit_card(text.replace('-', '').replace(' ', '')):
                confidence += 0.10
        
        return min(confidence, 1.0)
    
    def _is_valid_credit_card(self, card_number: str) -> bool:
        """Validate credit card using Luhn algorithm"""
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(card_number) == 0
    
    def _validate_pdf_header(self, file_content: bytes) -> bool:
        """Validate PDF file header to detect corrupt files early"""
        try:
            # Check minimum file size
            if len(file_content) < 4:
                return False
            
            # Check PDF header signature
            pdf_header = file_content[:4]
            if pdf_header != b'%PDF':
                return False
            
            # Check for PDF version
            header_line = file_content[:20].decode('ascii', errors='ignore')
            if not any(version in header_line for version in ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '2.0']):
                return False
            
            return True
        except Exception as e:
            logger.warning(f"PDF header validation failed: {e}")
            return False

    def process_pdf(self, file_content: bytes, file_id: str) -> Dict[str, Any]:
        """Process PDF file for content detection and redaction.

        Note: This function performs CPU-bound PDF work only. It does NOT perform any
        external side effects like uploading to S3 or database writes. It returns the
        redaction blocks and the redacted PDF bytes to the caller.
        """
        start_time = time.time()
        doc = None
        
        try:
            # Validate PDF file before processing
            if not self._validate_pdf_header(file_content):
                raise ValueError("Invalid PDF file: Corrupted or unsupported file format")
            
            # Open PDF document with additional error handling
            try:
                doc = fitz.open(stream=file_content, filetype="pdf")
            except Exception as open_error:
                if "password" in str(open_error).lower():
                    raise ValueError("Password-protected PDF files are not supported")
                elif "corrupt" in str(open_error).lower() or "damaged" in str(open_error).lower():
                    raise ValueError("PDF file appears to be corrupted or damaged")
                else:
                    raise ValueError(f"Unable to open PDF file: {str(open_error)}")
            
            # Validate document structure
            if doc is None or doc.page_count == 0:
                raise ValueError("PDF file contains no pages or is empty")
            
            total_pages = len(doc)
            redaction_blocks = []
            
            logger.info(f"Processing PDF with {total_pages} pages")
            
            # Process each page with error handling
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    page_blocks = self._process_page(page, page_num)
                    redaction_blocks.extend(page_blocks)
                except Exception as page_error:
                    logger.warning(f"Error processing page {page_num + 1}: {page_error}")
                    # Continue processing other pages even if one fails
                    continue
            
            # Apply redactions
            self._apply_redactions(doc, redaction_blocks)
            
            # Save redacted document bytes
            redacted_content = doc.write()
            
            processing_time = time.time() - start_time
            
            # Create summary
            summary = self._create_summary(redaction_blocks)
            
            result = {
                'file_id': file_id,
                'total_pages': total_pages,
                'redaction_blocks': redaction_blocks,
                'processing_time_seconds': processing_time,
                'summary': summary,
                'created_at': datetime.utcnow(),
                'redacted_bytes': redacted_content,
            }
            
            logger.info(f"PDF processing completed in {processing_time:.2f} seconds")
            return result
            
        except ValueError as ve:
            # User-friendly error for corrupt/invalid files
            logger.error(f"PDF validation failed: {ve}", extra={'file_id': file_id})
            raise ve
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}", exc_info=True, extra={
                'file_id': file_id,
                'error_type': type(e).__name__,
                'error_details': str(e),
                'stack_trace': traceback.format_exc()
            })
            # Convert technical errors to user-friendly messages
            if "memory" in str(e).lower():
                raise ValueError("PDF file is too large or complex to process")
            elif "timeout" in str(e).lower():
                raise ValueError("PDF processing timed out - file may be too complex")
            else:
                raise ValueError(f"Unable to process PDF file: {str(e)}")
        finally:
            # Ensure document is properly closed
            if doc is not None:
                try:
                    doc.close()
                except Exception as close_error:
                    logger.warning(f"Error closing PDF document: {close_error}")
                    # Force cleanup by setting doc to None
                    doc = None
    
    def _process_page(self, page: fitz.Page, page_num: int) -> List[RedactionBlock]:
        """Process a single page for content detection"""
        blocks = []
        
        # Extract text with position information
        text_instances = page.get_text("dict")
        counter=0
        
        for block in text_instances["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        counter+=1
                        if text.strip():
                            detected_items = self.detect_content(text)
                            
                            for original_text, reason, confidence in detected_items:
                                # Get text rectangle
                                bbox = span["bbox"]
                                
                                # Create redaction block
                                redaction_block = RedactionBlock(
                                    page_number=page_num + 1,  # 1-indexed
                                    x=bbox[0],
                                    y=bbox[1],
                                    width=bbox[2] - bbox[0],
                                    height=bbox[3] - bbox[1],
                                    reason=reason,
                                    confidence=confidence,
                                    original_text=original_text
                                )
                                blocks.append(redaction_block)

        logger.info(f"Total blocks detected: {counter}")
        return blocks
    
    def _apply_redactions(self, doc: fitz.Document, blocks: List[RedactionBlock]) -> None:
        """Apply redaction blocks to the document"""
        if not blocks:
            return
            
        # Group blocks by page number to minimize page access
        blocks_by_page = {}
        for block in blocks:
            page_num = block.page_number - 1  # Convert to 0-indexed
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)
        
        # Apply redactions page by page
        for page_num in blocks_by_page:
            try:
                page = doc[page_num]
                page_blocks = blocks_by_page[page_num]
                
                # Add redaction annotations for this page
                for block in page_blocks:
                    rect = fitz.Rect(
                        block.x, block.y, 
                        block.x + block.width, 
                        block.y + block.height
                    )
                    
                    # Add redaction annotation
                    redact_annot = page.add_redact_annot(rect, fill=(0, 0, 0))
                    redact_annot.update()
                
                # Apply redactions for this page immediately
                page.apply_redactions()
                
                # Clear page reference to help with cleanup
                page = None
                
            except Exception as e:
                logger.warning(f"Error applying redactions to page {page_num + 1}: {e}")
                continue
    
    def _create_summary(self, blocks: List[RedactionBlock]) -> Dict[str, Any]:
        """Create summary of redaction results"""
        if not blocks:
            return {
                'total_redactions': 0,
                'redactions_by_reason': {},
                'pages_affected': 0,
                'confidence_scores': {}
            }
        
        # Count redactions by reason
        redactions_by_reason = {}
        confidence_scores = []
        pages_affected = set()
        
        for block in blocks:
            reason = block.reason.value
            redactions_by_reason[reason] = redactions_by_reason.get(reason, 0) + 1
            confidence_scores.append(block.confidence)
            pages_affected.add(block.page_number)
        
        # Calculate confidence statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        
        return {
            'total_redactions': len(blocks),
            'redactions_by_reason': redactions_by_reason,
            'pages_affected': len(pages_affected),
            'confidence_scores': {
                'average': avg_confidence,
                'minimum': min_confidence,
                'maximum': max_confidence
            }
        }


# Global PDF processor instance
pdf_processor = PDFProcessor()
