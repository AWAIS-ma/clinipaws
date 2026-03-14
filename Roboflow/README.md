# Roboflow Image Detection Module

This module provides Lumpy Skin Disease detection using Roboflow API.

## Files

- `detector.py` - Django-integrated detector class
- `detect_lumpy_skin.py` - Standalone detection script

## Usage

### Standalone Script
```bash
python Roboflow/detect_lumpy_skin.py
```

### Django Integration
```python
from Roboflow.detector import LumpySkinDetector

detector = LumpySkinDetector()
result = detector.detect_from_path("path/to/image.jpg")
print(result)
```

## API Key
Configured for Roboflow account with model ID: `lumpy-skin-wab9r/1`
