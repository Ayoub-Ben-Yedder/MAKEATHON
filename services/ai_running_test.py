import cv2
from ultralytics import YOLO

# Load your custom model weights
model = YOLO("best.pt")

# Open PC webcam
cap = cv2.VideoCapture(1)

print("Starting live detection... Press 'q' to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Run detection with 50% confidence threshold
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

    # Display counts on screen
    status_text = f"Piece A: {count_a} | Piece B: {count_b}"
    annotated_frame = results.plot()

    cv2.putText(annotated_frame, status_text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.imshow("Hackathon Object Detector", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()