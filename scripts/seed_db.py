"""
Seed database with sample data for testing
Run with: python -m scripts.seed_db
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import AsyncSessionLocal, init_db
from src.db import models


async def seed_integrations():
    """Seed integration configurations"""
    async with AsyncSessionLocal() as db:
        integrations = [
            models.Integration(
                system=models.IntegrationSystem.ADP,
                name="ADP Workforce Now",
                description="Payroll and HR management system",
                is_active=True,
                is_configured=False,
                sync_enabled=False,
                health_status="unknown"
            ),
            models.Integration(
                system=models.IntegrationSystem.EAGLESOFT,
                name="Eaglesoft Practice Management",
                description="Dental practice management software",
                is_active=True,
                is_configured=False,
                sync_enabled=False,
                health_status="unknown"
            ),
            models.Integration(
                system=models.IntegrationSystem.DENTALINTEL,
                name="DentalIntel Analytics",
                description="Production KPIs and analytics",
                is_active=True,
                is_configured=False,
                sync_enabled=False,
                health_status="unknown"
            ),
            models.Integration(
                system=models.IntegrationSystem.NETSUITE,
                name="NetSuite ERP",
                description="Financial GL, AP/AR management",
                is_active=True,
                is_configured=False,
                sync_enabled=False,
                health_status="unknown"
            ),
            models.Integration(
                system=models.IntegrationSystem.BANK,
                name="Bank/Merchant Processor",
                description="Payment and deposit processing",
                is_active=True,
                is_configured=False,
                sync_enabled=False,
                health_status="unknown"
            ),
        ]

        db.add_all(integrations)
        await db.commit()
        print(f"✅ Seeded {len(integrations)} integrations")


async def seed_sample_mappings():
    """Seed sample mapping data"""
    async with AsyncSessionLocal() as db:
        mappings = [
            # Example: Employee mapping between ADP and DentalERP
            models.Mapping(
                source_system=models.IntegrationSystem.ADP,
                source_id="ADP-EMP-12345",
                source_entity_type=models.EntityType.EMPLOYEE,
                target_system=models.IntegrationSystem.DENTALERP,
                target_id="ERP-EMP-001",
                target_entity_type=models.EntityType.EMPLOYEE,
                status=models.MappingStatus.ACTIVE,
                confidence_score=100,
                metadata={"name": "John Doe", "department": "Dental Hygiene"}
            ),
            # Example: Patient mapping between Eaglesoft and DentalERP
            models.Mapping(
                source_system=models.IntegrationSystem.EAGLESOFT,
                source_id="EAGLE-PAT-67890",
                source_entity_type=models.EntityType.PATIENT,
                target_system=models.IntegrationSystem.DENTALERP,
                target_id="ERP-PAT-001",
                target_entity_type=models.EntityType.PATIENT,
                status=models.MappingStatus.ACTIVE,
                confidence_score=100,
                metadata={"name": "Jane Smith", "practice": "Main Office"}
            ),
        ]

        db.add_all(mappings)
        await db.commit()
        print(f"✅ Seeded {len(mappings)} sample mappings")


async def seed_sample_job():
    """Seed a sample job"""
    async with AsyncSessionLocal() as db:
        job = models.Job(
            job_type="sync_employees",
            workflow_id="workflow_sample_001",
            source_system=models.IntegrationSystem.ADP,
            target_system=models.IntegrationSystem.DENTALERP,
            entity_type=models.EntityType.EMPLOYEE,
            status=models.JobStatus.COMPLETED,
            total_records=100,
            processed_records=100,
            failed_records=0,
            config={"batch_size": 50, "full_sync": True},
            result={"status": "success", "synced_count": 100}
        )

        db.add(job)
        await db.commit()
        print("✅ Seeded 1 sample job")


async def main():
    """Main seed function"""
    print("🌱 Starting database seeding...")

    # Initialize database (create tables)
    print("Creating database tables...")
    await init_db()

    # Seed data
    await seed_integrations()
    await seed_sample_mappings()
    await seed_sample_job()

    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
