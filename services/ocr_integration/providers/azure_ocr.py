import os
import logging
from io import BytesIO
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from fastapi import HTTPException
from typing import List, Dict
from ..base_ocr import BaseOCR

logger = logging.getLogger(__name__)

class AzureOCR(BaseOCR):
    def __init__(self):
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not endpoint or not key:
            raise ValueError("Azure Document Intelligence credentials are not properly set.")

        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    async def process_document(self, content: bytes, filename: str) -> List[Dict]:
        """
        Process a document using Azure Document Intelligence Read Model
        """
        try:
            logger.info(f"Starting Azure Document Intelligence OCR for file: {filename}")
            
            # Create the request with the document content
            request = AnalyzeDocumentRequest(bytes_source=content)
            
            # Start the document analysis operation
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                body=request
            )
            
            # Wait for the operation to complete
            result = poller.result()

            #logger.info(f"Azure Document Intelligence OCR result: {result}")

            # Process results into structured output
            pages = []
            for page in result.pages:
                lines = [line.content for line in page.lines]
                text = "\n".join(lines)
                
                pages.append({
                    "page_number": page.page_number,
                    "text": text,
                    "isRelevant": False,
                    "foundTerms": [],
                    "foundTermsCount": 0,
                    "uniqueTermsCount": 0,
                    "classification": "Not Relevant",
                    "isOcr": True
                })

            logger.info(f"Azure Document Intelligence OCR complete: {len(pages)} pages processed.")
            return pages

        except Exception as e:
            logger.error(f"Error in Azure Document Intelligence OCR: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed: {str(e)}"
            ) 