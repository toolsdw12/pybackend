import os
import json
import time
from typing import Dict
from google import genai
from google.genai import types
from google.oauth2 import service_account
from ..base_assistant import BaseAssistant
import logging


logger = logging.getLogger(__name__)

class VertexAIAssistant(BaseAssistant):
    """VertexAI implementation of the AI assistant service"""
    
    def __init__(self):
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_VERTEX_LOCATION', 'us-west4')
        credentials_json = os.getenv('GOOGLE_CREDENTIALS')

        if not project_id or not credentials_json:
            raise ValueError("GOOGLE_CLOUD_PROJECT and GOOGLE_CREDENTIALS environment variables must be set")

        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )

        self.client = genai.Client(
            vertexai=True, project=project_id, location=location, credentials=credentials
        )
        self.default_model = "gemini-2.0-flash"
        
    async def extract_financial_data(self, ocr_text: str) -> Dict:
        """
        Extract financial data from OCR text using VertexAI
        
        Args:
            ocr_text: The OCR text to analyze
            
        Returns:
            Dictionary containing extracted financial data and timing information
        """
        start_time = time.time()
        logger.info("Starting financial data extraction with VertexAI")

        try:
            system_prompt = """You are a specialized financial data extraction expert, trained to analyze quarterly financial statements with precision. Your purpose is to transform unstructured financial text into structured, machine-readable data.
                                <process_instruction>
                                    STEP 1: READ THE COMPLETE DOCUMENT FROM START TO FINISH before attempting any extraction.
                                    STEP 2: ONLY AFTER reading the entire document, begin identifying financial metrics.
                                </process_instruction>
                                Your capabilities include:
                                1. Identifying and distinguishing between current quarter and year-over-year comparison data
                                2. Recognizing financial metrics across different terminology variations and formats
                                3. Handling complex numerical notations (lakhs, crores, millions) and negative value representations
                                4. Understanding the contextual relationships between financial line items
                                5. Extracting period information from various date formats and references
                                Extract data with accounting-level accuracy, maintaining the integrity of financial relationships. When information is genuinely missing, return null rather than attempting to derive values.
                                <note>
                                    1) if Profit/Loss for the Period not explicitly stated, calculate as: Profit/Loss After Tax from Ordinary Activities + Extraordinary Items (if any).
                                    2) Extra Ordinary Items include profit/loss from discontinued operations after tax.
                                </note>
                                <task>
                                    Extract these financial metrics from the PDF for both current quarter and year-over-year comparison:

                                    1. Revenue from Operations
                                    2. Other Income
                                    3. Depreciation
                                    4. Finance Costs
                                    5. Total Expenses
                                    6. Profit/Loss Before Exceptional Items and Tax
                                    7. Exceptional Items (check postive and negative values by checking Profit/Loss Before Exceptional Items and Tax and Profit/Loss After Tax from Ordinary Activities)
                                    8. Share of Profit/Loss of Associates
                                    9. Profit/Loss Before Tax
                                    10. Profit/Loss After Tax from Ordinary Activities
                                    11. Prior Year Adjustments (not related to tax)
                                    12. Extra Ordinary Items
                                    13. Profit/Loss for the Period
                                    14. Period Information (e.g., "Jan-Mar 2024")
                                </task>
                                <data_availability>
                                    When year-over-year quarter comparison data (same quarter from previous year) isn't explicitly provided in the document:
                                    1. Return null for all comparison metrics
                                    2. Do NOT substitute with previous quarter data or any other period's data
                                    3. Do NOT attempt to calculate or derive comparison values from other available information
                                    This ensures data integrity by preventing incorrect period comparisons that could lead to misleading financial analysis.
                                </data_availability>"""
            
            user_prompt = f"""<context>
                            Analyze the following quarterly financial statement text and extract the financial metrics for both current quarter and year-over-year comparison quarter.
                            </context>

                            Here is the quarterly financial result page OCR text:
                            {ocr_text}"""
            
            response = self.client.models.generate_content(
                model=self.default_model,
                contents = [
                    types.Content(
                        role="user",
                            parts=[
                                types.Part.from_text(text=user_prompt),
                            ],
                )],
                config=types.GenerateContentConfig(
                    max_output_tokens=2000,
                    temperature=0.1,
                    top_p=0.2,
                    response_mime_type="application/json",
                    system_instruction=[
                        types.Part.from_text(text=system_prompt),
                    ],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "currentQuarter": {
                                "type": "object",
                                "properties": {
                                    "revenueFromOps": { "type": "number", "nullable": True },
                                    "otherIncome": { "type": "number", "nullable": True },
                                    "depreciation": { "type": "number", "nullable": True },
                                    "financeCosts": { "type": "number", "nullable": True },
                                    "totalExpenses": { "type": "number", "nullable": True },
                                    "profitLossBeforeExceptionalItemsAndTax": { "type": "number", "nullable": True },
                                    "exceptionalItems": { "type": "number", "nullable": True },
                                    "shareOfPLOfAssociates": { "type": "number", "nullable": True },
                                    "profitLossBeforeTax": { "type": "number", "nullable": True },
                                    "profitLossAfterTaxFromOrdinaryActivities": { "type": "number", "nullable": True },
                                    "priorYearAdjustments": { "type": "number", "nullable": True },
                                    "extraOrdinaryItems": { "type": "number", "nullable": True },
                                    "profitLossForThePeriod": { "type": "number", "nullable": True },
                                    "period": { "type": "string", "nullable": False }
                                },
                                "required": [
                                    "revenueFromOps",
                                    "otherIncome",
                                    "depreciation",
                                    "financeCosts",
                                    "totalExpenses",
                                    "profitLossBeforeExceptionalItemsAndTax",
                                    "exceptionalItems",
                                    "shareOfPLOfAssociates",
                                    "profitLossBeforeTax",
                                    "profitLossAfterTaxFromOrdinaryActivities",
                                    "priorYearAdjustments",
                                    "extraOrdinaryItems",
                                    "profitLossForThePeriod",
                                    "period"
                                ],
                                "propertyOrdering": [
                                    "revenueFromOps",
                                    "otherIncome",
                                    "depreciation",
                                    "financeCosts",
                                    "totalExpenses",
                                    "profitLossBeforeExceptionalItemsAndTax",
                                    "exceptionalItems",
                                    "shareOfPLOfAssociates",
                                    "profitLossBeforeTax",
                                    "profitLossAfterTaxFromOrdinaryActivities",
                                    "priorYearAdjustments",
                                    "extraOrdinaryItems",
                                    "profitLossForThePeriod",
                                    "period"
                                ]
                            },
                            "previousYearQuarter": {
                                "type": "object",
                                "properties": {
                                    "revenueFromOps": { "type": "number", "nullable": True },
                                    "otherIncome": { "type": "number", "nullable": True },
                                    "depreciation": { "type": "number", "nullable": True },
                                    "financeCosts": { "type": "number", "nullable": True },
                                    "totalExpenses": { "type": "number", "nullable": True },
                                    "profitLossBeforeExceptionalItemsAndTax": { "type": "number", "nullable": True },
                                    "exceptionalItems": { "type": "number", "nullable": True },
                                    "shareOfPLOfAssociates": { "type": "number", "nullable": True },
                                    "profitLossBeforeTax": { "type": "number", "nullable": True },
                                    "profitLossAfterTaxFromOrdinaryActivities": { "type": "number", "nullable": True },
                                    "priorYearAdjustments": { "type": "number", "nullable": True },
                                    "extraOrdinaryItems": { "type": "number", "nullable": True },
                                    "profitLossForThePeriod": { "type": "number", "nullable": True },
                                    "period": { "type": "string", "nullable": False }
                                },
                                "required": [
                                    "revenueFromOps",
                                    "otherIncome",
                                    "depreciation",
                                    "financeCosts",
                                    "totalExpenses",
                                    "profitLossBeforeExceptionalItemsAndTax",
                                    "exceptionalItems",
                                    "shareOfPLOfAssociates",
                                    "profitLossBeforeTax",
                                    "profitLossAfterTaxFromOrdinaryActivities",
                                    "priorYearAdjustments",
                                    "extraOrdinaryItems",
                                    "profitLossForThePeriod",
                                    "period"
                                ],
                                "propertyOrdering": [
                                    "revenueFromOps",
                                    "otherIncome",
                                    "depreciation",
                                    "financeCosts",
                                    "totalExpenses",
                                    "profitLossBeforeExceptionalItemsAndTax",
                                    "exceptionalItems",
                                    "shareOfPLOfAssociates",
                                    "profitLossBeforeTax",
                                    "profitLossAfterTaxFromOrdinaryActivities",
                                    "priorYearAdjustments",
                                    "extraOrdinaryItems",
                                    "profitLossForThePeriod",
                                    "period"
                                ]
                            },
                            "revenue-format": {
                                "type": "string",
                                "enum": ["Lakhs", "Crores", "Millions"]
                            }
                        },
                        "required": ["currentQuarter", "previousYearQuarter", "revenue-format"],
                        "propertyOrdering": ["currentQuarter", "previousYearQuarter", "revenue-format"]
                    }
                )
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            structured_data = json.loads(response.text)
            
            return {
                "data": structured_data,
                "timing": {
                    "start": start_time,
                    "end": end_time,
                    "duration": processing_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error in financial data extraction: {str(e)}")
            raise 







