from services.notifications.financial_report_builder import FinancialReportBuilder
from services.notifications.estimates_calculator import EstimatesCalculator
from services.notifications.estimates_report_builder import EstimatesReportBuilder
from typing import Dict, Any
import logging
from services.ocr_integration.ocr_factory import OCRFactory, OCRServiceType
import asyncio
from services.notifications.telegram_notification_service import TelegramNotificationService
from services.ai_integration.assistant_factory import AssistantFactory
import config
from dataclasses import dataclass
logger = logging.getLogger(__name__)

@dataclass
class AnalysisParams:
    """Parameters for financial analysis"""
    pdf_bytes: bytes  # Contains single page PDF
    filename: str
    stock_data_dict: Dict[str, Any] = None  
    python_start: float = None

class FinancialAnalyzer:
    def __init__(self):
        self.message_aggregator = FinancialReportBuilder()
        self.estimates_calculator = EstimatesCalculator()
        self.estimates_report_builder = EstimatesReportBuilder()
        
        # Initialize AI assistant
        try:
            self.ai_assistant = AssistantFactory.get_assistant(config.DEFAULT_AI_SERVICE)
            logger.info(f"Initialized {config.DEFAULT_AI_SERVICE} AI assistant")
        except Exception as e:
            logger.error(f"Failed to initialize AI assistant: {str(e)}")
            self.ai_assistant = None
            
        # Initialize Telegram service if configured and not in testing mode
        if config.TELEGRAM_ENABLED and config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID and not config.TESTING_MODE:
            self.telegram_service = TelegramNotificationService(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
            logger.info("FinancialAnalyzer Telegram service initialized for production mode")
        else:
            self.telegram_service = None
            if config.TESTING_MODE:
                logger.info("FinancialAnalyzer: Testing mode enabled - financial analysis Telegram notifications will be bypassed")

    async def start_analysis(
        self,
        result_pdf_bytes: bytes,
        filename: str = "result.pdf",
        stock_data_dict: Dict[str, Any] = None,
        python_start: float = None
    ) -> Dict:
        """
        Start the analysis process and return the results.
        
        Args:
            result_pdf_bytes: The PDF content in bytes
            filename: The name of the file
            stock_data_dict: Optional stock data dictionary for additional analysis context
            python_start: Start time of Python processing from time.perf_counter()
            
        Returns:
            Dictionary containing analysis results or None if analysis fails
        """
        params = AnalysisParams(
            pdf_bytes=result_pdf_bytes,
            filename=filename,
            stock_data_dict=stock_data_dict,
            python_start=python_start
        )
        # Process and return results instead of background processing
        return await self._process_and_notify(params)

    async def _process_and_notify(self, params: AnalysisParams) -> Dict:
        """
        Process the document, send notifications, and return results.
        """
        try:
            # Process the page
            analysis_result = await self.process_result_page(params)

            if analysis_result["status"] == "error":
                logger.error(f"Analysis failed: {analysis_result['message']}")
                return analysis_result

            return analysis_result

        except Exception as e:
            logger.error(f"Error in financial analysis processing: {str(e)}")
            error_message = f"⚠️ Error analyzing {params.filename}: {str(e)}"
            if self.telegram_service:
                await self.telegram_service.send_message(error_message)
            elif config.TESTING_MODE:
                logger.info("TESTING MODE: Would have sent financial analysis error message:")
                logger.info(f"TESTING MODE: Error message: {error_message}")
            
            return {
                "status": "error",
                "message": f"Financial analysis failed: {str(e)}"
            }

    async def process_result_page(self, params: AnalysisParams) -> Dict:
        """
        Process result page by sending PDF bytes directly to AI model.
        """
        try:
            logger.info(f"Processing PDF directly with AI model for file {params.filename}")
            analysis_results = await self._analyze_with_ai(params.pdf_bytes, params.stock_data_dict, params.python_start)
            
            return {
                "status": "success",
                "analysis_results": analysis_results
            }
                
        except Exception as e:
            logger.error(f"Error processing result page for {params.filename}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process result page: {str(e)}"
            }

    async def _analyze_with_ai(self, pdf_bytes: bytes, stock_data_dict: Dict[str, Any] = None, python_start: float = None) -> Dict:
        """
        Analyze PDF bytes directly with AI model and format results for Telegram.
        
        Args:
            pdf_bytes: The PDF content in bytes
            stock_data_dict: Optional stock data dictionary for additional analysis context
            python_start: Start time of Python processing from time.perf_counter()
        """
        try:
            if not self.ai_assistant:
                raise ValueError("AI assistant not initialized")
    
            # Track result page OCR timing
            import time
            result_page_ocr_start = time.perf_counter()
            ocr_service = OCRFactory.get_ocr_service(OCRServiceType.TEXTRACT_SERVICE)
            ocr_data = await ocr_service.process_document(pdf_bytes)
            result_page_ocr_end = time.perf_counter()
            result_page_ocr_duration = result_page_ocr_end - result_page_ocr_start;
            
            logger.info(f"Result page OCR duration: {result_page_ocr_duration} seconds")
            logger.info(f"OCR data: {ocr_data}")
          
            # Track AI analysis timing
            ai_start_time = time.perf_counter()
            analysis_result = await self.ai_assistant.extract_financial_data(ocr_data)
            ai_end_time = time.perf_counter()
            ai_duration = ai_end_time - ai_start_time
            
            # Add processing time and timing data to the result
            if stock_data_dict:
                stock_data_dict['pythonStart'] = python_start
                analysis_result["data"]["stockData"] = stock_data_dict
            
            # Add detailed timing information
            analysis_result["data"]["timing"] = {
                "result_page_ocr_duration": result_page_ocr_duration,
                "ai_analysis_duration": ai_duration,
                "total_financial_analysis_duration": ai_duration + result_page_ocr_duration
            }

            # Calculate estimates if stock data is available
            if stock_data_dict.get("estimates"):
                try:
                    # Prepare input data for estimates calculation
                    input_data = self.estimates_calculator.prepare_input_data(
                        analysis_result["data"],
                        stock_data_dict
                    )
                    
                    # Calculate estimates
                    estimates_result = self.estimates_calculator.calculate_estimates(input_data)
                    
                    # Format estimates data
                    formatted_estimates = self.estimates_report_builder.format_estimates_data(estimates_result)
                    
                    # Add both raw and formatted estimates to the analysis result
                    analysis_result["data"]["estimates"] = estimates_result
                    analysis_result["data"]["formatted_estimates"] = formatted_estimates
                    
                    logger.info("Successfully calculated and formatted estimates")
                except Exception as e:
                    logger.error(f"Error calculating estimates: {str(e)}")
                    # Continue with the analysis even if estimates calculation fails
  
            # Format the data for both Telegram/logging and frontend response
            formatted_financial = self.message_aggregator.format_financial_data(analysis_result["data"])
            
            # Add formatted messages to the result for frontend display
            analysis_result["data"]["formatted_financial_message"] = formatted_financial
            
            # If Telegram service is available, send the formatted data
            if self.telegram_service:
                # Send financial data
                self.telegram_service.send_message(formatted_financial, parse_mode="HTML")
                
                # Send estimates if available
                if "formatted_estimates" in analysis_result["data"]:
                    self.telegram_service.send_message(analysis_result["data"]["formatted_estimates"], parse_mode="HTML")
            elif config.TESTING_MODE:
                logger.info("TESTING MODE: Would have sent financial analysis message:")
                logger.info(f"TESTING MODE: Financial data message: {formatted_financial}")
                
                # Log estimates if available
                if "formatted_estimates" in analysis_result["data"]:
                    logger.info("TESTING MODE: Would have sent estimates message:")
                    logger.info(f"TESTING MODE: Estimates message: {analysis_result['data']['formatted_estimates']}")
            
            return analysis_result["data"]
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return {
                "status": "error",
                "message": f"AI analysis failed: {str(e)}"
            } 