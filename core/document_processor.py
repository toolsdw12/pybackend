from typing import Dict, Optional
import pymupdf
import logging
from services.analysis.text_analyzer import TextAnalyzer
from services.pdf.pymupdf_text_extractor import PyMuPDFTextExtractor
from services.images.result_image_creator import ResultImageCreator
from services.storage.s3_service import S3Service
from services.notifications.telegram_notification_service import TelegramNotificationService
from services.notifications.extraction_status_formatter import ExtractionStatusFormatter
from core.financial_analyzer import FinancialAnalyzer
from services.ocr_integration.ocr_factory import OCRFactory, OCRServiceType
from services.analysis.result_type_config import ResultTypeConfig
import config
import time
import json

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.text_extractor = PyMuPDFTextExtractor()
        self.text_analyzer = TextAnalyzer()
        self.result_image_creator = ResultImageCreator()
        self.financial_analyzer = FinancialAnalyzer()
        
        # Initialize AWS S3 service if configured
        if config.AWS_ENABLED and config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            self.s3_service = S3Service()
        else:
            self.s3_service = None
            if config.AWS_ENABLED:
                logger.warning("AWS integration is enabled but credentials are missing")
                
        # Initialize Telegram service if configured and not in testing mode
        if config.TELEGRAM_ENABLED and config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID and not config.TESTING_MODE:
            self.telegram_service = TelegramNotificationService(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
            logger.info("Telegram service initialized for production mode")
        else:
            self.telegram_service = None
            if config.TESTING_MODE:
                logger.info("Testing mode enabled - Telegram notifications will be bypassed")
            elif config.TELEGRAM_ENABLED:
                logger.warning("Telegram integration is enabled but bot token or chat ID is missing")

    async def process_document(
        self,
        content: bytes,
        filename: str,
        ocr_service: Optional[OCRServiceType] = None,
        stock_data: Optional[str] = None,
        python_start: float = None
    ) -> Dict:
        """
        Process a document through the following steps:
        1. Extract text using PyMuPDF
        2. Analyze for financial terms
        3. Apply OCR if needed
        4. Create result PDF if result pages found
        5. Send result PDF to S3 if configured
        
        Args:
            content: The document content in bytes
            filename: The name of the file
            ocr_service: Optional OCR service to use
            stock_data: Optional stock data JSON string for result type configuration
            python_start: Start time of Python processing from time.perf_counter()
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Parse stock data if provided
            stock_data_dict = json.loads(stock_data) if stock_data else {}
            # Extract node.js elapsed time if provided
            node_elapsed_ms = stock_data_dict.get('nodeElapsedMs', 0)
            
            # Create result type configuration from stock data
            result_type_config = ResultTypeConfig.from_stock_data(stock_data)
            logger.info(f"Using result type configuration: {result_type_config}")
            
            # Use context manager to ensure PDF document is properly closed and reused
            with pymupdf.open(stream=content, filetype="pdf") as pdf_document:
                # Extract text from PDF using PyMuPDF
                pages = await self.text_extractor.extract_text(pdf_document)
                
                # Analyze pages for financial terms and classification
                analysis_result = self.text_analyzer.analyze_document(pages, result_type_config)
                logger.info(f"Pages analyzed. Found {len(analysis_result['pages'])} pages.")
                
                # Store whether OCR was needed and initialize duration
                needs_ocr = analysis_result['needs_ocr']
                ocr_duration = None
                processing_time = None
                
                # If OCR is needed, process with selected OCR service
                if needs_ocr:
                    logger.info(f"OCR processing required, using {ocr_service.value}")
                    ocr_start = time.perf_counter()
                    ocr_service_instance = OCRFactory.get_ocr_service(ocr_service)
                    ocr_pages = await ocr_service_instance.process_document(content, filename)
                    ocr_duration = time.perf_counter() - ocr_start

                    # Re-analyze the OCR processed pages
                    analysis_result = self.text_analyzer.analyze_document(ocr_pages, result_type_config)
                    logger.info(f"OCR pages analyzed. Found {len(analysis_result['pages'])} pages.")
                
                # Create a new PDF with only result pages
                result_page_number = [p["page_number"] for p in analysis_result['pages'] if p["classification"] == "Results Page"]
                logger.info(f"Found {len(result_page_number)} result pages")
                # Check if any pages were processed with OCR
                ocr_applied = any(page.get('isOcr', False) for page in analysis_result['pages'])
                
                # Create result image if result pages found
                result_image_bytes = None
                s3_url = None
                result_page_generation_duration = None
                if result_page_number:
                    # Take only the first result page for image creation
                    result_page_generation_start = time.perf_counter()
                    result_image_bytes = self.result_image_creator.create_result_image(pdf_document, result_page_number[0])
                    result_page_generation_duration = time.perf_counter() - result_page_generation_start

                    # Start financial analysis and get results
                    financial_analysis_result = await self.financial_analyzer.start_analysis(
                        result_pdf_bytes=result_image_bytes,
                        filename=filename,
                        stock_data_dict=stock_data_dict,
                        python_start=python_start
                    )

                    # Handle S3 upload and prepare message for either Telegram or testing
                    s3_url = None
                    if result_image_bytes:
                        if config.TELEGRAM_USE_S3_URL and self.s3_service:
                            # Try to upload to S3 first
                            s3_url = self.s3_service.upload_file(result_image_bytes, filename)
                            if s3_url:
                                logger.info(f"Result image uploaded to S3 successfully: {s3_url}")
                            else:
                                logger.error("Failed to upload result image to S3")
                                # Fallback to direct Telegram upload if S3 fails
                                config.TELEGRAM_USE_S3_URL = False
                        
                        # Calculate total processing time in seconds
                        processing_time = round((node_elapsed_ms / 1000) + (time.perf_counter() - python_start), 2)
                        
                        # Format the message (available for both Telegram and testing mode)
                        caption = ExtractionStatusFormatter.format_extraction_report(
                            filename, 
                            analysis_result['pages'], 
                            result_page_number,
                            s3_url=s3_url if config.TELEGRAM_USE_S3_URL else None,
                            processing_time=processing_time
                        )
                        
                        # Send to Telegram or log for testing mode
                        if self.telegram_service:
                            if config.TELEGRAM_USE_S3_URL and s3_url:
                                # Send only the message with S3 URL
                                if self.telegram_service.send_message(caption, parse_mode="HTML"):
                                    logger.info("S3 URL sent to Telegram successfully")
                                else:
                                    logger.error("Failed to send S3 URL to Telegram")
                            else:
                                # Send file directly to Telegram
                                if self.telegram_service.send_document_bytes(result_image_bytes, filename, caption):
                                    logger.info("Result image sent to Telegram successfully")
                                else:
                                    logger.error("Failed to send result image to Telegram")
                        elif config.TESTING_MODE:
                            # Log what would be sent to Telegram in testing mode
                            logger.info("TESTING MODE: Would have sent Telegram message:")
                            logger.info(f"TESTING MODE: Caption: {caption}")
                            if config.TELEGRAM_USE_S3_URL and s3_url:
                                logger.info(f"TESTING MODE: Would have sent S3 URL message")
                            else:
                                logger.info(f"TESTING MODE: Would have sent image document: {filename}")
                else:
                    # No result pages found even after OCR (if applied)
                    error_message = f"⚠️ ERROR: Not able to find the result page for {filename}. Please check configuration."
                    
                    # Add additional info if OCR was applied
                    if ocr_applied:
                        error_message += f"\n\n🔍 OCR was applied using {ocr_service.value} but no result pages were found."
                    
                    if self.telegram_service:
                        if self.telegram_service.send_message(error_message):
                            logger.info("No result pages notification sent to Telegram successfully")
                        else:
                            logger.error("Failed to send no result pages notification to Telegram")
                    elif config.TESTING_MODE:
                        # Log what would be sent to Telegram in testing mode
                        logger.info("TESTING MODE: Would have sent error message:")
                        logger.info(f"TESTING MODE: Error message: {error_message}")
            
            # Prepare the response data
            response_data = {
                "status": "success",
                "message": analysis_result['message'],
                "pages": analysis_result['pages'],
                "ocr_service": ocr_service.value if ocr_applied else None,
                "s3_url": s3_url,
                "sent_to_telegram": self.telegram_service is not None and result_image_bytes is not None,
                "processing_time": processing_time if result_page_number else None,
                "needs_ocr": needs_ocr,
                "ocr_duration": ocr_duration,
                "result_page_generation_duration": result_page_generation_duration
            }
            
            # Include financial analysis results if available
            if result_page_number and 'financial_analysis_result' in locals():
                if financial_analysis_result and financial_analysis_result.get('status') == 'success':
                    response_data["financial_analysis"] = financial_analysis_result.get('analysis_results')
                elif financial_analysis_result:
                    response_data["financial_analysis_error"] = financial_analysis_result.get('message', 'Financial analysis failed')
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise 