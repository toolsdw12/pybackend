"""
OCR Integration service package for handling optical character recognition functionality.
"""
from .base_ocr import BaseOCR
from .ocr_factory import OCRFactory

__all__ = ['BaseOCR', 'OCRFactory'] 