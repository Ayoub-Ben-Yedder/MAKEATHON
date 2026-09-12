from sqlalchemy import Column, Integer, String, Float
from database import Base

class Product(Base):
	__tablename__ = 'products'
	id = Column(Integer, primary_key=True)
	name = Column(String(100), nullable=False, unique=True)
	weight_dry = Column(Float, nullable=True)
	weight_wet = Column(Float, nullable=True)

	def as_dict(self):
		return {"id": self.id, "name": self.name, "weight_dry": self.weight_dry, "weight_wet": self.weight_wet}
