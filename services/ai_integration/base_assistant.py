from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAssistant(ABC):
    """Abstract base class for AI assistant services"""
    
    @abstractmethod
    async def extract_financial_data(self, ocr_text: str) -> Dict:
        """
        Extract financial data from OCR text
        
        Args:
            ocr_text: The OCR text to analyze
            
        Returns:
            Dictionary containing extracted financial data
        """
        pass 