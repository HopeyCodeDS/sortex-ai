"""Tests for ValidationEngine — config-driven rule evaluation."""
import pytest

from src.domain.entities.document import DocumentType
from src.domain.entities.validation_result import ValidationStatus
from src.domain.services.validation_engine import ValidationEngine


class TestCMRValidation:
    """Legacy CMR validation path."""

    def test_valid_cmr(self, validation_engine):
        data = {
            "shipper_name": "Acme Corp",
            "consignee_name": "Beta Ltd",
            "date_of_consignment": "2024-01-15",
        }
        errors = validation_engine.validate(DocumentType.CMR, data)
        assert errors == []

    def test_cmr_missing_required_fields(self, validation_engine):
        data = {}
        errors = validation_engine.validate(DocumentType.CMR, data)
        field_names = {e.field for e in errors}
        assert "shipper_name" in field_names
        assert "consignee_name" in field_names
        assert "date_of_consignment" in field_names

    def test_cmr_non_string_date(self, validation_engine):
        data = {
            "shipper_name": "Acme",
            "consignee_name": "Beta",
            "date_of_consignment": 12345,
        }
        errors = validation_engine.validate(DocumentType.CMR, data)
        date_errors = [e for e in errors if e.field == "date_of_consignment"]
        assert len(date_errors) == 1
        assert "string" in date_errors[0].message.lower()


class TestInvoiceValidation:
    """Legacy Invoice validation path."""

    def test_valid_invoice(self, validation_engine):
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "total_amount": "1500.00",
        }
        errors = validation_engine.validate(DocumentType.INVOICE, data)
        assert errors == []

    def test_invoice_missing_fields(self, validation_engine):
        errors = validation_engine.validate(DocumentType.INVOICE, {})
        field_names = {e.field for e in errors}
        assert "invoice_number" in field_names
        assert "invoice_date" in field_names
        assert "total_amount" in field_names

    def test_invoice_valid_amount_with_currency(self, validation_engine):
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "total_amount": "€1,500.00",
        }
        errors = validation_engine.validate(DocumentType.INVOICE, data)
        assert errors == []

    def test_invoice_invalid_amount(self, validation_engine):
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "total_amount": "not-a-number",
        }
        errors = validation_engine.validate(DocumentType.INVOICE, data)
        amount_errors = [e for e in errors if e.field == "total_amount"]
        assert len(amount_errors) == 1


class TestDeliveryNoteValidation:
    """Legacy Delivery Note validation path."""

    def test_valid_delivery_note(self, validation_engine):
        data = {"delivery_date": "2024-03-15", "recipient_name": "Beta Ltd"}
        errors = validation_engine.validate(DocumentType.DELIVERY_NOTE, data)
        assert errors == []

    def test_delivery_note_missing_fields(self, validation_engine):
        errors = validation_engine.validate(DocumentType.DELIVERY_NOTE, {})
        field_names = {e.field for e in errors}
        assert "delivery_date" in field_names
        assert "recipient_name" in field_names


class TestConfigDrivenValidation:
    """Config-driven validation for newer document types."""

    def test_bill_of_lading_valid(self, validation_engine):
        data = {
            "bl_number": "BOL-123",
            "shipper_name": "Acme",
            "consignee_name": "Beta",
            "port_of_loading": "Rotterdam",
            "port_of_discharge": "Shanghai",
            "date_of_issue": "2024-01-15",
        }
        errors = validation_engine.validate(DocumentType.BILL_OF_LADING, data)
        assert errors == []

    def test_bill_of_lading_missing_fields(self, validation_engine):
        errors = validation_engine.validate(DocumentType.BILL_OF_LADING, {})
        field_names = {e.field for e in errors}
        assert "bl_number" in field_names
        assert "shipper_name" in field_names
        assert "port_of_loading" in field_names

    def test_packing_list_numeric_validation(self, validation_engine):
        data = {
            "packing_list_number": "PL-001",
            "shipper_name": "Acme",
            "date": "2024-01-15",
            "gross_weight": "not-a-number",
            "net_weight": "450",
        }
        errors = validation_engine.validate(DocumentType.PACKING_LIST, data)
        weight_errors = [e for e in errors if e.field == "gross_weight"]
        assert len(weight_errors) == 1
        assert "number" in weight_errors[0].message.lower()

    def test_packing_list_numeric_with_currency_symbols(self, validation_engine):
        data = {
            "packing_list_number": "PL-001",
            "shipper_name": "Acme",
            "gross_weight": "USD 500",
            "net_weight": "€450",
        }
        errors = validation_engine.validate(DocumentType.PACKING_LIST, data)
        # Currency symbols should be stripped before float parse
        numeric_errors = [e for e in errors if e.field in ("gross_weight", "net_weight")]
        assert len(numeric_errors) == 0

    def test_customs_declaration_required_fields(self, validation_engine):
        errors = validation_engine.validate(DocumentType.CUSTOMS_DECLARATION, {})
        field_names = {e.field for e in errors}
        assert "declaration_number" in field_names
        assert "goods_description" in field_names

    def test_freight_bill_valid(self, validation_engine):
        data = {
            "freight_bill_number": "FB-001",
            "shipper_name": "Acme",
            "origin": "Berlin",
            "destination": "Paris",
            "date_of_issue": "2024-01-15",
            "freight_charges": "1200.00",
            "total_amount": "1500.00",
        }
        errors = validation_engine.validate(DocumentType.FREIGHT_BILL, data)
        assert errors == []

    def test_date_field_non_string(self, validation_engine):
        data = {
            "bl_number": "BOL-123",
            "shipper_name": "Acme",
            "consignee_name": "Beta",
            "port_of_loading": "Rotterdam",
            "port_of_discharge": "Shanghai",
            "date_of_issue": 12345,  # not a string
        }
        errors = validation_engine.validate(DocumentType.BILL_OF_LADING, data)
        date_errors = [e for e in errors if e.field == "date_of_issue"]
        assert len(date_errors) == 1

    def test_unknown_type_no_validation(self, validation_engine):
        errors = validation_engine.validate(DocumentType.UNKNOWN, {})
        assert errors == []


class TestValidationStatus:
    """Test get_validation_status logic."""

    def test_no_errors_returns_passed(self, validation_engine):
        status = validation_engine.get_validation_status([])
        assert status == ValidationStatus.PASSED

    def test_errors_return_failed(self, validation_engine):
        from src.domain.entities.validation_result import ValidationError
        errors = [ValidationError(field="x", message="missing", severity="error")]
        status = validation_engine.get_validation_status(errors)
        assert status == ValidationStatus.FAILED

    def test_warnings_only_return_warning(self, validation_engine):
        from src.domain.entities.validation_result import ValidationError
        errors = [ValidationError(field="x", message="check value", severity="warning")]
        status = validation_engine.get_validation_status(errors)
        assert status == ValidationStatus.WARNING
