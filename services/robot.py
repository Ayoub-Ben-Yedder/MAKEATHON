import time
import requests
from config import ROBOT_SIMULATE

url = "http://10.97.193.40:8765/pick"
def store_box(product_id , x, y):
	print("Sending to Blender : ", product_id, x, y)
	if(product_id == 1):
		product = "A"
	elif (product_id == 2):
		product = "B"
	else:
		product = "XX"
	data = {
		"product": product,
		"x": x,
		"y": y
	}
	try:
		response = requests.post(url, json=data)
		if response.ok:
			print("Sent Successfully")
		else:
			print(f"Failed to send to Blender: status={response.status_code}, body={response.text}")
	except requests.RequestException as e:
		print(f"Request error when sending to Blender: {e}")
	return True

def retrieve_box(product_id, x, y):
	print("Sending to Blender : ", product_id, x, y)
	data = {
		"product": product_id,
		"x": x,
		"y": y
	}
	try:
		response = requests.post(url, json=data)
		if response.ok:
			print("Sent Successfully")
		else:
			print(f"Failed to send to Blender: status={response.status_code}, body={response.text}")
	except requests.RequestException as e:
		print(f"Request error when sending to Blender: {e}")
	return True
