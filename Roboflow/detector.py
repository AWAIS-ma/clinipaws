"""
Skin Disease Detector
Django-integrated version for livestock disease prediction
Supports multiple Roboflow models for comprehensive disease detection
"""
from inference_sdk import InferenceHTTPClient
import cv2
import json
import os

class SkinDiseaseDetector:
    """
    Class to handle Skin Disease detection using multiple AI models
    """
    
    def __init__(self, api_key="4IOLuSyX2FW86klgSqew"):
        """Initialize the detection client with multiple models"""
        self.client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=api_key
        )
        # Multiple model IDs for comprehensive detection
        self.models = [
            "lumpy-skin-wab9r/1",      # Lumpy skin disease model
            "cattle-disease-pnjdc/3"    # General cattle disease model
        ]
    
    def detect_from_path(self, image_path):
        """
        Detect Skin Disease from an image file path using multiple models
        
        Args:
            image_path: Path to the image file
            
        Returns:
            dict: Combined detection results from all models
        """
        if not os.path.exists(image_path):
            return {
                'detected': False,
                'confidence': 0.0,
                'error': 'Image file not found',
                'details': None
            }
        
        try:
            all_results = []
            
            # Run inference on all models
            for model_id in self.models:
                result = self.client.infer(image_path, model_id=model_id)
                parsed = self._parse_results(result, model_id)
                all_results.append(parsed)
            
            # Combine results from all models
            return self._combine_results(all_results)
        
        except Exception as e:
            return {
                'detected': False,
                'confidence': 0.0,
                'error': str(e),
                'details': None
            }
    
    def _parse_results(self, result, model_id):
        """Parse AI API results from a single model"""
        detected = False
        max_confidence = 0.0
        details = []
        disease_class = "No Disease Detected"
        
        # Case 1: Detection output (list of predictions)
        if "predictions" in result and isinstance(result["predictions"], list):
            for pred in result["predictions"]:
                cls = pred.get("class", "")
                conf = pred.get("confidence", 0.0)
                
                # Look for any skin disease indicators
                if conf > 0.5:  # Threshold for detection
                    detected = True
                    max_confidence = max(max_confidence, conf)
                    disease_class = cls
                
                details.append({
                    'class': cls,
                    'confidence': round(conf, 3),
                    'x': int(pred.get('x', 0)),
                    'y': int(pred.get('y', 0)),
                    'width': int(pred.get('width', 0)),
                    'height': int(pred.get('height', 0))
                })
        
        # Case 2: Classification output (dictionary)
        elif "predictions" in result and isinstance(result["predictions"], dict):
            preds = result["predictions"]
            for disease_name, disease_data in preds.items():
                conf = disease_data.get("confidence", 0.0)
                if conf > 0.5:
                    detected = True
                    max_confidence = max(max_confidence, conf)
                    disease_class = disease_name
                    details.append({
                        'class': disease_name,
                        'confidence': round(conf, 3)
                    })
        
        return {
            'detected': detected,
            'confidence': round(max_confidence, 3),
            'disease': disease_class,
            'details': details,
            'model_id': model_id,
            'raw_result': result
        }
    
    def _combine_results(self, all_results):
        """
        Combine results from multiple models with priority-based fallback
        
        Priority Logic:
        1. Check lumpy-skin model first for Lumpy Skin Disease
        2. If not detected, check cattle-disease model for other diseases (mouth infection, etc.)
        3. Use whichever model detects a disease
        """
        detected = False
        max_confidence = 0.0
        disease_class = "No Disease Detected"
        combined_details = []
        
        # Separate results by model type
        lumpy_result = None
        cattle_result = None
        
        for result in all_results:
            if 'lumpy-skin' in result.get('model_id', ''):
                lumpy_result = result
            elif 'cattle-disease' in result.get('model_id', ''):
                cattle_result = result
        
        # Helper function to check if result is actually a disease (not normal/healthy)
        def is_actual_disease(result):
            if not result or not result.get('detected'):
                return False
            disease_name = result.get('disease', '').lower()
            # Filter out normal, healthy, or no disease indicators
            healthy_keywords = ['normal', 'healthy', 'no disease', 'fine', 'ok']
            return not any(keyword in disease_name for keyword in healthy_keywords)
        
        # Priority 1: Check lumpy-skin model
        if is_actual_disease(lumpy_result):
            detected = True
            max_confidence = lumpy_result['confidence']
            disease_class = lumpy_result['disease']
            combined_details = lumpy_result['details'] if lumpy_result['details'] else []
            print(f"DEBUG: Lumpy model detected: {disease_class} ({max_confidence})")
        
        # Priority 2: If lumpy didn't detect, check cattle-disease model
        elif is_actual_disease(cattle_result):
            detected = True
            max_confidence = cattle_result['confidence']
            disease_class = cattle_result['disease']
            combined_details = cattle_result['details'] if cattle_result['details'] else []
            print(f"DEBUG: Cattle model detected: {disease_class} ({max_confidence})")
        
        # Priority 3: No disease detected by either model
        else:
            detected = False
            disease_class = "No Disease Detected"
            # Combine details from both for reference
            for result in all_results:
                if result['details']:
                    combined_details.extend(result['details'])
            print("DEBUG: No disease detected by either model")
        
        return {
            'detected': detected,
            'confidence': round(max_confidence, 3),
            'disease': disease_class,
            'details': combined_details,
            'all_model_results': all_results
        }
    
    def draw_detections(self, image_path, output_path=None):
        """
        Draw detection boxes on image and save
        Uses all models and combines results
        
        Args:
            image_path: Input image path
            output_path: Where to save annotated image (optional)
            
        Returns:
            tuple: (annotated_image_path, detection_result)
        """
        img = cv2.imread(image_path)
        
        if img is None:
            raise ValueError("Could not load image")
        
        all_results = []
        all_predictions = []
        
        # Run inference on all models
        for model_id in self.models:
            result = self.client.infer(image_path, model_id=model_id)
            parsed = self._parse_results(result, model_id)
            all_results.append(parsed)
            
            # Collect predictions for drawing
            if "predictions" in result and isinstance(result["predictions"], list):
                for pred in result["predictions"]:
                    pred['model_id'] = model_id  # Tag with model source
                    all_predictions.append(pred)
        
        # Combine results
        combined_result = self._combine_results(all_results)
        
        final_result = combined_result['disease']
        detected = combined_result['detected']
        
        # Draw all predictions
        for pred in all_predictions:
            cls = pred["class"]
            conf = round(pred["confidence"], 2)
            
            if conf > 0.5:  # Detection threshold
                x, y, w, h = int(pred["x"]), int(pred["y"]), int(pred["width"]), int(pred["height"])
                
                # Draw rectangle
                cv2.rectangle(img, (x - w//2, y - h//2), (x + w//2, y + h//2), (0, 255, 0), 3)
                # Label
                label = f"{cls} ({conf})"
                cv2.putText(img, label, (x - w//2, y - h//2 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Add final result text
        color = (0, 255, 0) if not detected else (0, 0, 255)
        cv2.putText(img, final_result, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        
        # Save annotated image
        if output_path is None:
            base_name = os.path.splitext(image_path)[0]
            output_path = f"{base_name}_detected.jpg"
        
        cv2.imwrite(output_path, img)
        
        return output_path, combined_result
