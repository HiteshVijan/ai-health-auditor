#!/usr/bin/env python3
"""
Synthetic Medical Bill Data Generator.

Generates realistic fake PDF invoices/bills with corresponding JSON labels
for training and testing document parsing pipelines.

Usage:
    python generate_synthetic_data.py --output-dir ./data/synthetic --num-samples 100
"""

import argparse
import json
import logging
import os
import random
import string
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from faker import Faker
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker with seed for reproducibility
fake = Faker()


@dataclass
class LineItem:
    """Represents a single line item on a medical bill."""
    description: str
    cpt_code: str
    quantity: int
    unit_price: float
    line_total: float


@dataclass
class BillLabels:
    """Ground truth labels for a generated bill."""
    document_id: str
    file_name: str
    total_amount: str
    invoice_number: str
    patient_name: str
    bill_date: str
    subtotal: str
    tax: str
    provider_name: str
    provider_address: str
    patient_address: str
    account_number: str
    line_items: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# Common medical procedures and their CPT codes
MEDICAL_PROCEDURES = [
    ("Office Visit - New Patient", "99201", 75.00, 150.00),
    ("Office Visit - Established Patient", "99213", 50.00, 125.00),
    ("Office Visit - Complex", "99215", 150.00, 250.00),
    ("Complete Blood Count (CBC)", "85025", 25.00, 75.00),
    ("Comprehensive Metabolic Panel", "80053", 50.00, 150.00),
    ("Lipid Panel", "80061", 40.00, 100.00),
    ("Urinalysis", "81003", 15.00, 45.00),
    ("Chest X-Ray", "71046", 100.00, 300.00),
    ("ECG/EKG", "93000", 75.00, 200.00),
    ("MRI - Brain", "70551", 500.00, 2000.00),
    ("CT Scan - Abdomen", "74150", 400.00, 1500.00),
    ("Ultrasound - Abdominal", "76700", 150.00, 400.00),
    ("Physical Therapy - Initial", "97001", 100.00, 200.00),
    ("Physical Therapy - Session", "97110", 50.00, 150.00),
    ("Vaccine Administration", "90471", 20.00, 50.00),
    ("Flu Vaccine", "90686", 25.00, 60.00),
    ("COVID-19 Test", "87635", 50.00, 150.00),
    ("Strep Test - Rapid", "87880", 20.00, 50.00),
    ("IV Infusion - Initial", "96365", 100.00, 300.00),
    ("Wound Care", "97597", 75.00, 200.00),
    ("Suture Removal", "99211", 30.00, 75.00),
    ("Injection - Therapeutic", "96372", 25.00, 75.00),
    ("Nebulizer Treatment", "94640", 30.00, 80.00),
    ("Spirometry", "94010", 50.00, 150.00),
    ("Allergy Testing", "95004", 100.00, 300.00),
]

# Healthcare provider templates
PROVIDER_TYPES = [
    "Medical Center",
    "Hospital",
    "Clinic",
    "Healthcare",
    "Medical Group",
    "Family Practice",
    "Urgent Care",
    "Specialty Center",
]


def generate_invoice_number() -> str:
    """Generate a realistic invoice number."""
    formats = [
        lambda: f"INV-{datetime.now().year}-{random.randint(10000, 99999)}",
        lambda: f"BILL-{random.randint(100000, 999999)}",
        lambda: f"{fake.random_uppercase_letter()}{fake.random_uppercase_letter()}-{random.randint(1000, 9999)}-{random.randint(100, 999)}",
        lambda: f"MED{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}",
        lambda: f"HC-{random.randint(10000000, 99999999)}",
    ]
    return random.choice(formats)()


def generate_account_number() -> str:
    """Generate a realistic account number."""
    formats = [
        lambda: f"ACC-{random.randint(100000, 999999)}",
        lambda: f"{random.randint(1000000000, 9999999999)}",
        lambda: f"PT{random.randint(10000, 99999)}{fake.random_uppercase_letter()}",
    ]
    return random.choice(formats)()


def generate_provider_info() -> Tuple[str, str, str, str, str]:
    """Generate realistic provider information."""
    city = fake.city()
    state = fake.state_abbr()
    provider_name = f"{city} {random.choice(PROVIDER_TYPES)}"
    address = fake.street_address()
    zip_code = fake.zipcode()
    phone = fake.phone_number()
    full_address = f"{address}\n{city}, {state} {zip_code}"
    return provider_name, full_address, phone, city, state


def generate_line_items(num_items: int = None) -> List[LineItem]:
    """Generate realistic line items for a medical bill."""
    if num_items is None:
        num_items = random.randint(1, 8)
    
    items = []
    selected_procedures = random.sample(MEDICAL_PROCEDURES, min(num_items, len(MEDICAL_PROCEDURES)))
    
    for desc, cpt, min_price, max_price in selected_procedures:
        quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
        unit_price = round(random.uniform(min_price, max_price), 2)
        line_total = round(quantity * unit_price, 2)
        
        items.append(LineItem(
            description=desc,
            cpt_code=cpt,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
        ))
    
    return items


def generate_bill_date() -> str:
    """Generate a realistic bill date within the past year."""
    days_ago = random.randint(1, 365)
    bill_date = datetime.now() - timedelta(days=days_ago)
    
    # Various date formats
    formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%d-%m-%Y",
    ]
    return bill_date.strftime(random.choice(formats))


def create_pdf_bill(
    output_path: str,
    labels: BillLabels,
    line_items: List[LineItem],
    include_logo: bool = True,
    add_noise: bool = False,
) -> None:
    """
    Create a PDF medical bill with realistic formatting.
    
    Args:
        output_path: Path to save the PDF file.
        labels: BillLabels containing all bill information.
        line_items: List of line items for the bill.
        include_logo: Whether to include a placeholder logo.
        add_noise: Whether to add visual noise for OCR testing.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='ProviderName',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2c5282'),
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='RightAlign',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name='CenterAlign',
        parent=styles['Normal'],
        alignment=TA_CENTER,
    ))
    
    story = []
    
    # Header with provider info
    header_data = [
        [
            Paragraph(labels.provider_name, styles['ProviderName']),
            Paragraph(f"<b>STATEMENT</b><br/><br/>Date: {labels.bill_date}", styles['RightAlign']),
        ],
        [
            Paragraph(labels.provider_address.replace('\n', '<br/>'), styles['Normal']),
            Paragraph(f"Invoice #: {labels.invoice_number}<br/>Account #: {labels.account_number}", styles['RightAlign']),
        ],
    ]
    
    header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Horizontal line
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e0')))
    story.append(Spacer(1, 0.2 * inch))
    
    # Patient information
    story.append(Paragraph("BILL TO:", styles['SectionHeader']))
    story.append(Paragraph(f"<b>{labels.patient_name}</b>", styles['Normal']))
    story.append(Paragraph(labels.patient_address.replace('\n', '<br/>'), styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    
    # Line items table
    story.append(Paragraph("SERVICES", styles['SectionHeader']))
    
    table_data = [
        ['Description', 'CPT Code', 'Qty', 'Unit Price', 'Amount'],
    ]
    
    for item in line_items:
        table_data.append([
            item.description,
            item.cpt_code,
            str(item.quantity),
            f"${item.unit_price:,.2f}",
            f"${item.line_total:,.2f}",
        ])
    
    items_table = Table(table_data, colWidths=[3 * inch, 0.8 * inch, 0.5 * inch, 1 * inch, 1 * inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        # Alignment
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f7fafc')) 
          for i in range(2, len(table_data), 2)],
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # Totals section
    subtotal = float(labels.subtotal.replace('$', '').replace(',', ''))
    tax = float(labels.tax.replace('$', '').replace(',', ''))
    total = float(labels.total_amount.replace('$', '').replace(',', ''))
    
    totals_data = [
        ['', '', '', 'Subtotal:', labels.subtotal],
        ['', '', '', 'Tax:', labels.tax],
        ['', '', '', 'TOTAL DUE:', labels.total_amount],
    ]
    
    totals_table = Table(totals_data, colWidths=[3 * inch, 0.8 * inch, 0.5 * inch, 1 * inch, 1 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -1), (-1, -1), 11),
        ('TEXTCOLOR', (3, -1), (-1, -1), colors.HexColor('#1a365d')),
        ('LINEABOVE', (3, -1), (-1, -1), 1, colors.HexColor('#2c5282')),
        ('TOPPADDING', (3, -1), (-1, -1), 8),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.4 * inch))
    
    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 0.1 * inch))
    
    footer_text = random.choice([
        "Payment is due within 30 days. Please include your account number with your payment.",
        "Thank you for choosing our services. Payment due upon receipt.",
        "For billing questions, please contact our billing department.",
        "Insurance claims should be submitted within 60 days.",
    ])
    story.append(Paragraph(footer_text, styles['CenterAlign']))
    
    # Payment options (randomly include)
    if random.random() > 0.5:
        story.append(Spacer(1, 0.2 * inch))
        payment_info = """
        <b>Payment Options:</b><br/>
        • Mail check to address above<br/>
        • Pay online at www.patientpay.example.com<br/>
        • Call (555) 123-4567 for credit card payment
        """
        story.append(Paragraph(payment_info, styles['Normal']))
    
    # Build PDF
    doc.build(story)


def generate_synthetic_bill(
    output_dir: str,
    document_id: str = None,
) -> BillLabels:
    """
    Generate a single synthetic medical bill with labels.
    
    Args:
        output_dir: Directory to save the PDF and JSON files.
        document_id: Optional document ID (generated if not provided).
    
    Returns:
        BillLabels containing the ground truth labels.
    """
    if document_id is None:
        document_id = str(uuid.uuid4())[:8]
    
    # Generate all bill components
    patient_name = fake.name()
    patient_address = f"{fake.street_address()}\n{fake.city()}, {fake.state_abbr()} {fake.zipcode()}"
    provider_name, provider_address, provider_phone, _, _ = generate_provider_info()
    
    invoice_number = generate_invoice_number()
    account_number = generate_account_number()
    bill_date = generate_bill_date()
    
    # Generate line items
    line_items = generate_line_items()
    
    # Calculate totals
    subtotal = sum(item.line_total for item in line_items)
    tax_rate = random.choice([0, 0, 0, 0.05, 0.06, 0.075, 0.08])  # Usually no tax on medical
    tax = round(subtotal * tax_rate, 2)
    total_amount = round(subtotal + tax, 2)
    
    # Create file name
    file_name = f"bill_{document_id}.pdf"
    pdf_path = os.path.join(output_dir, file_name)
    
    # Create labels
    labels = BillLabels(
        document_id=document_id,
        file_name=file_name,
        total_amount=f"${total_amount:,.2f}",
        invoice_number=invoice_number,
        patient_name=patient_name,
        bill_date=bill_date,
        subtotal=f"${subtotal:,.2f}",
        tax=f"${tax:,.2f}",
        provider_name=provider_name,
        provider_address=provider_address,
        patient_address=patient_address,
        account_number=account_number,
        line_items=[asdict(item) for item in line_items],
    )
    
    # Generate PDF
    create_pdf_bill(pdf_path, labels, line_items)
    
    # Save labels as JSON
    json_path = os.path.join(output_dir, f"bill_{document_id}.json")
    with open(json_path, 'w') as f:
        json.dump(labels.to_dict(), f, indent=2)
    
    logger.info(f"Generated: {file_name} with {len(line_items)} line items, total: ${total_amount:,.2f}")
    
    return labels


def generate_dataset(
    output_dir: str,
    num_samples: int = 100,
    seed: Optional[int] = None,
) -> List[BillLabels]:
    """
    Generate a dataset of synthetic medical bills.
    
    Args:
        output_dir: Directory to save generated files.
        num_samples: Number of samples to generate.
        seed: Random seed for reproducibility.
    
    Returns:
        List of BillLabels for all generated samples.
    """
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Generating {num_samples} synthetic bills in {output_dir}")
    
    all_labels = []
    for i in range(num_samples):
        document_id = f"{i+1:05d}"
        labels = generate_synthetic_bill(output_dir, document_id)
        all_labels.append(labels)
        
        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i + 1}/{num_samples} samples generated")
    
    # Save combined labels file
    combined_path = os.path.join(output_dir, "labels.json")
    with open(combined_path, 'w') as f:
        json.dump([label.to_dict() for label in all_labels], f, indent=2)
    
    logger.info(f"Dataset generation complete. Combined labels saved to {combined_path}")
    
    # Generate summary statistics
    summary = {
        "total_samples": num_samples,
        "total_amount_range": {
            "min": min(float(l.total_amount.replace('$', '').replace(',', '')) for l in all_labels),
            "max": max(float(l.total_amount.replace('$', '').replace(',', '')) for l in all_labels),
        },
        "avg_line_items": sum(len(l.line_items) for l in all_labels) / len(all_labels),
        "generated_at": datetime.now().isoformat(),
    }
    
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary statistics saved to {summary_path}")
    
    return all_labels


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic medical bill PDFs with JSON labels."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/synthetic",
        help="Directory to save generated files (default: ./data/synthetic)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=100,
        help="Number of samples to generate (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: None)",
    )
    
    args = parser.parse_args()
    
    generate_dataset(
        output_dir=args.output_dir,
        num_samples=args.num_samples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

