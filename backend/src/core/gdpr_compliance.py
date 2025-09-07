from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
from fastapi import HTTPException
from .data_encryption import DataEncryption

class ConsentType(str, Enum):
    ESSENTIAL = "essential"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    THIRD_PARTY = "third_party"

class ConsentStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"

class DataRetentionPolicy(str, Enum):
    ONE_MONTH = "one_month"
    THREE_MONTHS = "three_months"
    SIX_MONTHS = "six_months"
    ONE_YEAR = "one_year"
    TWO_YEARS = "two_years"
    INDEFINITE = "indefinite"

class GDPRCompliance:
    def __init__(
        self,
        encryption: DataEncryption,
        storage_backend: Any  # Your database/storage interface
    ):
        self.encryption = encryption
        self.storage = storage_backend

    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record user consent for specific data processing purposes.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        consent_record = {
            "consent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "consent_type": consent_type,
            "status": status,
            "timestamp": timestamp.isoformat(),
            "ip_address": self.storage.get_user_ip(user_id),
            "user_agent": self.storage.get_user_agent(user_id)
        }

        # Encrypt sensitive data
        encrypted_record = {
            **consent_record,
            "ip_address": self.encryption.encrypt_text(consent_record["ip_address"]),
            "user_agent": self.encryption.encrypt_text(consent_record["user_agent"])
        }

        await self.storage.save_consent(encrypted_record)
        return consent_record

    async def get_user_consents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all consent records for a user.
        """
        encrypted_consents = await self.storage.get_user_consents(user_id)
        decrypted_consents = []

        for consent in encrypted_consents:
            decrypted_consent = {
                **consent,
                "ip_address": self.encryption.decrypt_text(consent["ip_address"]),
                "user_agent": self.encryption.decrypt_text(consent["user_agent"])
            }
            decrypted_consents.append(decrypted_consent)

        return decrypted_consents

    async def request_data_export(self, user_id: str) -> str:
        """
        Handle a data export request, returning a request ID.
        """
        request_id = str(uuid.uuid4())
        
        # Record the export request
        await self.storage.save_export_request({
            "request_id": request_id,
            "user_id": user_id,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat()
        })

        # Trigger async export process
        self.storage.trigger_export_process(request_id, user_id)
        
        return request_id

    async def get_export_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of a data export request.
        """
        status = await self.storage.get_export_status(request_id)
        if not status:
            raise HTTPException(status_code=404, detail="Export request not found")
        return status

    async def request_data_deletion(
        self,
        user_id: str,
        deletion_scope: Optional[List[str]] = None
    ) -> str:
        """
        Handle a data deletion request, returning a request ID.
        """
        request_id = str(uuid.uuid4())
        
        # Record the deletion request
        await self.storage.save_deletion_request({
            "request_id": request_id,
            "user_id": user_id,
            "scope": deletion_scope or ["all"],
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat()
        })

        # Trigger async deletion process
        self.storage.trigger_deletion_process(request_id, user_id, deletion_scope)
        
        return request_id

    async def get_deletion_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of a data deletion request.
        """
        status = await self.storage.get_deletion_status(request_id)
        if not status:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        return status

    async def anonymize_user_data(
        self,
        user_id: str,
        fields_to_anonymize: Optional[List[str]] = None
    ) -> None:
        """
        Anonymize specific user data fields instead of deleting them.
        """
        if not fields_to_anonymize:
            fields_to_anonymize = ["name", "email", "phone", "address"]

        for field in fields_to_anonymize:
            await self.storage.anonymize_field(user_id, field)

    async def apply_retention_policy(
        self,
        data_type: str,
        retention_policy: DataRetentionPolicy
    ) -> None:
        """
        Apply data retention policy to specific types of data.
        """
        retention_periods = {
            DataRetentionPolicy.ONE_MONTH: timedelta(days=30),
            DataRetentionPolicy.THREE_MONTHS: timedelta(days=90),
            DataRetentionPolicy.SIX_MONTHS: timedelta(days=180),
            DataRetentionPolicy.ONE_YEAR: timedelta(days=365),
            DataRetentionPolicy.TWO_YEARS: timedelta(days=730),
            DataRetentionPolicy.INDEFINITE: None
        }

        retention_period = retention_periods[retention_policy]
        if retention_period:
            cutoff_date = datetime.utcnow() - retention_period
            await self.storage.delete_expired_data(data_type, cutoff_date)

    async def get_processing_activities(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get a record of all data processing activities for a user.
        """
        activities = await self.storage.get_processing_activities(user_id)
        return activities

def setup_gdpr_compliance(
    encryption: DataEncryption,
    storage_backend: Any
) -> GDPRCompliance:
    """
    Set up GDPR compliance utilities with encryption and storage backend.
    """
    return GDPRCompliance(encryption, storage_backend)