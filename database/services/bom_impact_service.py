"""BOM Impact service for database operations"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import BomImpactResult, Email


class BomImpactService:
    """Service for managing BOM impact analysis results in the database"""

    @staticmethod
    async def get_by_email_id(db: AsyncSession, email_id: int) -> List[BomImpactResult]:
        """Get all BOM impact results for an email"""
        result = await db.execute(
            select(BomImpactResult)
            .where(BomImpactResult.email_id == email_id)
            .order_by(BomImpactResult.product_index)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_message_id(db: AsyncSession, message_id: str) -> List[BomImpactResult]:
        """Get all BOM impact results for an email by message_id"""
        result = await db.execute(
            select(BomImpactResult)
            .join(Email)
            .where(Email.message_id == message_id)
            .order_by(BomImpactResult.product_index)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, impact_id: int) -> Optional[BomImpactResult]:
        """Get a single BOM impact result by ID"""
        result = await db.execute(
            select(BomImpactResult).where(BomImpactResult.id == impact_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        email_id: int,
        product_index: int,
        impact_data: Dict[str, Any]
    ) -> BomImpactResult:
        """Create a new BOM impact result from process_supplier_price_change() output"""
        
        # Extract data from the impact_data structure
        component = impact_data.get("component", {})
        supplier = impact_data.get("supplier", {})
        price_change = impact_data.get("price_change", {})
        bom_impact = impact_data.get("bom_impact", {})
        summary = bom_impact.get("summary", {})
        
        impact = BomImpactResult(
            email_id=email_id,
            product_index=product_index,
            part_num=price_change.get("part_num"),
            product_name=component.get("description"),
            old_price=Decimal(str(price_change.get("old_price", 0))) if price_change.get("old_price") else None,
            new_price=Decimal(str(price_change.get("new_price", 0))) if price_change.get("new_price") else None,
            price_delta=Decimal(str(price_change.get("price_delta", 0))) if price_change.get("price_delta") else None,
            price_change_pct=Decimal(str(price_change.get("price_change_pct", 0))) if price_change.get("price_change_pct") else None,
            component_validated=component.get("validated", False),
            component_description=component.get("description"),
            supplier_id=supplier.get("supplier_id"),
            supplier_validated=supplier.get("validated", False),
            supplier_name=supplier.get("name"),
            vendor_num=supplier.get("vendor_num"),
            summary=summary,
            impact_details=bom_impact.get("impact_details", []),
            high_risk_assemblies=bom_impact.get("high_risk_assemblies", []),
            annual_impact=bom_impact.get("annual_impact", {}),
            total_annual_cost_impact=Decimal(str(summary.get("total_annual_cost_impact", 0))),
            actions_required=impact_data.get("actions_required", []),
            can_auto_approve=impact_data.get("can_auto_approve", True),
            recommendation=bom_impact.get("recommendation"),
            thresholds_used=bom_impact.get("thresholds_used", {}),
            status=impact_data.get("status", "pending"),
            processing_errors=impact_data.get("processing_errors", [])
        )
        
        db.add(impact)
        await db.flush()
        await db.refresh(impact)
        return impact

    @staticmethod
    async def update(
        db: AsyncSession,
        impact_id: int,
        **kwargs
    ) -> Optional[BomImpactResult]:
        """Update a BOM impact result"""
        impact = await BomImpactService.get_by_id(db, impact_id)
        if not impact:
            return None
        
        for key, value in kwargs.items():
            if hasattr(impact, key):
                setattr(impact, key, value)
        
        impact.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(impact)
        return impact

    @staticmethod
    async def approve(
        db: AsyncSession,
        impact_id: int,
        approved_by_id: int,
        approval_notes: Optional[str] = None
    ) -> Optional[BomImpactResult]:
        """Approve a BOM impact result for Epicor sync"""
        return await BomImpactService.update(
            db,
            impact_id,
            approved=True,
            approved_by_id=approved_by_id,
            approved_at=datetime.utcnow(),
            approval_notes=approval_notes
        )

    @staticmethod
    async def delete_by_email_id(db: AsyncSession, email_id: int) -> int:
        """Delete all BOM impact results for an email (for re-processing)"""
        result = await db.execute(
            delete(BomImpactResult).where(BomImpactResult.email_id == email_id)
        )
        return result.rowcount

    @staticmethod
    async def get_pending_approval(db: AsyncSession, limit: int = 50) -> List[BomImpactResult]:
        """Get BOM impact results that need approval"""
        result = await db.execute(
            select(BomImpactResult)
            .where(
                and_(
                    BomImpactResult.approved == False,
                    BomImpactResult.can_auto_approve == False,
                    BomImpactResult.status.in_(["success", "warning"])
                )
            )
            .order_by(BomImpactResult.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def to_dict(impact: BomImpactResult) -> Dict[str, Any]:
        """Convert BOM impact result to dictionary for API response"""
        return {
            "id": impact.id,
            "email_id": impact.email_id,
            "product_index": impact.product_index,
            "part_num": impact.part_num,
            "product_name": impact.product_name,
            "old_price": float(impact.old_price) if impact.old_price else None,
            "new_price": float(impact.new_price) if impact.new_price else None,
            "price_delta": float(impact.price_delta) if impact.price_delta else None,
            "price_change_pct": float(impact.price_change_pct) if impact.price_change_pct else None,
            "component_validated": impact.component_validated,
            "component_description": impact.component_description,
            "supplier_id": impact.supplier_id,
            "supplier_validated": impact.supplier_validated,
            "supplier_name": impact.supplier_name,
            "vendor_num": impact.vendor_num,
            "summary": impact.summary,
            "impact_details": impact.impact_details,
            "high_risk_assemblies": impact.high_risk_assemblies,
            "annual_impact": impact.annual_impact,
            "total_annual_cost_impact": float(impact.total_annual_cost_impact) if impact.total_annual_cost_impact else 0,
            "actions_required": impact.actions_required,
            "can_auto_approve": impact.can_auto_approve,
            "recommendation": impact.recommendation,
            "thresholds_used": impact.thresholds_used,
            "status": impact.status,
            "processing_errors": impact.processing_errors,
            "approved": impact.approved,
            "approved_by_id": impact.approved_by_id,
            "approved_at": impact.approved_at.isoformat() if impact.approved_at else None,
            "approval_notes": impact.approval_notes,
            "created_at": impact.created_at.isoformat() if impact.created_at else None,
            "updated_at": impact.updated_at.isoformat() if impact.updated_at else None,
        }

