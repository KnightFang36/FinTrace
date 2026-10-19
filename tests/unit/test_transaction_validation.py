"""Financial boundary cases with handcrafted source values."""
from datetime import timezone
from decimal import Decimal
import unittest
from fintrace.validation.transactions import validate_transaction_fields


class TransactionValidationTests(unittest.TestCase):
    def row(self, **updates):
        fields = ["2022/09/01 00:00", "010", "000A", "001", "000B",
                  "0.00000001", "Bitcoin", "1.10", "US Dollar", "Wire"]
        for index, value in updates.items():
            fields[int(index)] = value
        return validate_transaction_fields(fields, timezone_policy="UTC", timestamp_precision="minute")

    def test_exact_amount_and_source_identifiers(self):
        result = self.row()
        self.assertEqual(result.record["amount_received"], Decimal("0.00000001"))
        self.assertEqual(result.record["sender_bank_id"], "010")
        self.assertEqual(result.record["sender_account_id"], "000A")
        self.assertEqual(result.record["occurred_at"].tzinfo, timezone.utc)

    def test_zero_negative_nonfinite_exponent_and_rounding_are_rejected(self):
        for value in ("0", "-1", "NaN", "Infinity", "1e3", "0.000000001", "9" * 31):
            with self.subTest(value=value):
                self.assertIsNone(self.row(**{"5": value}).record)

    def test_unmapped_channel_is_retained_as_warning(self):
        result = self.row(**{"9": "New Channel"})
        self.assertIsNotNone(result.record)
        self.assertEqual(result.issues[0]["severity"], "warning")

    def test_missing_or_whitespace_identifiers_are_not_repaired(self):
        for value in ("", " 010"):
            self.assertIsNone(self.row(**{"1": value}).record)

    def test_invalid_dates_and_source_precision_are_rejected(self):
        for value in ("2022/02/30 00:00", "2022/09/01 00:00:01", "not-a-date"):
            self.assertIsNone(self.row(**{"0": value}).record)

    def test_self_transfer_retains_exact_bank_identity(self):
        self.assertTrue(self.row(**{"3": "010", "4": "000A"}).record["is_self_transfer"])
        self.assertFalse(self.row(**{"3": "10", "4": "000A"}).record["is_self_transfer"])

    def test_dst_ambiguity_and_nonexistence_are_rejected(self):
        for timestamp in ("2022/11/06 01:30", "2022/03/13 02:30"):
            fields = [timestamp, "1", "A", "2", "B", "1", "USD", "1", "USD", "ACH"]
            with self.subTest(timestamp=timestamp):
                result = validate_transaction_fields(fields, timezone_policy="America/New_York",
                                                     timestamp_precision="minute")
                self.assertIsNone(result.record)

    def test_financial_function_does_not_accept_label_column(self):
        result = validate_transaction_fields(["x"] * 11, timezone_policy="UTC", timestamp_precision="minute")
        self.assertEqual(result.issues[0]["code"], "field_count")


class PackageStatusTests(unittest.TestCase):
    """A package whose modules are implemented must not advertise itself as pending."""

    PENDING_MARKERS = ("implementation pending", "no callable api", "planned fintrace")

    def test_package_docstrings_match_their_module_implementation_status(self):
        import importlib
        import pkgutil
        import fintrace

        def is_placeholder(module):
            source = (getattr(module, "__doc__", "") or "").lower()
            return any(marker in source for marker in self.PENDING_MARKERS)

        checked = 0
        for info in pkgutil.iter_modules(fintrace.__path__):
            package = importlib.import_module(f"fintrace.{info.name}")
            modules = [package]
            if hasattr(package, "__path__"):
                modules += [importlib.import_module(f"fintrace.{info.name}.{sub.name}")
                            for sub in pkgutil.iter_modules(package.__path__)]
            if all(is_placeholder(module) for module in modules):
                continue  # Genuinely pending: the banner is required here.
            checked += 1
            self.assertFalse(
                is_placeholder(package),
                f"fintrace.{info.name} has implemented modules but its docstring still says it is pending",
            )
        self.assertGreater(checked, 0)

    def test_validation_package_reexports_its_implemented_entry_point(self):
        import fintrace.validation as validation

        self.assertIs(validation.validate_transaction_fields, validate_transaction_fields)
        self.assertNotIn("implementation pending", (validation.__doc__ or "").lower())


def test_field_count_issue_reports_the_observed_source_width():
    """A narrowed field list must not hide the true source width from the operator."""
    from fintrace.validation.transactions import validate_transaction_fields
    # The adapter passes no financial fields for a widened row, but knows its real width.
    result = validate_transaction_fields(
        [], timezone_policy="UTC", timestamp_precision="minute", observed_field_count=13,
    )
    assert result.record is None
    assert result.issues[0]["code"] == "field_count"
    assert "source row has 13" in result.issues[0]["message"]


def test_field_count_issue_defaults_to_the_supplied_width():
    from fintrace.validation.transactions import validate_transaction_fields
    result = validate_transaction_fields(
        ["a"] * 9, timezone_policy="UTC", timestamp_precision="minute",
    )
    assert "source row has 9" in result.issues[0]["message"]
