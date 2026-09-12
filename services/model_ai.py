
import cv2


def take_image():
	cap = cv2.VideoCapture(0)
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
	# placeholder: in a real system, run a model on image bytes
	# return a product name and confidence
	return {"name": "A", "confidence": 0.95}
