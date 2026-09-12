from flask import Flask, render_template, request, redirect, url_for, jsonify
from config import SECRET_KEY
from database import init_db, get_session
from services import inventory, robot, ai
from models.cell import Cell
from models.box import Box
from models.product import Product
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/')
def index():
	return redirect(url_for('admin'))


@app.route('/init')
def init():
	init_db()
	# seed some cells
	db = get_session()
	try:
		if db.query(Cell).count() == 0:
			for y in range(4):
				for x in range(5):
					db.add(Cell(x=x, y=y, capacity=4))
			db.commit()
	finally:
		db.close()
	return 'initialized'


@app.route('/admin')
def admin():
	# list products, boxes, and cells
	db = get_session()
	try:
		products = [p.as_dict() for p in db.query(Product).order_by(Product.id).all()]
		boxes = [b.as_dict() for b in db.query(Box).order_by(Box.id).all()]
		cells = [c.as_dict() for c in db.query(Cell).order_by(Cell.id).all()]
	finally:
		db.close()
	return render_template('admin.html', products=products, boxes=boxes, cells=cells)


@app.route('/admin/products/create', methods=['POST'])
def admin_products_create():
	name = (request.form.get('name') or '').strip()
	if not name:
		return redirect(url_for('admin'))

	weight_dry_raw = (request.form.get('weight_dry') or '').strip()
	weight_wet_raw = (request.form.get('weight_wet') or '').strip()
	weight_dry = float(weight_dry_raw) if weight_dry_raw else None
	weight_wet = float(weight_wet_raw) if weight_wet_raw else None

	db = get_session()
	try:
		existing = db.query(Product).filter_by(name=name).first()
		if not existing:
			db.add(Product(name=name, weight_dry=weight_dry, weight_wet=weight_wet))
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/products/<int:product_id>/update', methods=['POST'])
def admin_products_update(product_id):
	name = (request.form.get('name') or '').strip()
	weight_dry_raw = (request.form.get('weight_dry') or '').strip()
	weight_wet_raw = (request.form.get('weight_wet') or '').strip()

	db = get_session()
	try:
		product = db.query(Product).get(product_id)
		if product:
			if name:
				product.name = name
			product.weight_dry = float(weight_dry_raw) if weight_dry_raw else None
			product.weight_wet = float(weight_wet_raw) if weight_wet_raw else None
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
def admin_products_delete(product_id):
	db = get_session()
	try:
		product = db.query(Product).get(product_id)
		if product:
			# Keep referential integrity by deleting related boxes first.
			db.query(Box).filter_by(product_id=product.id).delete()
			db.delete(product)
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/boxes/create', methods=['POST'])
def admin_boxes_create():
	product_id_raw = (request.form.get('product_id') or '').strip()
	cell_id_raw = (request.form.get('cell_id') or '').strip()
	quantity_raw = (request.form.get('quantity') or '0').strip()

	if not product_id_raw:
		return redirect(url_for('admin'))

	product_id = int(product_id_raw)
	cell_id = int(cell_id_raw) if cell_id_raw else None
	quantity = max(0, int(quantity_raw or 0))

	db = get_session()
	try:
		box = Box(product_id=product_id, cell_id=cell_id, quantity=quantity, added_at=datetime.utcnow())
		db.add(box)
		db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/boxes/<int:box_id>/update', methods=['POST'])
def admin_boxes_update(box_id):
	product_id_raw = (request.form.get('product_id') or '').strip()
	cell_id_raw = (request.form.get('cell_id') or '').strip()
	quantity_raw = (request.form.get('quantity') or '0').strip()
	added_at_raw = (request.form.get('added_at') or '').strip()

	db = get_session()
	try:
		box = db.query(Box).get(box_id)
		if box:
			if product_id_raw:
				box.product_id = int(product_id_raw)
			box.cell_id = int(cell_id_raw) if cell_id_raw else None
			box.quantity = max(0, int(quantity_raw or 0))
			box.added_at = datetime.fromisoformat(added_at_raw) if added_at_raw else None
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/boxes/<int:box_id>/delete', methods=['POST'])
def admin_boxes_delete(box_id):
	db = get_session()
	try:
		box = db.query(Box).get(box_id)
		if box:
			db.delete(box)
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/cells/create', methods=['POST'])
def admin_cells_create():
	x = int(request.form.get('x') or 0)
	y = int(request.form.get('y') or 0)
	capacity = max(1, int(request.form.get('capacity') or 1))

	db = get_session()
	try:
		db.add(Cell(x=x, y=y, capacity=capacity))
		db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/cells/<int:cell_id>/update', methods=['POST'])
def admin_cells_update(cell_id):
	x = int(request.form.get('x') or 0)
	y = int(request.form.get('y') or 0)
	capacity = max(1, int(request.form.get('capacity') or 1))

	db = get_session()
	try:
		cell = db.query(Cell).get(cell_id)
		if cell:
			cell.x = x
			cell.y = y
			cell.capacity = capacity
			db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/admin/cells/<int:cell_id>/delete', methods=['POST'])
def admin_cells_delete(cell_id):
	db = get_session()
	try:
		box_count = db.query(Box).filter_by(cell_id=cell_id).count()
		if box_count == 0:
			cell = db.query(Cell).get(cell_id)
			if cell:
				db.delete(cell)
				db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


@app.route('/store', methods=['GET', 'POST'])
def store():
	if request.method == 'GET':
		return render_template('input.html')
	# POST: receive product name and quantity
	name = request.form.get('name')
	qty = int(request.form.get('quantity') or 0)
	product = inventory.create_product(name)
	box = inventory.create_box(product.id, qty)
	# simulate robot store
	cell_id = box.cell_id
	cell = None
	if cell_id:
		db = get_session()
		try:
			cell = db.query(Cell).get(cell_id)
		finally:
			db.close()
	if cell:
		ok = robot.store_box(box.id, cell.x, cell.y)
		if ok:
			inventory.confirm_storage(box.id)
	return redirect(url_for('admin'))


@app.route('/retrieve/plan', methods=['POST'])
def retrieve_plan():
	product_id = int(request.form.get('product_id'))
	qty = int(request.form.get('quantity'))
	plan = inventory.fifo_plan(product_id, qty)
	return render_template('output.html', plan=plan)


@app.route('/retrieve/confirm', methods=['POST'])
def retrieve_confirm():
	# plan items come as JSON-like fields
	import json
	plan_json = request.form.get('plan')
	plan = json.loads(plan_json)
	# simulate robot operations
	for item in plan:
		# get cell coordinates
		db = get_session()
		try:
			cell = db.query(Cell).get(item['cell_id'])
		finally:
			db.close()
		if cell:
			robot.retrieve_box(item['box_id'], cell.x, cell.y, item['take'])
	inventory.apply_retrieval_plan(plan)
	return redirect(url_for('admin'))


if __name__ == '__main__':
	app.run(debug=True)

