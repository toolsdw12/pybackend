from abc import ABC, abstractmethod
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class BaseOCR(ABC):
    """Abstract base class for OCR services"""
    
    @abstractmethod
    async def process_document(self, content: bytes, filename: str) -> List[Dict]:
        """
        Process a document using OCR service
        
        Args:
            content: The document content in bytes
            filename: The name of the file
            
        Returns:
            List of dictionaries containing page information with the following structure:
            {
                "page_number": int,
                "text": str,
                "isRelevant": bool,
                "foundTerms": List[str],
                "foundTermsCount": int,
                "uniqueTermsCount": int,
                "classification": str,
                "isOcr": bool
            }
        """
        pass 