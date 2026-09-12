from sqlalchemy import Column, Integer
from database import Base

class Cell(Base):
	__tablename__ = 'cells'
	id = Column(Integer, primary_key=True)
	x = Column(Integer, nullable=False)
	y = Column(Integer, nullable=False)
	capacity = Column(Integer, nullable=False, default=4)

	def as_dict(self):
		return {"id": self.id, "x": self.x, "y": self.y, "capacity": self.capacity}
