#!/usr/bin/env python3
"""
PDF Test File Generator

This script generates various types of PDF files for testing the PDF redaction service:
- Normal text files
- Files with sensitive data (emails, SSNs, credit cards, phone numbers)
- Corrupt files
- Edge cases

Usage:
    python generate_test_pdfs.py [--output-dir OUTPUT_DIR] [--count COUNT]
"""

import os
import sys
import argparse
import random
import string
from datetime import datetime, date
from typing import List, Optional
import tempfile

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
except ImportError:
    print("Error: reportlab is required. Install it with: pip install reportlab")
    sys.exit(1)


class PDFTestGenerator:
    """Generate various types of test PDF files"""
    
    def __init__(self, output_dir: str = "test_pdfs"):
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()
        self._create_output_dir()
        
        # Sample data for generating content
        self.names = [
            "John Smith", "Jane Doe", "Michael Johnson", "Sarah Wilson",
            "David Brown", "Lisa Davis", "Robert Miller", "Jennifer Garcia",
            "William Martinez", "Linda Rodriguez", "James Anderson", "Patricia Taylor"
        ]
        
        self.companies = [
            "Acme Corporation", "Global Tech Solutions", "Innovation Labs",
            "Data Dynamics", "Cloud Systems Inc", "Digital Solutions LLC",
            "Enterprise Services", "Tech Innovations", "Advanced Systems",
            "Smart Technologies", "Future Solutions", "NextGen Systems"
        ]
        
        self.addresses = [
            "123 Main Street, New York, NY 10001",
            "456 Oak Avenue, Los Angeles, CA 90210",
            "789 Pine Road, Chicago, IL 60601",
            "321 Elm Street, Houston, TX 77001",
            "654 Maple Drive, Phoenix, AZ 85001"
        ]
        
        self.email_domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com", "test.org"]
        
        # Sample sensitive data patterns
        self.ssn_patterns = [
            "123-45-6789", "987-65-4321", "555-12-3456", "111-22-3333",
            "999-88-7777", "123456789", "987654321", "555123456"
        ]
        
        self.credit_card_patterns = [
            "4111-1111-1111-1111", "5555-5555-5555-4444", "4000-0000-0000-0002",
            "3782-822463-10005", "6011-1111-1111-1117", "4111111111111111",
            "5555555555554444", "4000000000000002"
        ]
        
        self.phone_patterns = [
            "(555) 123-4567", "555-123-4567", "555.123.4567", "5551234567",
            "(212) 555-0123", "212-555-0123", "212.555.0123", "2125550123",
            "+1-555-123-4567", "1-555-123-4567"
        ]
        
        self.bank_accounts = [
            "1234567890", "9876543210", "5555123456", "1111222233",
            "9999888877", "1234-5678-9012", "9876-5432-1098"
        ]

    def _create_output_dir(self):
        """Create output directory if it doesn't exist"""
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"📁 Output directory: {os.path.abspath(self.output_dir)}")

    def _generate_random_text(self, min_words: int = 50, max_words: int = 200) -> str:
        """Generate random text content"""
        words = [
            "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing",
            "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore",
            "et", "dolore", "magna", "aliqua", "enim", "ad", "minim", "veniam",
            "quis", "nostrud", "exercitation", "ullamco", "laboris", "nisi",
            "aliquip", "ex", "ea", "commodo", "consequat", "duis", "aute",
            "irure", "reprehenderit", "voluptate", "velit", "esse", "cillum",
            "fugiat", "nulla", "pariatur", "excepteur", "sint", "occaecat",
            "cupidatat", "non", "proident", "sunt", "culpa", "qui", "officia",
            "deserunt", "mollit", "anim", "id", "est", "laborum"
        ]
        
        word_count = random.randint(min_words, max_words)
        text = " ".join(random.choices(words, k=word_count))
        return text.capitalize()

    def _generate_email(self, name: str = None) -> str:
        """Generate a random email address"""
        if not name:
            name = random.choice(self.names).lower().replace(" ", ".")
        domain = random.choice(self.email_domains)
        return f"{name}@{domain}"

    def _generate_sensitive_content(self) -> List[str]:
        """Generate content with sensitive data"""
        content = []
        
        # Add some normal text first
        content.append(self._generate_random_text(20, 50))
        
        # Add sensitive data
        content.append(f"Contact Information:")
        content.append(f"Email: {self._generate_email()}")
        content.append(f"Phone: {random.choice(self.phone_patterns)}")
        content.append(f"SSN: {random.choice(self.ssn_patterns)}")
        
        content.append(f"\\nFinancial Information:")
        content.append(f"Credit Card: {random.choice(self.credit_card_patterns)}")
        content.append(f"Bank Account: {random.choice(self.bank_accounts)}")
        
        # Add more normal text
        content.append(f"\\n{self._generate_random_text(30, 80)}")
        
        # Add more sensitive data
        content.append(f"\\nAdditional Details:")
        content.append(f"Emergency Contact: {random.choice(self.names)}")
        content.append(f"Phone: {random.choice(self.phone_patterns)}")
        content.append(f"Email: {self._generate_email()}")
        
        return content

    def _generate_business_document(self) -> List[str]:
        """Generate business document content"""
        content = []
        
        company = random.choice(self.companies)
        employee = random.choice(self.names)
        
        content.append(f"EMPLOYEE CONFIDENTIALITY AGREEMENT")
        content.append(f"Company: {company}")
        content.append(f"Employee: {employee}")
        content.append(f"Date: {date.today().strftime('%B %d, %Y')}")
        
        content.append(f"\\nEmployee Information:")
        content.append(f"Full Name: {employee}")
        content.append(f"Employee ID: EMP{random.randint(10000, 99999)}")
        content.append(f"SSN: {random.choice(self.ssn_patterns)}")
        content.append(f"Email: {self._generate_email(employee.lower().replace(' ', '.'))}")
        content.append(f"Phone: {random.choice(self.phone_patterns)}")
        content.append(f"Address: {random.choice(self.addresses)}")
        
        content.append(f"\\nBanking Information:")
        content.append(f"Account Number: {random.choice(self.bank_accounts)}")
        content.append(f"Routing Number: {random.randint(100000000, 999999999)}")
        
        content.append(f"\\nAgreement Terms:")
        content.append(self._generate_random_text(100, 200))
        
        return content

    def generate_normal_pdf(self, filename: str = None) -> str:
        """Generate a normal PDF with regular text content"""
        if not filename:
            filename = f"normal_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Sample Document", title_style))
        story.append(Spacer(1, 20))
        
        # Content
        content = self._generate_random_text(200, 400)
        story.append(Paragraph(content, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add some structured content
        story.append(Paragraph("Document Details", self.styles['Heading2']))
        
        data = [
            ['Document Type:', 'Standard Business Document'],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Page Count:', '1'],
            ['Content Type:', 'Regular Text']
        ]
        
        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        doc.build(story)
        print(f"✅ Generated normal PDF: {filename}")
        return filepath

    def generate_sensitive_pdf(self, filename: str = None) -> str:
        """Generate a PDF with sensitive information"""
        if not filename:
            filename = f"sensitive_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("CONFIDENTIAL - SENSITIVE DATA", title_style))
        story.append(Spacer(1, 20))
        
        # Sensitive content
        content = self._generate_sensitive_content()
        for paragraph in content:
            if paragraph.startswith("\\n"):
                story.append(Spacer(1, 12))
                story.append(Paragraph(paragraph[2:], self.styles['Normal']))
            else:
                story.append(Paragraph(paragraph, self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Business document section
        story.append(Paragraph("Employee Information", self.styles['Heading2']))
        business_content = self._generate_business_document()
        for paragraph in business_content:
            if paragraph.startswith("\\n"):
                story.append(Spacer(1, 12))
                story.append(Paragraph(paragraph[2:], self.styles['Normal']))
            else:
                story.append(Paragraph(paragraph, self.styles['Normal']))
        
        doc.build(story)
        print(f"🔒 Generated sensitive PDF: {filename}")
        return filepath

    def generate_business_pdf(self, filename: str = None) -> str:
        """Generate a business document PDF"""
        if not filename:
            filename = f"business_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # Header
        header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        company = random.choice(self.companies)
        story.append(Paragraph(f"{company}", header_style))
        story.append(Paragraph("Internal Document", self.styles['Heading3']))
        story.append(Spacer(1, 30))
        
        # Business content
        business_content = self._generate_business_document()
        for paragraph in business_content:
            if paragraph.startswith("\\n"):
                story.append(Spacer(1, 12))
                story.append(Paragraph(paragraph[2:], self.styles['Normal']))
            else:
                story.append(Paragraph(paragraph, self.styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
        
        doc.build(story)
        print(f"🏢 Generated business PDF: {filename}")
        return filepath

    def generate_corrupt_pdf(self, filename: str = None) -> str:
        """Generate a corrupt PDF file"""
        if not filename:
            filename = f"corrupt_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # First create a normal PDF
        normal_pdf = self.generate_normal_pdf("temp_normal.pdf")
        
        # Read the normal PDF and corrupt it
        with open(normal_pdf, 'rb') as f:
            content = f.read()
        
        # Corrupt the PDF by modifying bytes
        content_array = bytearray(content)
        
        # Randomly corrupt some bytes
        corruption_points = random.sample(range(len(content_array)), min(50, len(content_array) // 10))
        for pos in corruption_points:
            content_array[pos] = random.randint(0, 255)
        
        # Write corrupted content
        with open(filepath, 'wb') as f:
            f.write(content_array)
        
        # Clean up temp file
        os.remove(normal_pdf)
        
        print(f"💥 Generated corrupt PDF: {filename}")
        return filepath

    def generate_empty_pdf(self, filename: str = None) -> str:
        """Generate an empty PDF file"""
        if not filename:
            filename = f"empty_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Just a title
        story.append(Paragraph("Empty Document", self.styles['Heading1']))
        story.append(Paragraph("This document contains minimal content.", self.styles['Normal']))
        
        doc.build(story)
        print(f"📄 Generated empty PDF: {filename}")
        return filepath

    def generate_large_pdf(self, filename: str = None) -> str:
        """Generate a large PDF with lots of content"""
        if not filename:
            filename = f"large_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Title
        story.append(Paragraph("Large Document", self.styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Generate multiple pages of content
        for page_num in range(10):  # 10 pages
            story.append(Paragraph(f"Page {page_num + 1}", self.styles['Heading2']))
            story.append(Paragraph(self._generate_random_text(300, 500), self.styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Add some structured content every few pages
            if page_num % 3 == 0:
                data = [
                    ['Item', 'Description', 'Value'],
                    ['Item 1', 'Description of item 1', f'${random.randint(100, 1000)}'],
                    ['Item 2', 'Description of item 2', f'${random.randint(100, 1000)}'],
                    ['Item 3', 'Description of item 3', f'${random.randint(100, 1000)}']
                ]
                
                table = Table(data, colWidths=[1.5*inch, 3*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
        
        doc.build(story)
        print(f"📚 Generated large PDF: {filename}")
        return filepath

    def generate_all_types(self, count: int = 1) -> List[str]:
        """Generate all types of test PDFs"""
        generated_files = []
        
        generators = [
            ("normal", self.generate_normal_pdf),
            ("sensitive", self.generate_sensitive_pdf),
            ("business", self.generate_business_pdf),
            ("corrupt", self.generate_corrupt_pdf),
            ("empty", self.generate_empty_pdf),
            ("large", self.generate_large_pdf)
        ]
        
        for i in range(count):
            for pdf_type, generator in generators:
                filename = f"{pdf_type}_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                filepath = generator(filename)
                generated_files.append(filepath)
        
        return generated_files


def main():
    """Main function to run the PDF generator"""
    parser = argparse.ArgumentParser(description="Generate test PDF files for PDF redaction testing")
    parser.add_argument("--output-dir", "-o", default="test_pdfs", 
                       help="Output directory for generated PDFs (default: test_pdfs)")
    parser.add_argument("--count", "-c", type=int, default=1,
                       help="Number of each type of PDF to generate (default: 1)")
    parser.add_argument("--type", "-t", choices=["normal", "sensitive", "business", "corrupt", "empty", "large", "all"],
                       default="all", help="Type of PDF to generate (default: all)")
    
    args = parser.parse_args()
    
    print("🔧 PDF Test File Generator")
    print("=" * 50)
    
    generator = PDFTestGenerator(args.output_dir)
    
    if args.type == "all":
        print(f"Generating {args.count} of each type...")
        generated_files = generator.generate_all_types(args.count)
    else:
        print(f"Generating {args.count} {args.type} PDF(s)...")
        generated_files = []
        
        for i in range(args.count):
            filename = f"{args.type}_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            if args.type == "normal":
                filepath = generator.generate_normal_pdf(filename)
            elif args.type == "sensitive":
                filepath = generator.generate_sensitive_pdf(filename)
            elif args.type == "business":
                filepath = generator.generate_business_pdf(filename)
            elif args.type == "corrupt":
                filepath = generator.generate_corrupt_pdf(filename)
            elif args.type == "empty":
                filepath = generator.generate_empty_pdf(filename)
            elif args.type == "large":
                filepath = generator.generate_large_pdf(filename)
            
            generated_files.append(filepath)
    
    print("\n" + "=" * 50)
    print(f"✅ Generated {len(generated_files)} test PDF files")
    print(f"📁 Location: {os.path.abspath(args.output_dir)}")
    
    # Show file sizes
    total_size = 0
    for filepath in generated_files:
        size = os.path.getsize(filepath)
        total_size += size
        print(f"   📄 {os.path.basename(filepath)}: {size:,} bytes")
    
    print(f"📊 Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    
    print("\n🎯 Usage:")
    print("   • Normal PDFs: Test basic functionality")
    print("   • Sensitive PDFs: Test redaction accuracy")
    print("   • Business PDFs: Test structured document processing")
    print("   • Corrupt PDFs: Test error handling")
    print("   • Empty PDFs: Test edge cases")
    print("   • Large PDFs: Test performance and memory usage")


if __name__ == "__main__":
    main()
