import logging
import pymupdf
import io

logger = logging.getLogger(__name__)

class ResultPDFCreator:
    def __init__(self):
        pass

    def create_result_pdf(self, source_pdf: pymupdf.Document, result_pages: list, close_source: bool = False) -> bytes:
        """Create a new PDF with specified pages and return as bytes
        
        Args:
            source_pdf: Source PDF document to copy pages from
            result_pages: List of page numbers to copy (1-based indexing)
            close_source: If True, close the source_pdf document after use (default: False)
            
        Returns:
            bytes of the created PDF or None if no pages could be copied
        """
        if not result_pages:
            return None

        try:
            # Use context manager directly to ensure the PDF document is properly closed
            with pymupdf.open() as result_doc:
                # Convert 1-based page numbers to 0-based for PyMuPDF
                valid_pages = [page_num - 1 for page_num in result_pages if 1 <= page_num <= source_pdf.page_count]
                
                if not valid_pages:
                    logger.warning("No valid pages to copy")
                    return None

                for page_num in valid_pages:
                    try:
                        result_doc.insert_pdf(source_pdf, from_page=page_num, to_page=page_num)
                        logger.info(f"Successfully copied page {page_num + 1}")
                    except Exception as e:
                        logger.error(f"Error copying page {page_num + 1}: {str(e)}")
                        continue

                if result_doc.page_count > 0:
                    # Save to memory instead of disk
                    pdf_bytes = result_doc.tobytes()
                    logger.info(f"Result PDF created with {result_doc.page_count} pages")
                    return pdf_bytes
                
                logger.warning("No pages were successfully copied to result PDF")
                return None

        except Exception as e:
            logger.error(f"Error creating result PDF: {str(e)}")
            return None
        finally:
            # Close the source document if requested
            if close_source and source_pdf:
                try:
                    source_pdf.close()
                    logger.debug("Source PDF document closed")
                except Exception as e:
                    logger.warning(f"Error closing source PDF: {str(e)}")