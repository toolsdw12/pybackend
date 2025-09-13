from enum import Enum
from typing import Dict, Type
from .base_ocr import BaseOCR
from .providers.azure_ocr import AzureOCR
from .providers.textract_ocr import TextractOCR

class OCRServiceType(Enum):
    AZURE_DOCUMENT_INTELLIGENCE = "azure_document_intelligence"
    TEXTRACT_SERVICE = "textract"

class OCRFactory:
    _services: Dict[OCRServiceType, Type[BaseOCR]] = {
        OCRServiceType.AZURE_DOCUMENT_INTELLIGENCE: AzureOCR,
        OCRServiceType.TEXTRACT_SERVICE: TextractOCR
    }

    @classmethod
    def get_ocr_service(cls, service_type: OCRServiceType) -> BaseOCR:
        """
        Get an instance of the specified OCR service
        
        Args:
            service_type: The type of OCR service to instantiate
            
        Returns:
            An instance of the specified OCR service
            
        Raises:
            ValueError: If the service type is not supported
        """
        if service_type not in cls._services:
            raise ValueError(f"Unsupported OCR service type: {service_type}")
            
        return cls._services[service_type]() 