import time
from config import ROBOT_SIMULATE

def move_to(x, y):
	# simulate movement
	if ROBOT_SIMULATE:
		time.sleep(0.1)
		return True
	# real implementation would send to ESP32
	return True

def store_box(box_id, x, y):
	# In a real system, instruct ESP32 to store the box
	success = move_to(x, y)
	return success

def retrieve_box(box_id, x, y, quantity):
	success = move_to(x, y)
	return success
