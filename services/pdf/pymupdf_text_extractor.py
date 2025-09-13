import pymupdf
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class PyMuPDFTextExtractor:
    def __init__(self):
        pass

    async def extract_text(self, pdf_document: pymupdf.Document):
        """Extract text from PDF document object using PyMuPDF"""
        try:
            pages = []
            for page_num in range(len(pdf_document)):
                try:
                    page = pdf_document[page_num]
                    text = page.get_text()
                    pages.append({
                        "page_number": page_num + 1,
                        "text": text
                    })
                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num + 1}: {str(e)}")
                    continue
            
            if not pages:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
            return pages

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid PDF file")