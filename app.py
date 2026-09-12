from flask import Flask, render_template, request, redirect, url_for, jsonify
from config import SECRET_KEY
from database import init_db, get_session
from services import inventory, robot, ai
from models.cell import Cell
from models.box import Box
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
	# list products and boxes
	products = inventory.list_products()
	db = get_session()
	try:
		boxes = [b.as_dict() for b in db.query(Box).all()]
	finally:
		db.close()
	return render_template('admin.html', products=products, boxes=boxes)


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

