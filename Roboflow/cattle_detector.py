"""
Cattle Disease Detector
Dedicated detector for general cattle diseases (mouth infection, FMD, etc.)
This is the SECOND model in the detection pipeline
"""
from inference_sdk import InferenceHTTPClient
import cv2
import os

class CattleDiseaseDetector:
    """
    Class to handle general cattle disease detection
    This runs as fallback when lumpy-skin model doesn't detect anything
    """
    
    def __init__(self, api_key="4IOLuSyX2FW86klgSqew"):
        """Initialize the cattle disease detection client"""
        self.client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=api_key
        )
        self.model_id = "cattle-disease-pnjdc/3"
    
    def detect_from_path(self, image_path):
        """
        Detect cattle diseases from an image file path
        
        Args:
            image_path: Path to the image file
            
        Returns:
            dict: Detection results with 'detected', 'confidence', 'disease', 'details'
        """
        if not os.path.exists(image_path):
            return {
                'detected': False,
                'confidence': 0.0,
                'disease': 'No Disease Detected',
                'error': 'Image file not found',
                'details': None
            }
        
        try:
            # Run inference on cattle disease model
            result = self.client.infer(image_path, model_id=self.model_id)
            
            # Parse results
            return self._parse_results(result)
        
        except Exception as e:
            return {
                'detected': False,
                'confidence': 0.0,
                'disease': 'No Disease Detected',
                'error': str(e),
                'details': None
            }
    
    def _parse_results(self, result):
        """
        Parse cattle disease detection results
        Handles various disease types: mouth infection, FMD, etc.
        """
        detected = False
        max_confidence = 0.0
        details = []
        disease_class = "No Disease Detected"
        
        # Case 1: Detection output (list of predictions with bounding boxes)
        if "predictions" in result and isinstance(result["predictions"], list):
            for pred in result["predictions"]:
                cls = pred.get("class", "")
                conf = pred.get("confidence", 0.0)
                
                # Detection threshold
                if conf > 0.5:
                    detected = True
                    if conf > max_confidence:
                        max_confidence = conf
                        disease_class = cls
                
                details.append({
                    'class': cls,
                    'confidence': round(conf, 3),
                    'x': int(pred.get('x', 0)),
                    'y': int(pred.get('y', 0)),
                    'width': int(pred.get('width', 0)),
                    'height': int(pred.get('height', 0))
                })
        
        # Case 2: Classification output (dictionary of diseases)
        elif "predictions" in result and isinstance(result["predictions"], dict):
            preds = result["predictions"]
            for disease_name, disease_data in preds.items():
                conf = disease_data.get("confidence", 0.0)
                if conf > 0.5:
                    detected = True
                    if conf > max_confidence:
                        max_confidence = conf
                        disease_class = disease_name
                    details.append({
                        'class': disease_name,
                        'confidence': round(conf, 3)
                    })
        
        # Filter out "normal", "healthy" or similar non-disease classes
        disease_name_lower = disease_class.lower()
        healthy_keywords = ['normal', 'healthy', 'no disease', 'fine', 'ok']
        if any(keyword in disease_name_lower for keyword in healthy_keywords):
            detected = False
            disease_class = "No Disease Detected"
        
        return {
            'detected': detected,
            'confidence': round(max_confidence, 3),
            'disease': disease_class,
            'details': details,
            'model_id': self.model_id,
            'raw_result': result
        }
    
    def draw_detections(self, image_path, output_path=None):
        """
        Draw detection boxes on image and save
        
        Args:
            image_path: Input image path
            output_path: Where to save annotated image (optional)
            
        Returns:
            tuple: (annotated_image_path, detection_result)
        """
        result = self.client.infer(image_path, model_id=self.model_id)
        img = cv2.imread(image_path)
        
        if img is None:
            raise ValueError("Could not load image")
        
        detection_result = self._parse_results(result)
        final_result = detection_result['disease']
        detected = detection_result['detected']
        
        # Draw bounding boxes if predictions exist
        if "predictions" in result and isinstance(result["predictions"], list):
            for pred in result["predictions"]:
                cls = pred["class"]
                conf = round(pred["confidence"], 2)
                
                if conf > 0.5:  # Detection threshold
                    x, y, w, h = int(pred["x"]), int(pred["y"]), int(pred["width"]), int(pred["height"])
                    
                    # Draw rectangle
                    color = (0, 0, 255) if detected else (0, 255, 0)  # Red for disease, green for normal
                    cv2.rectangle(img, (x - w//2, y - h//2), (x + w//2, y + h//2), color, 3)
                    
                    # Label
                    label = f"{cls} ({conf})"
                    cv2.putText(img, label, (x - w//2, y - h//2 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        # Add final result text at top
        text_color = (0, 255, 0) if not detected else (0, 0, 255)
        cv2.putText(img, final_result, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, text_color, 3)
        
        # Save annotated image
        if output_path is None:
            base_name = os.path.splitext(image_path)[0]
            output_path = f"{base_name}_cattle_detected.jpg"
        
        cv2.imwrite(output_path, img)
        
        return output_path, detection_result


# Standalone test function
if __name__ == "__main__":
    detector = CattleDiseaseDetector()
    
    # Test with an image
    test_image = "test_image.jpg"
    if os.path.exists(test_image):
        result = detector.detect_from_path(test_image)
        print("Detection Result:", result)
        
        # Draw and save
        annotated_path, _ = detector.draw_detections(test_image)
        print(f"Annotated image saved to: {annotated_path}")
    else:
        print(f"Test image '{test_image}' not found")
