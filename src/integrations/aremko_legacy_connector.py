"""
Aremko Legacy Connector
Reads and normalizes data from legacy CSV files
"""
import os
import csv
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.utils.logger import logger


class AremkoLegacyConnector:
    """
    Connector for Aremko's legacy data stored in CSV files
    Reads historical customer data from old booking system
    """

    def __init__(self, tenant: str = "aremko"):
        """
        Initialize Aremko Legacy connector

        Args:
            tenant: Tenant identifier (default: aremko)
        """
        self.tenant = tenant

        # Get path to legacy files from environment
        tenant_suffix = f"_{tenant.upper()}" if tenant != "aremko" else ""
        self.legacy_data_path = os.getenv(
            f"AREMKO_LEGACY_DATA_PATH{tenant_suffix}",
            os.getenv("AREMKO_LEGACY_DATA_PATH", "/path/to/legacy/data")
        )

        self.customers_file = os.path.join(
            self.legacy_data_path,
            "Clientes-2024-06-23-16-31-48.csv"
        )

        logger.info(f"AremkoLegacyConnector initialized for tenant: {tenant}")
        logger.info(f"Legacy data path: {self.legacy_data_path}")

    # ============================================
    # CSV Parsing
    # ============================================

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string from CSV (multiple formats)

        Args:
            date_str: Date string from CSV

        Returns:
            datetime object or None
        """
        if not date_str or date_str.strip() == '':
            return None

        # Try different date formats
        formats = [
            "%m/%d/%Y %H:%M",      # 2/25/2020 18:05
            "%Y-%m-%d %H:%M:%S",   # 2020-02-25 18:05:00
            "%Y-%m-%d",            # 2020-02-25
            "%m/%d/%Y",            # 02/25/2020
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _extract_name_from_client_field(self, client_field: str) -> str:
        """
        Extract clean name from 'Client' field
        Format: "Name PhoneNumber" -> "Name"

        Args:
            client_field: Client field value

        Returns:
            Clean name
        """
        if not client_field or client_field.strip() == '':
            return ""

        # Remove phone number at the end (9 digits)
        # Example: "sonia silva 984280796" -> "sonia silva"
        cleaned = re.sub(r'\s*\d{9}\s*$', '', client_field)
        return cleaned.strip().title()  # Capitalize properly

    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize Chilean phone number

        Args:
            phone: Phone number string

        Returns:
            Normalized phone number or None
        """
        if not phone or phone.strip() == '':
            return None

        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        # Chilean mobile numbers are 9 digits starting with 9
        if len(digits) == 9 and digits[0] == '9':
            return f"+569{digits[1:]}"  # Format: +569XXXXXXXX

        # If it's already 11 digits with country code
        if len(digits) == 11 and digits[:3] == '569':
            return f"+{digits}"

        # Invalid format
        logger.warning(f"Could not normalize phone: {phone}")
        return None

    def _normalize_email(self, email: str) -> Optional[str]:
        """
        Normalize and validate email

        Args:
            email: Email string

        Returns:
            Normalized email or None
        """
        if not email or email.strip() == '':
            return None

        email = email.strip().lower()

        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            return None

        return email

    def _parse_location(self, direccion: str) -> Dict[str, str]:
        """
        Parse location from 'Direccion' field
        Format: "City, Region" or "City"

        Args:
            direccion: Address/location string

        Returns:
            Dictionary with ciudad and region
        """
        if not direccion or direccion.strip() == '':
            return {"ciudad": None, "region": None}

        parts = [p.strip() for p in direccion.split(',')]

        if len(parts) >= 2:
            return {
                "ciudad": parts[0],
                "region": parts[1]
            }
        else:
            return {
                "ciudad": parts[0] if parts else None,
                "region": None
            }

    # ============================================
    # Data Fetching
    # ============================================

    async def fetch_legacy_customers(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all customers from legacy CSV file

        Args:
            limit: Optional limit on number of records

        Returns:
            List of normalized customer dictionaries
        """
        if not os.path.exists(self.customers_file):
            logger.error(f"Legacy customers file not found: {self.customers_file}")
            return []

        customers = []

        try:
            with open(self.customers_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for idx, row in enumerate(reader):
                    if limit and idx >= limit:
                        break

                    # Parse location
                    location = self._parse_location(row.get('Direccion', ''))

                    # Extract name from Client field
                    nombre = self._extract_name_from_client_field(row.get('Client', ''))

                    # If name is empty, skip this record
                    if not nombre:
                        continue

                    # Normalize phone
                    telefono = self._normalize_phone(row.get('Telefono', ''))

                    # Normalize email
                    email = self._normalize_email(row.get('Email', ''))

                    # Parse created date
                    created_on = self._parse_date(row.get('Created On', ''))

                    customer = {
                        "legacy_id": row.get('Auto Increment', ''),
                        "record_id": row.get('Record ID', ''),
                        "created_on": created_on,
                        "nombre": nombre,
                        "email": email,
                        "telefono": telefono,
                        "documento_identidad": row.get('Documento Identidad', '').strip() or None,
                        "ciudad": location['ciudad'],
                        "region": location['region'],
                        "pais": "Chile",  # Assume Chile for all legacy records
                        "voucher": row.get('voucher', '').strip() or None,
                    }

                    customers.append(customer)

            logger.info(f"Parsed {len(customers)} customers from legacy CSV")
            return customers

        except Exception as e:
            logger.error(f"Error reading legacy customers file: {str(e)}", exc_info=True)
            return []

    async def get_legacy_customer_by_id(
        self,
        legacy_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific legacy customer by legacy ID (Auto Increment)

        Args:
            legacy_id: Legacy customer ID

        Returns:
            Customer dictionary or None
        """
        customers = await self.fetch_legacy_customers()

        for customer in customers:
            if customer['legacy_id'] == legacy_id:
                return customer

        return None

    async def find_legacy_customer_by_identifier(
        self,
        identifier: str
    ) -> List[Dict[str, Any]]:
        """
        Find legacy customer(s) by any identifier

        Args:
            identifier: Search term (name, phone, email, or RUT)

        Returns:
            List of matching customers
        """
        customers = await self.fetch_legacy_customers()

        matches = []
        identifier_lower = identifier.lower()

        for customer in customers:
            # Check name
            if customer['nombre'] and identifier_lower in customer['nombre'].lower():
                matches.append(customer)
                continue

            # Check phone
            if customer['telefono'] and identifier in customer['telefono']:
                matches.append(customer)
                continue

            # Check email
            if customer['email'] and identifier_lower in customer['email'].lower():
                matches.append(customer)
                continue

            # Check RUT
            if customer['documento_identidad'] and identifier in customer['documento_identidad']:
                matches.append(customer)
                continue

        logger.info(f"Found {len(matches)} legacy customers matching '{identifier}'")
        return matches

    # ============================================
    # Statistics
    # ============================================

    async def get_legacy_stats(self) -> Dict[str, Any]:
        """
        Get statistics about legacy data

        Returns:
            Dictionary with statistics
        """
        customers = await self.fetch_legacy_customers()

        total = len(customers)
        with_email = sum(1 for c in customers if c['email'])
        with_phone = sum(1 for c in customers if c['telefono'])
        with_rut = sum(1 for c in customers if c['documento_identidad'])

        # Cities distribution
        cities = {}
        for c in customers:
            if c['ciudad']:
                cities[c['ciudad']] = cities.get(c['ciudad'], 0) + 1

        top_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]

        # Date range
        dates = [c['created_on'] for c in customers if c['created_on']]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None

        return {
            "total_customers": total,
            "with_email": with_email,
            "with_phone": with_phone,
            "with_rut": with_rut,
            "email_percentage": (with_email / total * 100) if total > 0 else 0,
            "phone_percentage": (with_phone / total * 100) if total > 0 else 0,
            "rut_percentage": (with_rut / total * 100) if total > 0 else 0,
            "top_cities": top_cities,
            "date_range": {
                "earliest": min_date.isoformat() if min_date else None,
                "latest": max_date.isoformat() if max_date else None,
            },
        }

    # ============================================
    # Matching Logic
    # ============================================

    async def find_potential_matches_in_current(
        self,
        legacy_customer: Dict[str, Any],
        current_customers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find potential matches for a legacy customer in current database

        Uses fuzzy matching on name, phone, email, and RUT

        Args:
            legacy_customer: Legacy customer data
            current_customers: List of current customers

        Returns:
            List of potential matches with confidence scores
        """
        matches = []

        for current in current_customers:
            score = 0
            reasons = []

            # Exact match on phone (highest confidence)
            if (legacy_customer.get('telefono') and
                current.get('telefono') and
                legacy_customer['telefono'] == current['telefono']):
                score += 90
                reasons.append("phone_exact")

            # Exact match on email
            if (legacy_customer.get('email') and
                current.get('email') and
                legacy_customer['email'].lower() == current['email'].lower()):
                score += 85
                reasons.append("email_exact")

            # Exact match on RUT
            if (legacy_customer.get('documento_identidad') and
                current.get('documento_identidad') and
                legacy_customer['documento_identidad'] == current['documento_identidad']):
                score += 95
                reasons.append("rut_exact")

            # Fuzzy match on name
            if legacy_customer.get('nombre') and current.get('nombre'):
                legacy_name = legacy_customer['nombre'].lower()
                current_name = current['nombre'].lower()

                if legacy_name == current_name:
                    score += 70
                    reasons.append("name_exact")
                elif legacy_name in current_name or current_name in legacy_name:
                    score += 50
                    reasons.append("name_partial")

            # If score is high enough, add to matches
            if score >= 50:
                matches.append({
                    "current_customer": current,
                    "confidence_score": min(score, 100),
                    "match_reasons": reasons,
                })

        # Sort by confidence score
        matches.sort(key=lambda x: x['confidence_score'], reverse=True)

        return matches
