"""
Mapping registry endpoints
Handles cross-system entity mappings
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db import crud, schemas
from src.core.security import get_current_user
from src.utils.logger import logger

router = APIRouter()


@router.post(
    "/mappings/register",
    response_model=schemas.MappingResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_mapping(
    mapping: schemas.MappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Register a new mapping between systems

    Creates a bidirectional mapping between a source and target system.
    """
    logger.info(
        f"Creating mapping: {mapping.source_system}:{mapping.source_id} -> "
        f"{mapping.target_system}:{mapping.target_id}"
    )

    try:
        # Check if mapping already exists
        existing = await crud.MappingCRUD.get_by_source(
            db,
            mapping.source_system,
            mapping.source_id,
            mapping.source_entity_type
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mapping already exists for this source entity"
            )

        # Create mapping
        db_mapping = await crud.MappingCRUD.create(db, mapping)
        logger.info(f"Mapping created successfully: {db_mapping.id}")

        return db_mapping

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating mapping: {str(e)}"
        )


@router.get("/mappings/{mapping_id}", response_model=schemas.MappingResponse)
async def get_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific mapping by ID
    """
    mapping = await crud.MappingCRUD.get(db, mapping_id)

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    return mapping


@router.get("/mappings", response_model=schemas.MappingList)
async def list_mappings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List mappings with pagination and filtering

    Query parameters:
    - page: Page number (starts at 1)
    - page_size: Number of items per page
    - status: Filter by mapping status
    - entity_type: Filter by entity type
    """
    skip = (page - 1) * page_size

    mappings = await crud.MappingCRUD.get_multi(
        db,
        skip=skip,
        limit=page_size,
        status=status,
        entity_type=entity_type
    )

    total = await crud.MappingCRUD.count(
        db,
        status=status,
        entity_type=entity_type
    )

    return {
        "items": mappings,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/mappings/lookup/source", response_model=schemas.MappingResponse)
async def lookup_by_source(
    source_system: str = Query(...),
    source_id: str = Query(...),
    entity_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lookup mapping by source system and ID
    """
    mapping = await crud.MappingCRUD.get_by_source(
        db,
        source_system,
        source_id,
        entity_type
    )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    return mapping


@router.get("/mappings/lookup/target", response_model=schemas.MappingResponse)
async def lookup_by_target(
    target_system: str = Query(...),
    target_id: str = Query(...),
    entity_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lookup mapping by target system and ID
    """
    mapping = await crud.MappingCRUD.get_by_target(
        db,
        target_system,
        target_id,
        entity_type
    )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    return mapping


@router.patch("/mappings/{mapping_id}", response_model=schemas.MappingResponse)
async def update_mapping(
    mapping_id: UUID,
    mapping_update: schemas.MappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a mapping
    """
    # Check if mapping exists
    existing = await crud.MappingCRUD.get(db, mapping_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    # Update mapping
    updated_mapping = await crud.MappingCRUD.update(db, mapping_id, mapping_update)
    logger.info(f"Mapping updated: {mapping_id}")

    return updated_mapping


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: UUID,
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a mapping (soft delete by default)

    Query parameters:
    - hard_delete: If true, permanently deletes the mapping
    """
    # Check if mapping exists
    existing = await crud.MappingCRUD.get(db, mapping_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    # Delete mapping
    await crud.MappingCRUD.delete(db, mapping_id, soft=not hard_delete)
    logger.info(f"Mapping deleted: {mapping_id} (hard={hard_delete})")

    return None


@router.get("/mappings/status", response_model=dict)
async def get_mapping_status(
    source_system: str = Query(...),
    target_system: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get sync status between two systems

    Returns statistics about mappings between source and target systems
    """
    # TODO: Implement comprehensive status check
    # For now, return basic counts

    return {
        "source_system": source_system,
        "target_system": target_system,
        "status": "operational",
        "message": "Status endpoint - to be fully implemented"
    }
