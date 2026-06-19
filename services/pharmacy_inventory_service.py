"""Pharmacy inventory management and stock deduction on dispense."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


class PharmacyInventoryService:
    @staticmethod
    def list_items(db: Session, *, clinic_id: int) -> list[models.PharmacyInventoryItem]:
        return (
            db.query(models.PharmacyInventoryItem)
            .filter(models.PharmacyInventoryItem.clinic_id == clinic_id)
            .order_by(models.PharmacyInventoryItem.medication_name.asc())
            .all()
        )

    @staticmethod
    def upsert_item(
        db: Session,
        *,
        clinic_id: int,
        sku: str,
        medication_name: str,
        quantity: int,
        reorder_level: int = 10,
        unit_price_gnf: int = 25_000,
        batch_number: str | None = None,
        expiry_date=None,
        supplier: str | None = None,
    ) -> models.PharmacyInventoryItem:
        item = (
            db.query(models.PharmacyInventoryItem)
            .filter(
                models.PharmacyInventoryItem.clinic_id == clinic_id,
                models.PharmacyInventoryItem.sku == sku,
            )
            .first()
        )
        if item:
            item.medication_name = medication_name
            item.quantity = quantity
            item.reorder_level = reorder_level
            item.unit_price_gnf = unit_price_gnf
            if batch_number is not None:
                item.batch_number = batch_number
            if expiry_date is not None:
                item.expiry_date = expiry_date
            if supplier is not None:
                item.supplier = supplier
        else:
            item = models.PharmacyInventoryItem(
                clinic_id=clinic_id,
                sku=sku,
                medication_name=medication_name,
                quantity=quantity,
                reorder_level=reorder_level,
                unit_price_gnf=unit_price_gnf,
                batch_number=batch_number,
                expiry_date=expiry_date,
                supplier=supplier,
            )
            db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def adjust_quantity(
        db: Session, *, clinic_id: int, item_id: int, delta: int
    ) -> models.PharmacyInventoryItem:
        item = (
            db.query(models.PharmacyInventoryItem)
            .filter(
                models.PharmacyInventoryItem.id == item_id,
                models.PharmacyInventoryItem.clinic_id == clinic_id,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        item.quantity = max(0, item.quantity + delta)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def deduct_for_prescription(db: Session, *, clinic_id: int, medications_text: str) -> None:
        """Match prescription medication names to inventory and deduct default pack sizes."""
        if not medications_text:
            return
        items = PharmacyInventoryService.list_items(db, clinic_id=clinic_id)
        med_lower = medications_text.lower()
        for inv in items:
            name_key = inv.medication_name.lower()
            if name_key in med_lower or inv.sku.lower() in med_lower:
                deduct = 14 if "amox" in name_key else 20 if "para" in name_key else 10
                inv.quantity = max(0, inv.quantity - deduct)
        db.commit()

    @staticmethod
    def ensure_default_stock(db: Session, *, clinic_id: int) -> None:
        if (
            db.query(models.PharmacyInventoryItem)
            .filter(models.PharmacyInventoryItem.clinic_id == clinic_id)
            .count()
            > 0
        ):
            return
        defaults = [
            ("PARA-500", "Paracétamol 500mg", 240, 40, 15_000),
            ("AMOX-500", "Amoxicilline 500mg", 120, 20, 35_000),
            ("IBU-400", "Ibuprofène 400mg", 180, 30, 18_000),
        ]
        for sku, name, qty, reorder, price in defaults:
            PharmacyInventoryService.upsert_item(
                db,
                clinic_id=clinic_id,
                sku=sku,
                medication_name=name,
                quantity=qty,
                reorder_level=reorder,
                unit_price_gnf=price,
            )
