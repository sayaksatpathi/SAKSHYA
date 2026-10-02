import pytest
import numpy as np
from backend.ai.ocr.plate_ocr import PlateOCR

def test_anpr():
    ocr = PlateOCR()
    if not ocr.is_available():
        pytest.skip("EasyOCR not installed, skipping ANPR test")

    # Generate a synthetic plate image
    # Note: testing EasyOCR might actually download its model! 
    # For a deterministic offline test, we might mock it if needed.
    import cv2
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(img, "MH12AB1234", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

    plate_box = [0, 0, 300, 100]
    result = ocr.recognize(img, plate_box)
    
    # We might not get exactly MH12AB1234 due to synthesis, but it should return something
    assert result is not None, "OCR should return a result"
    assert "raw_text" in result
    assert "normalized_text" in result
    assert "confidence" in result

    # Test normalization
    assert " " not in result["normalized_text"]
    assert "-" not in result["normalized_text"]
    
    # Test no plate
    blank_img = np.zeros((100, 300, 3), dtype=np.uint8)
    blank_result = ocr.recognize(blank_img, plate_box)
    assert blank_result is None, "Blank image should return no OCR result"
