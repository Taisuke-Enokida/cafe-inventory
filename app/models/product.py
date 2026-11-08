from app.extensions import db


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    unit = db.Column(db.String(24), nullable=False)
    reorder_point = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    __table_args__ = (
        db.CheckConstraint("reorder_point >= 0", name="ck_product_reorder_point_nonnegative"),
    )

    movements = db.relationship(
        "InventoryMovement",
        back_populates="product",
        lazy="select",
        passive_deletes=True,
    )
