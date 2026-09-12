from datetime import datetime, timedelta
from database import get_session
from models.product import Product
from models.box import Box
from models.cell import Cell

MIN_AGE = timedelta(hours=24)

def create_product(name, weight_dry=None, weight_wet=None):
	db = get_session()
	try:
		p = db.query(Product).filter_by(name=name).first()
		if not p:
			p = Product(name=name, weight_dry=weight_dry, weight_wet=weight_wet)
			db.add(p)
			db.commit()
			db.refresh(p)
		return p
	finally:
		db.close()

def list_products():
	db = get_session()
	try:
		return [p.as_dict() for p in db.query(Product).all()]
	finally:
		db.close()

def find_suitable_cell(db):
	# simplistic: pick first cell with room (boxes count < capacity)
	cells = db.query(Cell).order_by(Cell.id).all()
	for cell in cells:
		cnt = db.query(Box).filter_by(cell_id=cell.id).count()
		if cnt < cell.capacity:
			return cell
	return None

def create_box(product_id, quantity, assign_cell=True):
	db = get_session()
	try:
		box = Box(product_id=product_id, quantity=quantity)
		if assign_cell:
			cell = find_suitable_cell(db)
			if cell:
				box.cell_id = cell.id
		db.add(box)
		db.commit()
		db.refresh(box)
		return box
	finally:
		db.close()

def confirm_storage(box_id):
	db = get_session()
	try:
		box = db.query(Box).get(box_id)
		if box:
			box.added_at = datetime.utcnow()
			db.commit()
			db.refresh(box)
		return box
	finally:
		db.close()

def fifo_plan(product_id, requested_qty):
	db = get_session()
	try:
		now = datetime.utcnow()
		ready_cutoff = now - MIN_AGE
		boxes = db.query(Box).filter(Box.product_id==product_id, Box.quantity>0, Box.added_at!=None, Box.added_at<=ready_cutoff).order_by(Box.added_at.asc()).all()
		plan = []
		remaining = requested_qty
		for b in boxes:
			take = min(b.quantity, remaining)
			plan.append({"box_id": b.id, "cell_id": b.cell_id, "available": b.quantity, "take": take, "added_at": b.added_at.isoformat()})
			remaining -= take
			if remaining <= 0:
				break
		return {"requested": requested_qty, "fulfilled": requested_qty - remaining, "remaining": remaining, "plan": plan}
	finally:
		db.close()

def apply_retrieval_plan(plan):
	db = get_session()
	try:
		for item in plan:
			box = db.query(Box).get(item['box_id'])
			if not box:
				continue
			take = item['take']
			if take >= box.quantity:
				box.quantity = 0
			else:
				box.quantity = box.quantity - take
		db.commit()
	finally:
		db.close()

