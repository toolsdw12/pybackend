import logging
from typing import List, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class ExtractionStatusFormatter:
    @staticmethod
    def format_extraction_report(filename: str, pages: List[dict], result_pages: List[int], s3_url: Optional[str] = None, processing_time: Optional[float] = None) -> str:
        """
        Format the extraction report message for Telegram
        
        Args:
            filename: Name of the processed file
            pages: List of all pages in the document
            result_pages: List of page numbers that were extracted
            s3_url: Optional S3 URL for the uploaded file
            processing_time: Optional processing time in seconds
            
        Returns:
            str: Formatted message string
        """
        try:
            # Get total pages and result pages
            total_pages = len(pages)
            result_page_str = ", ".join(map(str, result_pages))
            
            # Determine method used
            method = "OCR" if any(page.get('isOcr', False) for page in pages) else "PyMuPDF"
            
            message = [
                "✅ EXTRACTION COMPLETE",
                "---------------------------------------------------",
                "",
                f"📄 {filename}",
                "",
                f"📍 Page {result_page_str} of {total_pages}",
                "",
                f"🔍 {method}"
            ]
            
            # Add processing time if available
            if processing_time is not None:
                message.append(f"\n⏱ Processing Time: {processing_time:.2f}s")
            
            # Add S3 URL if available
            if s3_url:
                message.append(f"\n📄 Details: <a href='{s3_url}'>View Result</a>")
            
            # Add current time in IST
            utc_now = datetime.now(pytz.utc)
            ist_tz = pytz.timezone("Asia/Kolkata")
            ist_time = utc_now.astimezone(ist_tz)
            formatted_time = ist_time.strftime("%I:%M:%S %p · %d %b %y")

            message.append(f"\n<code>{formatted_time}</code>")
                
            return "\n".join(message)
            
        except Exception as e:
            logger.error(f"Error formatting extraction report: {str(e)}")
            return f"📄 {filename}\n📍 Page {result_page_str} of {total_pages}" 