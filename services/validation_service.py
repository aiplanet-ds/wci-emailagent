"""
Validation Service for Price Change Emails
Detects missing required fields based on business rules
"""
from typing import Dict, List, Any, Optional


class ValidationService:
    """Validates price change email data and identifies missing fields"""

    # Field display names for user-friendly messages
    FIELD_LABELS = {
        "supplier_id": "Supplier ID",
        "supplier_name": "Supplier Name",
        "effective_date": "Effective Date",
        "product_id": "Product ID / Part Number",
        "new_price": "New Price",
        "currency": "Currency",
        "contact_email": "Contact Email",
        "contact_phone": "Contact Phone",
        "contact_person": "Contact Person",
        "reason": "Reason for Change",
        "old_price": "Old Price"
    }

    @staticmethod
    def _is_empty(value: Any) -> bool:
        """Check if a value is considered empty"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False

    @classmethod
    def validate_email_data(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate email data and identify missing fields

        Returns:
            {
                "is_valid": bool,
                "missing_fields": [{"field": str, "label": str, "section": str}],
                "needs_info": bool,
                "validation_errors": [str]
            }
        """
        missing_fields = []
        validation_errors = []

        # Extract sections
        supplier_info = email_data.get("supplier_info", {})
        price_change_summary = email_data.get("price_change_summary", {})
        affected_products = email_data.get("affected_products", [])

        # Rule 1: Always required - supplier_id, supplier_name, effective_date
        if cls._is_empty(supplier_info.get("supplier_id")):
            missing_fields.append({
                "field": "supplier_id",
                "label": cls.FIELD_LABELS["supplier_id"],
                "section": "supplier_info"
            })

        if cls._is_empty(supplier_info.get("supplier_name")):
            missing_fields.append({
                "field": "supplier_name",
                "label": cls.FIELD_LABELS["supplier_name"],
                "section": "supplier_info"
            })

        if cls._is_empty(price_change_summary.get("effective_date")):
            missing_fields.append({
                "field": "effective_date",
                "label": cls.FIELD_LABELS["effective_date"],
                "section": "price_change_summary"
            })

        # Rule 2: At least one contact field required
        has_contact_email = not cls._is_empty(supplier_info.get("contact_email"))
        has_contact_phone = not cls._is_empty(supplier_info.get("contact_phone"))

        if not has_contact_email and not has_contact_phone:
            missing_fields.append({
                "field": "contact_email",
                "label": cls.FIELD_LABELS["contact_email"],
                "section": "supplier_info"
            })
            missing_fields.append({
                "field": "contact_phone",
                "label": cls.FIELD_LABELS["contact_phone"],
                "section": "supplier_info"
            })
            validation_errors.append(
                "At least one contact method (email or phone) is required"
            )

        # Rule 3: If price change, validate product fields
        is_price_change = len(affected_products) > 0

        if is_price_change:
            for idx, product in enumerate(affected_products):
                product_prefix = f"product_{idx}"

                # Product ID (part number) required
                if cls._is_empty(product.get("product_id")):
                    missing_fields.append({
                        "field": f"{product_prefix}_product_id",
                        "label": f"{cls.FIELD_LABELS['product_id']} (Product {idx + 1})",
                        "section": "affected_products",
                        "product_index": idx
                    })

                # New price required
                if cls._is_empty(product.get("new_price")):
                    missing_fields.append({
                        "field": f"{product_prefix}_new_price",
                        "label": f"{cls.FIELD_LABELS['new_price']} (Product {idx + 1})",
                        "section": "affected_products",
                        "product_index": idx
                    })

                # Currency required
                if cls._is_empty(product.get("currency")):
                    missing_fields.append({
                        "field": f"{product_prefix}_currency",
                        "label": f"{cls.FIELD_LABELS['currency']} (Product {idx + 1})",
                        "section": "affected_products",
                        "product_index": idx
                    })

        # Rule 4: Optional but recommended fields
        recommended_missing = []

        if cls._is_empty(supplier_info.get("contact_person")):
            recommended_missing.append({
                "field": "contact_person",
                "label": cls.FIELD_LABELS["contact_person"],
                "section": "supplier_info",
                "severity": "recommended"
            })

        if is_price_change and cls._is_empty(price_change_summary.get("reason")):
            recommended_missing.append({
                "field": "reason",
                "label": cls.FIELD_LABELS["reason"],
                "section": "price_change_summary",
                "severity": "recommended"
            })

        # Combine required and recommended
        all_missing = missing_fields + recommended_missing

        return {
            "is_valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "recommended_fields": recommended_missing,
            "all_missing_fields": all_missing,
            "needs_info": len(all_missing) > 0,
            "validation_errors": validation_errors,
            "is_price_change": is_price_change
        }

    @classmethod
    def can_sync_to_epicor(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if email data is ready to sync to Epicor

        Returns:
            {
                "can_sync": bool,
                "blockers": [str],  # Critical issues that prevent sync
                "warnings": [str]   # Non-critical missing fields
            }
        """
        validation_result = cls.validate_email_data(email_data)
        blockers = []
        warnings = []

        # Critical blockers only
        supplier_info = email_data.get("supplier_info", {})
        price_change_summary = email_data.get("price_change_summary", {})
        affected_products = email_data.get("affected_products", [])

        # BLOCKER: Supplier ID is absolutely required
        if cls._is_empty(supplier_info.get("supplier_id")):
            blockers.append("Supplier ID is required for Epicor sync")

        # BLOCKER: Must have at least one product for price changes
        if len(affected_products) == 0:
            blockers.append("No affected products found")
        else:
            # BLOCKER: Each product must have minimum required data
            for idx, product in enumerate(affected_products):
                if cls._is_empty(product.get("product_id")):
                    blockers.append(f"Product {idx + 1} is missing product ID (part number)")

                if cls._is_empty(product.get("new_price")):
                    blockers.append(f"Product {idx + 1} is missing new price")

        # BLOCKER: Effective date is required
        if cls._is_empty(price_change_summary.get("effective_date")):
            blockers.append("Effective date is required for Epicor sync")

        # WARNINGS: Recommended but not critical fields
        if cls._is_empty(supplier_info.get("supplier_name")):
            warnings.append("Supplier name is missing (recommended)")

        has_contact_email = not cls._is_empty(supplier_info.get("contact_email"))
        has_contact_phone = not cls._is_empty(supplier_info.get("contact_phone"))
        if not has_contact_email and not has_contact_phone:
            warnings.append("No contact information available (email or phone recommended)")

        if cls._is_empty(supplier_info.get("contact_person")):
            warnings.append("Contact person is missing (recommended)")

        if cls._is_empty(price_change_summary.get("reason")):
            warnings.append("Reason for price change is missing (recommended)")

        # Check for currency on products
        for idx, product in enumerate(affected_products):
            if cls._is_empty(product.get("currency")):
                warnings.append(f"Product {idx + 1} is missing currency (recommended)")

        return {
            "can_sync": len(blockers) == 0,
            "blockers": blockers,
            "warnings": warnings
        }


# Global instance
validation_service = ValidationService()
