from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Box(Base):
	__tablename__ = 'boxes'
	id = Column(Integer, primary_key=True)
	product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
	cell_id = Column(Integer, ForeignKey('cells.id'), nullable=True)
	quantity = Column(Integer, nullable=False, default=0)
	added_at = Column(DateTime, nullable=True)

	product = relationship('Product')
	cell = relationship('Cell')

	def as_dict(self):
		return {"id": self.id, "product_id": self.product_id, "cell_id": self.cell_id, "quantity": self.quantity, "added_at": self.added_at.isoformat() if self.added_at else None}
