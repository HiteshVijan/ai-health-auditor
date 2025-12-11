"""
Unit tests for generate_synthetic_data.py.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path

import pytest

from scripts.generate_synthetic_data import (
    generate_invoice_number,
    generate_account_number,
    generate_provider_info,
    generate_line_items,
    generate_bill_date,
    generate_synthetic_bill,
    generate_dataset,
    BillLabels,
    LineItem,
)


class TestInvoiceNumberGeneration:
    """Tests for invoice number generation."""
    
    def test_generates_non_empty_string(self):
        """Invoice number should be a non-empty string."""
        invoice_number = generate_invoice_number()
        assert isinstance(invoice_number, str)
        assert len(invoice_number) > 0
    
    def test_generates_unique_numbers(self):
        """Should generate unique invoice numbers."""
        numbers = [generate_invoice_number() for _ in range(100)]
        # Allow some duplicates due to random chance, but most should be unique
        unique_count = len(set(numbers))
        assert unique_count > 90  # At least 90% unique


class TestAccountNumberGeneration:
    """Tests for account number generation."""
    
    def test_generates_non_empty_string(self):
        """Account number should be a non-empty string."""
        account_number = generate_account_number()
        assert isinstance(account_number, str)
        assert len(account_number) > 0


class TestProviderInfoGeneration:
    """Tests for provider info generation."""
    
    def test_returns_tuple_of_five_elements(self):
        """Should return a tuple with 5 elements."""
        result = generate_provider_info()
        assert isinstance(result, tuple)
        assert len(result) == 5
    
    def test_provider_name_contains_type(self):
        """Provider name should contain a provider type."""
        provider_name, _, _, _, _ = generate_provider_info()
        provider_types = ["Medical Center", "Hospital", "Clinic", "Healthcare", 
                        "Medical Group", "Family Practice", "Urgent Care", "Specialty Center"]
        assert any(ptype in provider_name for ptype in provider_types)


class TestLineItemsGeneration:
    """Tests for line items generation."""
    
    def test_generates_list_of_line_items(self):
        """Should return a list of LineItem objects."""
        items = generate_line_items()
        assert isinstance(items, list)
        assert len(items) > 0
        assert all(isinstance(item, LineItem) for item in items)
    
    def test_respects_num_items_parameter(self):
        """Should generate specified number of items."""
        items = generate_line_items(num_items=5)
        assert len(items) == 5
    
    def test_line_item_has_valid_fields(self):
        """Each line item should have valid fields."""
        items = generate_line_items(num_items=3)
        for item in items:
            assert isinstance(item.description, str)
            assert len(item.description) > 0
            assert isinstance(item.cpt_code, str)
            assert len(item.cpt_code) > 0
            assert isinstance(item.quantity, int)
            assert item.quantity > 0
            assert isinstance(item.unit_price, float)
            assert item.unit_price > 0
            assert isinstance(item.line_total, float)
            assert item.line_total > 0
    
    def test_line_total_equals_quantity_times_price(self):
        """Line total should equal quantity * unit_price."""
        items = generate_line_items(num_items=10)
        for item in items:
            expected = round(item.quantity * item.unit_price, 2)
            assert item.line_total == expected


class TestBillDateGeneration:
    """Tests for bill date generation."""
    
    def test_generates_non_empty_string(self):
        """Bill date should be a non-empty string."""
        bill_date = generate_bill_date()
        assert isinstance(bill_date, str)
        assert len(bill_date) > 0
    
    def test_generates_parseable_date(self):
        """Bill date should be in a recognized format."""
        from datetime import datetime
        
        bill_date = generate_bill_date()
        
        # Try common formats
        formats = ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%d-%m-%Y"]
        parsed = False
        
        for fmt in formats:
            try:
                datetime.strptime(bill_date, fmt)
                parsed = True
                break
            except ValueError:
                continue
        
        assert parsed, f"Could not parse date: {bill_date}"


class TestSyntheticBillGeneration:
    """Tests for single synthetic bill generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_generates_pdf_and_json(self, temp_dir):
        """Should generate both PDF and JSON files."""
        labels = generate_synthetic_bill(temp_dir, "test001")
        
        pdf_path = os.path.join(temp_dir, "bill_test001.pdf")
        json_path = os.path.join(temp_dir, "bill_test001.json")
        
        assert os.path.exists(pdf_path)
        assert os.path.exists(json_path)
    
    def test_returns_bill_labels(self, temp_dir):
        """Should return a BillLabels object."""
        labels = generate_synthetic_bill(temp_dir, "test002")
        assert isinstance(labels, BillLabels)
    
    def test_labels_have_required_fields(self, temp_dir):
        """Labels should contain all required fields."""
        labels = generate_synthetic_bill(temp_dir, "test003")
        
        assert labels.document_id == "test003"
        assert labels.file_name == "bill_test003.pdf"
        assert labels.total_amount.startswith("$")
        assert len(labels.invoice_number) > 0
        assert len(labels.patient_name) > 0
        assert len(labels.bill_date) > 0
        assert labels.subtotal.startswith("$")
        assert labels.tax.startswith("$")
        assert len(labels.provider_name) > 0
        assert len(labels.line_items) > 0
    
    def test_json_matches_labels(self, temp_dir):
        """JSON file should match returned labels."""
        labels = generate_synthetic_bill(temp_dir, "test004")
        
        json_path = os.path.join(temp_dir, "bill_test004.json")
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        assert json_data["document_id"] == labels.document_id
        assert json_data["total_amount"] == labels.total_amount
        assert json_data["invoice_number"] == labels.invoice_number
        assert json_data["patient_name"] == labels.patient_name
        assert json_data["bill_date"] == labels.bill_date
    
    def test_pdf_is_valid(self, temp_dir):
        """Generated PDF should be a valid PDF file."""
        labels = generate_synthetic_bill(temp_dir, "test005")
        
        pdf_path = os.path.join(temp_dir, "bill_test005.pdf")
        
        # Check PDF magic bytes
        with open(pdf_path, 'rb') as f:
            header = f.read(8)
        
        assert header.startswith(b'%PDF'), "File should start with PDF header"
    
    def test_total_equals_subtotal_plus_tax(self, temp_dir):
        """Total amount should equal subtotal + tax."""
        labels = generate_synthetic_bill(temp_dir, "test006")
        
        subtotal = float(labels.subtotal.replace('$', '').replace(',', ''))
        tax = float(labels.tax.replace('$', '').replace(',', ''))
        total = float(labels.total_amount.replace('$', '').replace(',', ''))
        
        expected_total = round(subtotal + tax, 2)
        assert total == expected_total


class TestDatasetGeneration:
    """Tests for dataset generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_generates_correct_number_of_samples(self, temp_dir):
        """Should generate the specified number of samples."""
        labels = generate_dataset(temp_dir, num_samples=3, seed=42)
        
        assert len(labels) == 3
        
        # Count PDF files
        pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
        assert len(pdf_files) == 3
    
    def test_generates_combined_labels_file(self, temp_dir):
        """Should generate a combined labels.json file."""
        generate_dataset(temp_dir, num_samples=3, seed=42)
        
        labels_path = os.path.join(temp_dir, "labels.json")
        assert os.path.exists(labels_path)
        
        with open(labels_path, 'r') as f:
            all_labels = json.load(f)
        
        assert len(all_labels) == 3
    
    def test_generates_summary_file(self, temp_dir):
        """Should generate a summary.json file."""
        generate_dataset(temp_dir, num_samples=3, seed=42)
        
        summary_path = os.path.join(temp_dir, "summary.json")
        assert os.path.exists(summary_path)
        
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        assert summary["total_samples"] == 3
        assert "total_amount_range" in summary
        assert "avg_line_items" in summary
    
    def test_seed_produces_reproducible_results(self, temp_dir):
        """Same seed should produce same results."""
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            labels1 = generate_dataset(temp_dir, num_samples=3, seed=12345)
            labels2 = generate_dataset(temp_dir2, num_samples=3, seed=12345)
            
            # Same seed should produce same patient names and amounts
            for l1, l2 in zip(labels1, labels2):
                assert l1.patient_name == l2.patient_name
                assert l1.total_amount == l2.total_amount
                assert l1.invoice_number == l2.invoice_number
        finally:
            shutil.rmtree(temp_dir2)


class TestGenerateThreeSamplePDFs:
    """
    Integration test: Generate 3 sample PDFs and verify their structure.
    This test demonstrates the full workflow.
    """
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_generate_three_sample_pdfs(self, temp_dir):
        """Generate 3 sample PDFs and verify all components."""
        # Generate 3 samples with fixed seed for reproducibility
        labels = generate_dataset(temp_dir, num_samples=3, seed=42)
        
        # Verify we got 3 labels
        assert len(labels) == 3
        
        # Verify each sample
        for i, label in enumerate(labels):
            document_id = f"{i+1:05d}"
            
            # Check PDF exists and is valid
            pdf_path = os.path.join(temp_dir, f"bill_{document_id}.pdf")
            assert os.path.exists(pdf_path), f"PDF for sample {i+1} should exist"
            assert os.path.getsize(pdf_path) > 0, f"PDF for sample {i+1} should not be empty"
            
            # Check JSON exists and is valid
            json_path = os.path.join(temp_dir, f"bill_{document_id}.json")
            assert os.path.exists(json_path), f"JSON for sample {i+1} should exist"
            
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Verify required fields
            required_fields = [
                'total_amount', 'invoice_number', 'patient_name', 'bill_date'
            ]
            for field in required_fields:
                assert field in json_data, f"Field '{field}' missing in sample {i+1}"
                assert json_data[field], f"Field '{field}' is empty in sample {i+1}"
            
            # Verify total_amount format
            assert json_data['total_amount'].startswith('$'), \
                f"total_amount should start with $ in sample {i+1}"
            
            # Verify line items exist
            assert 'line_items' in json_data, f"line_items missing in sample {i+1}"
            assert len(json_data['line_items']) > 0, \
                f"Should have at least 1 line item in sample {i+1}"
            
            # Log sample info
            print(f"\nSample {i+1}:")
            print(f"  File: {label.file_name}")
            print(f"  Patient: {label.patient_name}")
            print(f"  Invoice: {label.invoice_number}")
            print(f"  Date: {label.bill_date}")
            print(f"  Total: {label.total_amount}")
            print(f"  Line Items: {len(label.line_items)}")
        
        # Verify combined labels file
        combined_path = os.path.join(temp_dir, "labels.json")
        assert os.path.exists(combined_path)
        
        with open(combined_path, 'r') as f:
            all_labels = json.load(f)
        
        assert len(all_labels) == 3
        
        # Verify summary file
        summary_path = os.path.join(temp_dir, "summary.json")
        assert os.path.exists(summary_path)
        
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        assert summary['total_samples'] == 3
        assert summary['total_amount_range']['min'] > 0
        assert summary['total_amount_range']['max'] >= summary['total_amount_range']['min']
        assert summary['avg_line_items'] > 0
        
        print(f"\n✅ Successfully generated 3 sample PDFs")
        print(f"   Total amount range: ${summary['total_amount_range']['min']:.2f} - ${summary['total_amount_range']['max']:.2f}")
        print(f"   Average line items: {summary['avg_line_items']:.1f}")

