
import cv2
import numpy as np
from ultralytics import YOLO

# Load your custom model weights
model = YOLO("best.pt")


def take_image():
	cap = cv2.VideoCapture(1)
	if not cap.isOpened():
		raise RuntimeError("Could not open webcam.")

	ret, frame = cap.read()
	cap.release()
	cv2.destroyAllWindows()

	if not ret or frame is None:
		raise RuntimeError("Failed to capture image.")

	# Return image bytes so it can be used with detect_product_from_image
	encoded, buffer = cv2.imencode(".jpg", frame)
	if not encoded:
		raise RuntimeError("Failed to encode image.")
	return buffer.tobytes()


def detect_product_from_image(image_bytes=None):
	# Run detection with 50% confidence threshold
	if image_bytes is None:
		raise ValueError("image_bytes is required.")
	frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
	if frame is None:
		raise RuntimeError("Failed to decode image bytes.")
	results = model(frame, conf=0.5)[0]
	count_a = 0
	count_b = 0
# Count detected pieces
	for box in results.boxes:
		cls_id = int(box.cls[0])
		class_name = model.names[cls_id]

		if class_name == "Piece_A":
			count_a += 1
		elif class_name == "Piece_B":
			count_b += 1
	
	print("Count A:", count_a)
	print("Count B:", count_b)

	if count_a == 0 and count_b == 0:
		return {"name": "XX"}
	if count_a > count_b:
		return {"name": "A"}
	else:
		return {"name": "B"}
	
