"""
Tests for PDF processing functionality
"""

import pytest
from app.services.pdf_processor import PDFProcessor
from app.models import RedactionReason


class TestPDFProcessor:
    """Test PDF processor functionality"""
    
    def setup_method(self):
        """Setup test instance"""
        self.processor = PDFProcessor()
    
    def test_email_detection(self):
        """Test email address detection"""
        text = "Contact us at john.doe@example.com or support@company.org"
        detected = self.processor.detect_content(text)
        
        assert len(detected) == 2
        assert any("john.doe@example.com" in item[0] and item[1] == RedactionReason.EMAIL for item in detected)
        assert any("support@company.org" in item[0] and item[1] == RedactionReason.EMAIL for item in detected)
    
    def test_ssn_detection(self):
        """Test SSN detection"""
        text = "SSN: 123-45-6789 or 123456789"
        detected = self.processor.detect_content(text)
        
        assert len(detected) >= 2
        assert any("123-45-6789" in item[0] and item[1] == RedactionReason.SSN for item in detected)
        assert any("123456789" in item[0] and item[1] == RedactionReason.SSN for item in detected)
    
    def test_credit_card_detection(self):
        """Test credit card detection"""
        text = "Card: 4111-1111-1111-1111 or 4111111111111111"
        detected = self.processor.detect_content(text)
        
        assert len(detected) >= 2
        assert any("4111-1111-1111-1111" in item[0] and item[1] == RedactionReason.CREDIT_CARD for item in detected)
        assert any("4111111111111111" in item[0] and item[1] == RedactionReason.CREDIT_CARD for item in detected)
    
    def test_phone_number_detection(self):
        """Test phone number detection"""
        text = "Call us at (555) 123-4567 or 555.123.4567"
        detected = self.processor.detect_content(text)
        
        assert len(detected) >= 2
        assert any("(555) 123-4567" in item[0] and item[1] == RedactionReason.PHONE_NUMBER for item in detected)
        assert any("555.123.4567" in item[0] and item[1] == RedactionReason.PHONE_NUMBER for item in detected)
    
    def test_date_of_birth_detection(self):
        """Test date of birth detection"""
        text = "DOB: 01/15/1990 or 12-31-1985"
        detected = self.processor.detect_content(text)
        
        assert len(detected) >= 2
        assert any("01/15/1990" in item[0] and item[1] == RedactionReason.DATE_OF_BIRTH for item in detected)
        assert any("12-31-1985" in item[0] and item[1] == RedactionReason.DATE_OF_BIRTH for item in detected)
    
    def test_account_number_detection(self):
        """Test account number detection"""
        text = "Account: 12345678 or 9876543210"
        detected = self.processor.detect_content(text)
        
        assert len(detected) >= 2
        assert any("12345678" in item[0] and item[1] == RedactionReason.ACCOUNT_NUMBER for item in detected)
        assert any("9876543210" in item[0] and item[1] == RedactionReason.ACCOUNT_NUMBER for item in detected)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # Test email confidence
        email_confidence = self.processor._calculate_confidence(RedactionReason.EMAIL, "test@example.com")
        assert email_confidence >= 0.9
        
        # Test SSN confidence
        ssn_confidence = self.processor._calculate_confidence(RedactionReason.SSN, "123-45-6789")
        assert ssn_confidence >= 0.8
        
        # Test credit card confidence
        cc_confidence = self.processor._calculate_confidence(RedactionReason.CREDIT_CARD, "4111111111111111")
        assert cc_confidence >= 0.8
    
    def test_luhn_algorithm(self):
        """Test Luhn algorithm for credit card validation"""
        # Valid credit card number (Visa test number)
        valid_cc = "4111111111111111"
        assert self.processor._is_valid_credit_card(valid_cc) == True
        
        # Invalid credit card number
        invalid_cc = "4111111111111112"
        assert self.processor._is_valid_credit_card(invalid_cc) == False
    
    def test_no_sensitive_content(self):
        """Test text with no sensitive content"""
        text = "This is a regular document with no sensitive information."
        detected = self.processor.detect_content(text)
        
        assert len(detected) == 0
    
    def test_mixed_content(self):
        """Test text with multiple types of sensitive content"""
        text = """
        Name: John Doe
        Email: john.doe@example.com
        SSN: 123-45-6789
        Phone: (555) 123-4567
        DOB: 01/15/1990
        Card: 4532-1234-5678-9012
        Account: 12345678
        """
        
        detected = self.processor.detect_content(text)
        
        # Should detect multiple types
        detected_reasons = set(item[1] for item in detected)
        expected_reasons = {
            RedactionReason.EMAIL,
            RedactionReason.SSN,
            RedactionReason.PHONE_NUMBER,
            RedactionReason.DATE_OF_BIRTH,
            RedactionReason.CREDIT_CARD,
            RedactionReason.ACCOUNT_NUMBER
        }
        
        assert len(detected_reasons & expected_reasons) >= 5
    
    def test_process_pdf_success(self):
        """Test successful PDF processing with real PDF file"""
        import os
        import tempfile
        
        # Create a simple test PDF with sensitive content
        test_pdf_content = self._create_test_pdf_with_sensitive_content()
        
        # Process PDF
        result = self.processor.process_pdf(test_pdf_content, "test-file-id")
        
        assert result["file_id"] == "test-file-id"
        assert result["total_pages"] >= 1
        assert isinstance(result["redacted_bytes"], bytes)
        assert len(result["redacted_bytes"]) > 0
        assert "processing_time_seconds" in result
        assert "summary" in result
        assert "redaction_blocks" in result
        assert result["processing_time_seconds"] > 0
    
    def test_process_pdf_with_sensitive_content(self):
        """Test PDF processing with actual sensitive content detection"""
        # Create a test PDF with known sensitive content
        test_pdf_content = self._create_test_pdf_with_sensitive_content()
        
        # Process PDF
        result = self.processor.process_pdf(test_pdf_content, "test-sensitive-file")
        
        # Verify basic structure
        assert result["file_id"] == "test-sensitive-file"
        assert result["total_pages"] >= 1
        assert isinstance(result["redacted_bytes"], bytes)
        assert len(result["redacted_bytes"]) > 0
        
        # Check that some redaction blocks were found (since we include sensitive content)
        assert len(result["redaction_blocks"]) > 0
        assert result["summary"]["total_redactions"] > 0
        assert result["summary"]["pages_affected"] > 0
        
        # Verify redaction reasons are present
        redaction_reasons = set(block.reason for block in result["redaction_blocks"])
        expected_reasons = {RedactionReason.EMAIL, RedactionReason.SSN, RedactionReason.PHONE_NUMBER}
        assert len(redaction_reasons & expected_reasons) > 0
    
    def test_process_pdf_with_no_sensitive_content(self):
        """Test PDF processing with no sensitive content"""
        # Create a test PDF with only normal text
        test_pdf_content = self._create_test_pdf_with_normal_content()
        
        # Process PDF
        result = self.processor.process_pdf(test_pdf_content, "test-normal-file")
        
        # Verify basic structure
        assert result["file_id"] == "test-normal-file"
        assert result["total_pages"] >= 1
        assert isinstance(result["redacted_bytes"], bytes)
        assert len(result["redacted_bytes"]) > 0
        
        # Check that no redaction blocks were found
        assert len(result["redaction_blocks"]) == 0
        assert result["summary"]["total_redactions"] == 0
        assert result["summary"]["pages_affected"] == 0
    
    def _create_test_pdf_with_sensitive_content(self) -> bytes:
        """Create a test PDF with sensitive content for testing"""
        import tempfile
        import os
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add content with sensitive information
            content = [
                "Test Document with Sensitive Information",
                "",
                "Contact Information:",
                "Email: john.doe@example.com",
                "Phone: (555) 123-4567",
                "SSN: 123-45-6789",
                "",
                "Additional Details:",
                "Another email: support@company.org",
                "Credit Card: 4111-1111-1111-1111",
                "Account Number: 1234567890"
            ]
            
            for line in content:
                story.append(Paragraph(line, styles['Normal']))
            
            doc.build(story)
            
            # Read the PDF content
            with open(tmp_file.name, 'rb') as f:
                pdf_content = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
            
            return pdf_content
    
    def _create_test_pdf_with_normal_content(self) -> bytes:
        """Create a test PDF with normal content for testing"""
        import tempfile
        import os
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add normal content without sensitive information
            content = [
                "Test Document with Normal Content",
                "",
                "This is a regular document with no sensitive information.",
                "It contains only normal text content for testing purposes.",
                "",
                "Document Details:",
                "Type: Test Document",
                "Purpose: Testing PDF processing",
                "Content: Regular text only"
            ]
            
            for line in content:
                story.append(Paragraph(line, styles['Normal']))
            
            doc.build(story)
            
            # Read the PDF content
            with open(tmp_file.name, 'rb') as f:
                pdf_content = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
            
            return pdf_content
    
    def test_create_summary_empty_blocks(self):
        """Test summary creation with no redaction blocks"""
        summary = self.processor._create_summary([])
        
        assert summary["total_redactions"] == 0
        assert summary["redactions_by_reason"] == {}
        assert summary["pages_affected"] == 0
        assert summary["confidence_scores"] == {}
    
    def test_create_summary_with_blocks(self):
        """Test summary creation with redaction blocks"""
        from app.models import RedactionBlock
        
        blocks = [
            RedactionBlock(
                page_number=1,
                x=100, y=200, width=50, height=20,
                reason=RedactionReason.EMAIL,
                confidence=0.95,
                original_text="test@example.com"
            ),
            RedactionBlock(
                page_number=1,
                x=150, y=250, width=50, height=20,
                reason=RedactionReason.SSN,
                confidence=0.90,
                original_text="123-45-6789"
            ),
            RedactionBlock(
                page_number=2,
                x=100, y=300, width=50, height=20,
                reason=RedactionReason.EMAIL,
                confidence=0.85,
                original_text="another@example.com"
            )
        ]
        
        summary = self.processor._create_summary(blocks)
        
        assert summary["total_redactions"] == 3
        assert summary["redactions_by_reason"]["email"] == 2
        assert summary["redactions_by_reason"]["ssn"] == 1
        assert summary["pages_affected"] == 2
        assert summary["confidence_scores"]["average"] == (0.95 + 0.90 + 0.85) / 3
        assert summary["confidence_scores"]["minimum"] == 0.85
        assert summary["confidence_scores"]["maximum"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__])
