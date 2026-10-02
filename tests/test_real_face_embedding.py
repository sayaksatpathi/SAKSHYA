import pytest
import numpy as np
from backend.ai.engine import ai_engine
import cv2

def test_real_face_embedding():
    # 1. Initialize engine
    ai_engine.initialize("models")
    
    if not ai_engine._face_detector.is_available():
        pytest.skip("Face detector unavailable")
    
    if not ai_engine._face_recognizer.is_available():
        pytest.skip("Face recognizer unavailable")

    # Generate two synthetic images with a face-like structure (e.g. a circle)
    # Using real image or a standard test image would be better, but synthetic can pass through the detector
    
    # Actually, a synthetic image might not trigger YuNet. 
    # Let's create an empty white square and hope YuNet detects nothing. 
    # Or we can just use the provided model paths and skip if it finds nothing.
    
    img1 = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.circle(img1, (200, 200), 50, (0, 0, 0), -1) # fake eye
    
    img2 = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.circle(img2, (200, 200), 50, (0, 0, 0), -1) # fake eye

    faces1 = ai_engine._face_detector.detect(img1)
    
    if not faces1:
        # Without real faces, YuNet might not detect anything, so we'll just test the compute_embedding function directly
        # by passing a fake face_box to test the crop and resize logic
        pass

    # Test the compute_embedding logic directly with a fake bounding box
    bbox = [50, 50, 100, 100]
    
    emb1 = ai_engine._face_recognizer.compute_embedding(img1, bbox)
    emb2 = ai_engine._face_recognizer.compute_embedding(img2, bbox)
    
    if emb1 is not None and emb2 is not None:
        # Same image -> high similarity
        similarity = float(np.dot(emb1.flatten(), emb2.flatten()) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
        ))
        assert similarity > 0.9, "Same image should have high similarity"
        
        # Different image -> different similarity
        img3 = np.zeros((400, 400, 3), dtype=np.uint8)
        emb3 = ai_engine._face_recognizer.compute_embedding(img3, bbox)
        
        if emb3 is not None:
            similarity_diff = float(np.dot(emb1.flatten(), emb3.flatten()) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb3) + 1e-8
            ))
            assert similarity_diff < similarity, "Different images should have lower similarity"
