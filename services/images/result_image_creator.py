import logging
import pymupdf

logger = logging.getLogger(__name__)

class ResultImageCreator:
    def __init__(self):
        pass

    def create_result_image(self, source_pdf: pymupdf.Document, result_page_num: int) -> bytes:
        """Create an image from a single PDF page and return as bytes
        
        Args:
            source_pdf: Source PDF document to extract page from
            result_page_num: Page number (1-based indexing)
            
        Returns:
            bytes of the created PNG image or None if page could not be rendered
        """
        try:
            # Convert 1-based page number to 0-based for PyMuPDF
            page_index = result_page_num - 1
            
            # Load the specific page
            page = source_pdf.load_page(page_index)
            
            # Create pixmap with default settings
            pixmap = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)

            # Convert to PNG bytes
            image_bytes = pixmap.tobytes("png")
            
            return image_bytes

        except Exception as e:
            logger.error(f"Error creating image from page {result_page_num}: {str(e)}")
            return None