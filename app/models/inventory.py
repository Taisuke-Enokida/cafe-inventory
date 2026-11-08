from app.extensions import db


class InventoryMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    correction_of_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_movement.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    kind = db.Column(db.String(16), nullable=False)
    quantity_delta = db.Column(db.Numeric(12, 3), nullable=False)
    reason = db.Column(db.String(500), nullable=True)
    occurred_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        index=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            "kind IN ('receipt', 'usage', 'waste', 'correction')",
            name="ck_movement_kind",
        ),
        db.CheckConstraint("quantity_delta != 0", name="ck_movement_nonzero"),
        db.CheckConstraint(
            "(kind = 'receipt' AND quantity_delta > 0) OR "
            "(kind IN ('usage', 'waste') AND quantity_delta < 0) OR "
            "(kind = 'correction' AND correction_of_id IS NOT NULL AND reason IS NOT NULL)",
            name="ck_movement_sign_and_correction",
        ),
        db.Index("ix_movement_product_occurred", "product_id", "occurred_at"),
    )

    product = db.relationship("Product", back_populates="movements")
    actor = db.relationship("User")
    correction_of = db.relationship(
        "InventoryMovement",
        remote_side=[id],
        foreign_keys=[correction_of_id],
    )
