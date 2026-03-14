from inference_sdk import InferenceHTTPClient
import cv2
import json

# -----------------------------
# Initialize Roboflow Client
# -----------------------------
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="4IOLuSyX2FW86klgSqew"
)

# -----------------------------
# Input Image
# -----------------------------
image_path = "images.jpg"

# -----------------------------
# Run inference
# -----------------------------
result = CLIENT.infer(image_path, model_id="lumpy-skin-wab9r/1")

print("\n--- PREDICTION RESULT ---")
print(json.dumps(result, indent=4))

# -----------------------------
# Handle Classification OR Detection
# -----------------------------
final_result = "No Lumpy Skin Disease"  # default

# Case 1: Detection output (list of predictions)
if "predictions" in result and isinstance(result["predictions"], list):
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Could not load image.")
        exit()
    
    for pred in result["predictions"]:
        cls = pred["class"]
        conf = round(pred["confidence"], 2)
        x, y, w, h = int(pred["x"]), int(pred["y"]), int(pred["width"]), int(pred["height"])
        
        # Draw rectangle
        cv2.rectangle(img, (x - w//2, y - h//2), (x + w//2, y + h//2), (0, 255, 0), 2)
        # Label
        cv2.putText(img, f"{cls} ({conf})", (x - w//2, y - h//2 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Update final result if "Lumpy" detected
        if "Lumpy" in cls:
            final_result = "Lumpy Skin Disease Detected"
    
    # Show image
    cv2.putText(
        img, final_result, (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
        (0, 255, 0) if "No" in final_result else (0, 0, 255),
        2
    )
    cv2.imshow("Result", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Case 2: Classification output (dictionary)
elif "predictions" in result and isinstance(result["predictions"], dict):
    preds = result["predictions"]
    lumpy_conf = preds.get("Lumpy", {}).get("confidence", 0.0)
    threshold = 0.5
    if lumpy_conf > threshold:
        final_result = "Lumpy Skin Disease Detected"

print("\nFINAL RESULT:", final_result)
