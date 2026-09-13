from flask import Flask, render_template, request, redirect, url_for, jsonify
from config import SECRET_KEY
from database import init_db, get_session
from services import inventory, robot, model_ai
from models.cell import Cell
from models.box import Box
from models.product import Product
from datetime import datetime
import os
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

CAPTURE_DIR = os.path.join(app.root_path, 'static', 'captures')
os.makedirs(CAPTURE_DIR, exist_ok=True)

input_state_lock = threading.Lock()
latest_input_state = {
	"image_path": None,
	"captured_at": None,
	"detected_product_id": None,
	"detected_product_name": None,
	"ai_confidence": None,
	"last_weight": None,
	"estimated_quantity": None,
	"unit_weight": None,
	"message": "Waiting for camera capture"
}


def _resolve_product_from_detection(db, detection):
	product_id = detection.get('product_id')
	name = (detection.get('name') or '').strip()
	product = None

	if product_id:
		product = db.query(Product).get(int(product_id))

	if not product and name:
		product = db.query(Product).filter(Product.name.ilike(name)).first()

	if not product and name:
		# Keep flow continuous for demos: create a product when AI predicts a new name.
		product = Product(name=name)
		db.add(product)
		db.commit()
		db.refresh(product)

	return product


def _calculate_estimated_quantity(db, product_id, measured_weight):
	if not product_id or measured_weight is None:
		return None, None

	product = db.query(Product).get(int(product_id))
	if not product:
		return None, None

	unit_weight = product.weight_wet if product.weight_wet is not None else product.weight_dry
	if not unit_weight or unit_weight <= 0:
		return None, None

	estimated_qty = max(0, int(measured_weight / unit_weight))
	return estimated_qty, unit_weight


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
			for y in range(2):
				for x in range(1):
					db.add(Cell(x=x, y=y, capacity=4))
		if db.query(Product).count() == 0:
			db.add_all([Product(name="A", weight_dry=50, weight_wet=55), Product(name="B", weight_dry=10, weight_wet=12)])
		db.commit()
	finally:
		db.close()
	return redirect(url_for('admin'))


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
	# POST: receive either a product id or product name and a quantity
	product_id_raw = (request.form.get('product_id') or '').strip()
	name = (request.form.get('name') or '').strip()
	qty = int(request.form.get('quantity') or 0)
	if qty < 1:
		return redirect(url_for('store'))

	product = None
	product_id = None
	db = get_session()
	try:
		if product_id_raw:
			try:
				product_id = int(product_id_raw)
			except (TypeError, ValueError):
				product_id = None
			if product_id is not None:
				product = db.query(Product).get(product_id)

		if not product and name:
			product = db.query(Product).filter(Product.name.ilike(name)).first()
	finally:
		db.close()

	if not product:
		if not name:
			return redirect(url_for('store'))
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
		ok = robot.store_box(product.id, cell.x, cell.y)
		if ok:
			inventory.confirm_storage(box.id)

	with input_state_lock:
		latest_input_state['message'] = 'Box stored successfully'
		latest_input_state['detected_product_id'] = product.id
		latest_input_state['detected_product_name'] = product.name
	return redirect(url_for('store'))


@app.route('/api/input/capture', methods=['POST'])
def input_capture():
	uploaded = request.files.get('image')
	if not uploaded:
		return jsonify({"ok": False, "error": "Missing image file in field 'image'"}), 400

	ext = os.path.splitext(uploaded.filename or '')[1].lower() or '.jpg'
	if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
		ext = '.jpg'

	ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
	filename = f"capture_{ts}{ext}"
	absolute_path = os.path.join(CAPTURE_DIR, filename)
	uploaded.save(absolute_path)

	with open(absolute_path, 'rb') as f:
		image_bytes = f.read()

	detection = model_ai.detect_product_from_image(image_bytes) or {}
	confidence = detection.get('confidence')

	db = get_session()
	try:
		product = _resolve_product_from_detection(db, detection)
		weight = None
		with input_state_lock:
			weight = latest_input_state['last_weight']
		estimated_qty, unit_weight = _calculate_estimated_quantity(db, product.id if product else None, weight)
	finally:
		db.close()

	with input_state_lock:
		latest_input_state['image_path'] = f"captures/{filename}"
		latest_input_state['captured_at'] = datetime.utcnow().isoformat()
		latest_input_state['detected_product_id'] = product.id if product else None
		latest_input_state['detected_product_name'] = product.name if product else None
		latest_input_state['ai_confidence'] = confidence
		latest_input_state['estimated_quantity'] = estimated_qty
		latest_input_state['unit_weight'] = unit_weight
		latest_input_state['message'] = 'Image captured and product detected' if product else 'Image captured, product not found'

	return jsonify({
		"ok": True,
		"detected_product_id": product.id if product else None,
		"detected_product_name": product.name if product else None,
		"confidence": confidence,
		"saved_image": f"/static/captures/{filename}",
		"estimated_quantity": estimated_qty,
		"unit_weight": unit_weight
	})


@app.route('/api/input/weight', methods=['POST'])
@app.route('/api/weight', methods=['POST'])
def input_weight():
	payload = request.get_json(silent=True) or {}
	weight_raw = payload.get('weight', request.form.get('weight'))
	print(f"[input_weight] payload={payload}")
	print(f"[input_weight] raw weight={weight_raw}")

	try:
		weight = float(weight_raw)
	except (TypeError, ValueError):
		print("[input_weight] invalid or missing weight")
		return jsonify({"ok": False, "error": "Invalid or missing weight"}), 400

	if weight < 0:
		print(f"[input_weight] rejected negative weight={weight}")
		return jsonify({"ok": False, "error": "Weight must be >= 0"}), 400

	with input_state_lock:
		product_id = latest_input_state['detected_product_id']
	print(f"[input_weight] starting with latest detected_product_id={product_id}")

	# take image using webcam and persist it so the store page can preview it
	img_bytes = model_ai.take_image()
	filename = f"weight_capture_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
	absolute_path = os.path.join(CAPTURE_DIR, filename)
	with open(absolute_path, 'wb') as f:
		f.write(img_bytes)

	# run the img through the ai to detect its name
	detection = model_ai.detect_product_from_image(img_bytes) or {}
	product_detected = (detection.get('name') or '').strip()
	print(f"[input_weight] detected product from image={product_detected!r}, detection={detection}")

	with input_state_lock:
		latest_input_state['image_path'] = f"captures/{filename}"
		latest_input_state['captured_at'] = datetime.utcnow().isoformat()
		latest_input_state['message'] = 'Weight captured and product checked'

	db = get_session()
	try:
		product = db.query(Product).filter(Product.name.ilike(product_detected)).first() if product_detected else None
		product_id = product.id if product else None
		print(f"[input_weight] db product match={getattr(product, 'name', None)!r}, product_id={product_id}")
		if product:
			latest_input_state['detected_product_id'] = product.id
			latest_input_state['detected_product_name'] = product.name
		else:
			latest_input_state['detected_product_id'] = None
			latest_input_state['detected_product_name'] = None
	finally:
		db.close()


	db = get_session()
	try:
		estimated_qty, unit_weight = _calculate_estimated_quantity(db, product_id, weight)
	finally:
		db.close()
	print(f"[input_weight] estimate updated estimated_qty={estimated_qty}, unit_weight={unit_weight}")

	with input_state_lock:
		latest_input_state['last_weight'] = weight
		latest_input_state['estimated_quantity'] = estimated_qty
		latest_input_state['unit_weight'] = unit_weight
		latest_input_state['message'] = 'Weight received and estimate updated'

	return jsonify({
		"ok": True,
		"weight": weight,
		"detected_product_id": product_id,
		"estimated_quantity": estimated_qty,
		"unit_weight": unit_weight
	})


@app.route('/api/input/status', methods=['GET'])
def input_status():
	with input_state_lock:
		state = dict(latest_input_state)

	if state.get('image_path'):
		state['image_url'] = url_for('static', filename=state['image_path'])
	else:
		state['image_url'] = None

	return jsonify({"ok": True, "state": state})


@app.route('/retrieve/plan', methods=['GET', 'POST'])
def retrieve_plan():
	plan = None
	error_message = None
	product_name_raw = (request.values.get('product_name') or '').strip()
	product_id_raw = (request.values.get('product_id') or '').strip()
	qty_raw = (request.values.get('quantity') or '').strip()

	if request.method == 'POST':
		db = get_session()
		try:
			product = None
			if product_name_raw:
				product = db.query(Product).filter(Product.name.ilike(product_name_raw)).first()
			elif product_id_raw:
				try:
					product = db.query(Product).get(int(product_id_raw))
				except (TypeError, ValueError):
					product = None

			try:
				qty = int(qty_raw)
				if qty < 1:
					raise ValueError
				if not product:
					raise ValueError
				plan = inventory.fifo_plan(product.id, qty)
			except (TypeError, ValueError):
				error_message = 'Please provide a valid product name and quantity.'
		finally:
			db.close()

	return render_template(
		'output.html',
		plan=plan,
		product_name=product_name_raw,
		product_id=product_id_raw,
		quantity=qty_raw,
		error_message=error_message
	)


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
			box = db.query(Box).filter_by(cell_id=cell.id).first() if cell else None
			product = db.query(Product).get(box.product_id) if box else None
		finally:
			db.close()
		if cell:
			robot.retrieve_box(product.id, cell.x, cell.y)
	inventory.apply_retrieval_plan(plan)
	executed_total = sum(item.get('take', 0) for item in plan)
	plan_summary = {
		'requested': executed_total,
		'fulfilled': executed_total,
		'remaining': 0,
		'plan': plan,
	}
	return render_template(
		'output.html',
		plan=plan_summary,
		product_name=request.form.get('product_name', ''),
		product_id=request.form.get('product_id', ''),
		quantity=request.form.get('quantity', ''),
		confirmation_message='Retrieval confirmed successfully.'
	)


if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5000, debug=True)

