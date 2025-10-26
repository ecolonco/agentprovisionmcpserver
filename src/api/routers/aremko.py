"""
Aremko API endpoints
Customer 360° profiles, analytics, and data orchestration
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db import crud, schemas, models
from src.core.security import get_current_user
from src.integrations.aremko_db_connector import AremkoDBConnector
from src.integrations.aremko_legacy_connector import AremkoLegacyConnector
from src.integrations.aremko_analytics_connector import AremkoAnalyticsConnector
from src.utils.logger import logger

router = APIRouter()


# ============================================
# Customer Lookup & Resolution
# ============================================

@router.get("/customers/search")
async def search_customers(
    query: str = Query(..., description="Search by name, phone, email, or RUT"),
    source: str = Query("current", description="Data source: current, legacy, or all"),
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for customers across current and/or legacy data

    Returns matches from both databases with confidence scores
    """
    logger.info(f"Searching customers: query='{query}', source={source}")

    results = {
        "query": query,
        "source": source,
        "current_matches": [],
        "legacy_matches": [],
    }

    try:
        # Search current database
        if source in ["current", "all"]:
            db_connector = AremkoDBConnector(tenant=x_tenant)
            current_matches = await db_connector.find_customer_by_identifier(query)
            results["current_matches"] = current_matches
            await db_connector.close()

        # Search legacy data
        if source in ["legacy", "all"]:
            legacy_connector = AremkoLegacyConnector(tenant=x_tenant)
            legacy_matches = await legacy_connector.find_legacy_customer_by_identifier(query)
            results["legacy_matches"] = legacy_matches

        logger.info(
            f"Found {len(results['current_matches'])} current, "
            f"{len(results['legacy_matches'])} legacy matches"
        )

        return results

    except Exception as e:
        logger.error(f"Error searching customers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching customers: {str(e)}"
        )


@router.get("/customers/{customer_id}/profile")
async def get_customer_360_profile(
    customer_id: int,
    include_legacy: bool = Query(True, description="Include legacy data if available"),
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive 360° profile for a customer

    Includes:
    - Basic info
    - Statistics (visits, spend)
    - RFM analysis
    - Service preferences
    - Recent activity
    - Legacy data (if available)
    """
    logger.info(f"Generating 360° profile for customer {customer_id}")

    try:
        analytics = AremkoAnalyticsConnector(tenant=x_tenant)
        profile = await analytics.generate_customer_360_profile(
            customer_id=customer_id,
            include_legacy=include_legacy
        )

        if "error" in profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=profile["error"]
            )

        await analytics.db_connector.close()

        logger.info(f"Profile generated for customer {customer_id}")
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating profile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating profile: {str(e)}"
        )


@router.get("/customers/{customer_id}/insights")
async def get_customer_insights(
    customer_id: int,
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get behavioral insights and recommendations for a customer

    Returns:
    - Segment classification
    - Churn risk
    - Upsell potential
    - Visit patterns
    - Service preferences
    """
    logger.info(f"Analyzing behavior for customer {customer_id}")

    try:
        analytics = AremkoAnalyticsConnector(tenant=x_tenant)

        # Generate profile first
        profile = await analytics.generate_customer_360_profile(
            customer_id=customer_id,
            include_legacy=True
        )

        if "error" in profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=profile["error"]
            )

        # Analyze behavior
        insights = await analytics.analyze_customer_behavior(profile)

        await analytics.db_connector.close()

        logger.info(f"Insights generated for customer {customer_id}")
        return insights

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing customer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing customer: {str(e)}"
        )


# ============================================
# Campaigns & Reactivation
# ============================================

@router.get("/campaigns/inactive-customers")
async def get_inactive_customers_for_campaign(
    months: int = Query(12, description="Months of inactivity", ge=1, le=36),
    limit: int = Query(100, description="Max customers to analyze", ge=1, le=500),
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get inactive customers with full analysis for reactivation campaigns

    Returns prioritized list of customers to target with:
    - Complete profiles
    - Behavioral insights
    - Reactivation priority score
    - Personalized recommendations
    """
    logger.info(f"Fetching inactive customers: months={months}, limit={limit}")

    try:
        analytics = AremkoAnalyticsConnector(tenant=x_tenant)

        results = await analytics.batch_analyze_inactive_customers(
            months=months,
            limit=limit
        )

        await analytics.db_connector.close()

        logger.info(f"Analyzed {len(results)} inactive customers")

        return {
            "total_analyzed": len(results),
            "parameters": {
                "months_inactive": months,
                "limit": limit,
            },
            "customers": results,
        }

    except Exception as e:
        logger.error(f"Error fetching inactive customers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching inactive customers: {str(e)}"
        )


@router.get("/campaigns/segments/{segment}")
async def get_customers_by_segment(
    segment: str,
    limit: int = Query(100, ge=1, le=500),
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customers by RFM segment

    Segments:
    - VIP
    - Champions
    - Loyal
    - Promising
    - At Risk
    - Hibernating
    - Lost
    - New
    - Occasional
    """
    logger.info(f"Fetching customers in segment: {segment}")

    valid_segments = [
        "VIP", "Champions", "Loyal", "Promising", "At Risk",
        "Hibernating", "Lost", "New", "Occasional"
    ]

    if segment not in valid_segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid segment. Must be one of: {', '.join(valid_segments)}"
        )

    try:
        db_connector = AremkoDBConnector(tenant=x_tenant)
        analytics = AremkoAnalyticsConnector(tenant=x_tenant)

        # Fetch all customers (would be optimized with DB query in production)
        customers = await db_connector.fetch_customers(limit=1000)

        # Filter by segment
        segment_customers = []
        for customer in customers:
            stats = await db_connector.get_customer_stats(customer['id'])
            rfm = analytics.calculate_rfm_score(stats)

            if rfm['segment'] == segment:
                segment_customers.append({
                    "customer": customer,
                    "stats": stats,
                    "rfm": rfm,
                })

                if len(segment_customers) >= limit:
                    break

        await db_connector.close()

        logger.info(f"Found {len(segment_customers)} customers in segment '{segment}'")

        return {
            "segment": segment,
            "total_found": len(segment_customers),
            "customers": segment_customers,
        }

    except Exception as e:
        logger.error(f"Error fetching segment customers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching segment customers: {str(e)}"
        )


# ============================================
# Data Synchronization & Mapping
# ============================================

@router.post("/sync/legacy-to-current")
async def sync_legacy_to_current(
    limit: Optional[int] = Query(None, description="Limit number of records to sync"),
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronize legacy customer data with current database

    Creates mappings between legacy and current customer records
    """
    logger.info(f"Starting legacy → current sync (limit={limit})")

    try:
        legacy_connector = AremkoLegacyConnector(tenant=x_tenant)
        db_connector = AremkoDBConnector(tenant=x_tenant)

        # Fetch legacy customers
        legacy_customers = await legacy_connector.fetch_legacy_customers(limit=limit)

        # Fetch current customers
        current_customers = await db_connector.fetch_customers(limit=10000)

        sync_results = {
            "total_legacy": len(legacy_customers),
            "total_current": len(current_customers),
            "mappings_created": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "no_match": 0,
            "details": []
        }

        for legacy in legacy_customers:
            # Find potential matches
            matches = await legacy_connector.find_potential_matches_in_current(
                legacy,
                current_customers
            )

            if matches and matches[0]['confidence_score'] >= 70:
                # High confidence match - create mapping
                current_match = matches[0]['current_customer']

                # Create mapping record
                mapping_data = schemas.MappingCreate(
                    source_system=models.IntegrationSystem.AREMKO_LEGACY,
                    source_id=legacy['legacy_id'],
                    source_entity_type=models.EntityType.CUSTOMER,
                    target_system=models.IntegrationSystem.AREMKO_DB,
                    target_id=str(current_match['id']),
                    target_entity_type=models.EntityType.CUSTOMER,
                    confidence_score=matches[0]['confidence_score'],
                    metadata={
                        "match_reasons": matches[0]['match_reasons'],
                        "legacy_name": legacy['nombre'],
                        "current_name": current_match['nombre'],
                    }
                )

                await crud.MappingCRUD.create(db, mapping_data)

                sync_results["mappings_created"] += 1

                if matches[0]['confidence_score'] >= 85:
                    sync_results["high_confidence"] += 1
                else:
                    sync_results["medium_confidence"] += 1

                sync_results["details"].append({
                    "legacy_id": legacy['legacy_id'],
                    "legacy_name": legacy['nombre'],
                    "current_id": current_match['id'],
                    "current_name": current_match['nombre'],
                    "confidence": matches[0]['confidence_score'],
                    "reasons": matches[0]['match_reasons'],
                })
            else:
                sync_results["no_match"] += 1

        await db_connector.close()

        logger.info(
            f"Sync complete: {sync_results['mappings_created']} mappings created"
        )

        return sync_results

    except Exception as e:
        logger.error(f"Error syncing legacy data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing legacy data: {str(e)}"
        )


@router.get("/mappings/customer/{customer_id}")
async def get_customer_mappings(
    customer_id: int,
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all mappings for a specific customer

    Shows links between current DB and legacy records
    """
    try:
        # Get mappings where this customer is the target
        mapping = await crud.MappingCRUD.get_by_target(
            db,
            target_system=models.IntegrationSystem.AREMKO_DB,
            target_id=str(customer_id),
            entity_type=models.EntityType.CUSTOMER
        )

        if not mapping:
            return {
                "customer_id": customer_id,
                "has_legacy_data": False,
                "mapping": None,
            }

        # Fetch legacy data
        legacy_connector = AremkoLegacyConnector(tenant=x_tenant)
        legacy_customer = await legacy_connector.get_legacy_customer_by_id(
            mapping.source_id
        )

        return {
            "customer_id": customer_id,
            "has_legacy_data": True,
            "mapping": {
                "id": str(mapping.id),
                "legacy_id": mapping.source_id,
                "confidence_score": mapping.confidence_score,
                "created_at": mapping.created_at.isoformat(),
                "metadata": mapping.metadata,
            },
            "legacy_customer": legacy_customer,
        }

    except Exception as e:
        logger.error(f"Error fetching mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching mappings: {str(e)}"
        )


# ============================================
# Statistics & Reporting
# ============================================

@router.get("/stats/overview")
async def get_aremko_stats_overview(
    x_tenant: str = Header("aremko", alias="X-Tenant"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get overall statistics for Aremko data

    Includes counts, segments, legacy data stats
    """
    try:
        db_connector = AremkoDBConnector(tenant=x_tenant)
        legacy_connector = AremkoLegacyConnector(tenant=x_tenant)

        # Current DB stats
        current_customers = await db_connector.fetch_customers(limit=10000)
        inactive_12m = await db_connector.get_inactive_customers(months=12)

        # Legacy stats
        legacy_stats = await legacy_connector.get_legacy_stats()

        # Services & Products
        services = await db_connector.fetch_all_services()
        products = await db_connector.fetch_all_products()

        await db_connector.close()

        return {
            "current_database": {
                "total_customers": len(current_customers),
                "inactive_12_months": len(inactive_12m),
                "services_available": len(services),
                "products_available": len(products),
            },
            "legacy_data": legacy_stats,
            "data_completeness": {
                "current_with_email": sum(1 for c in current_customers if c.get('email')),
                "current_with_phone": sum(1 for c in current_customers if c.get('telefono')),
                "current_with_rut": sum(1 for c in current_customers if c.get('documento_identidad')),
            }
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )
