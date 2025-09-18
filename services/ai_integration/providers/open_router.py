import os
import json
import time
from typing import Dict
import openai
from ..base_assistant import BaseAssistant
import logging

logger = logging.getLogger(__name__)

class OpenRouterAssistant(BaseAssistant):
    """OpenRouter implementation of the AI assistant service"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.default_model = os.getenv("OpenRouter_AI_MODEL")
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        
            
    async def extract_financial_data(self, ocr_text: str) -> Dict:
        """
        Extract financial data from OCR text using OpenRouter
        
        Args:
            ocr_text: The OCR text to analyze
            
        Returns:
            Dictionary containing extracted financial data and timing information
        """
        start_time = time.time()
        logger.info("Starting financial data extraction with OpenRouter")
        
        try:
            system_prompt = """You are a financial analyst specializing in quarterly financial statements. 
Your primary task is to extract and structure financial metrics from company documents.
You must be precise and methodical in your analysis.
You understand financial reporting standards and number notation (lakhs, crores).
Important term clarifications:
- priorYearAdjustments: Adjustments to previous financial periods not related to tax.
- extraOrdinaryItems: Unusual one-time events (discontinued operations after tax also included).
You must respond in valid JSON format."""
            
            user_prompt = f"""You are analyzing a company's quarterly financial statement. Extract both the current quarter and its year-over-year comparison data.

Extract financial metrics for both the latest quarter and its year-over-year (YoY) comparison from the provided text.
If any information is not found, return null for that field.

Follow these extraction rules:
1. Period identification:
   - Look for month ranges (Jan-Mar, January-March, etc.)
   - Look for date ranges (1st Jan - 31st Mar, 01/01/2024 - 31/03/2024)
   - Three month period references
   - Identify both current and previous year periods

2. Value extraction:
   - Extract numbers in lakhs, crores, or millions notation
   - Handle numbers with commas and decimals
   - Use negative numbers for losses
   - Set to null if value not found

3. Output format:
   - Return the data in JSON format
   - Follow the exact structure specified in the schema

Text to analyze:
{ocr_text}"""
            
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "financial_data",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "currentQuarter": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "revenueFromOps": {"type": ["number", "null"]},
                                        "otherIncome": {"type": ["number", "null"]},
                                        "depreciation": {"type": ["number", "null"]},
                                        "financeCosts": {"type": ["number", "null"]},
                                        "totalExpenses": {"type": ["number", "null"]},
                                        "profitLossBeforeExceptionalItemsAndTax": {"type": ["number", "null"]},
                                        "exceptionalItems": {"type": ["number", "null"]},
                                        "shareOfPLOfAssociates": {"type": ["number", "null"]},
                                        "profitLossBeforeTax": {"type": ["number", "null"]},
                                        "profitLossAfterTaxFromOrdinaryActivities": {"type": ["number", "null"]},
                                        "priorYearAdjustments": {"type": ["number", "null"]},
                                        "extraOrdinaryItems": {"type": ["number", "null"]},
                                        "profitLossForThePeriod": {"type": ["number", "null"]},
                                        "period": {"type": "string"}
                                    },
                                    "required": [
                                        "revenueFromOps", "depreciation", "financeCosts", "otherIncome", "totalExpenses",
                                        "profitLossBeforeExceptionalItemsAndTax", "exceptionalItems",
                                        "shareOfPLOfAssociates", "profitLossBeforeTax", "profitLossAfterTaxFromOrdinaryActivities",
                                        "priorYearAdjustments", "extraOrdinaryItems", "profitLossForThePeriod",
                                        "period"
                                    ]
                                },
                                "previousYearQuarter": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "revenueFromOps": {"type": ["number", "null"]},
                                        "otherIncome": {"type": ["number", "null"]},
                                        "depreciation": {"type": ["number", "null"]},
                                        "financeCosts": {"type": ["number", "null"]},
                                        "totalExpenses": {"type": ["number", "null"]},
                                        "profitLossBeforeExceptionalItemsAndTax": {"type": ["number", "null"]},
                                        "exceptionalItems": {"type": ["number", "null"]},
                                        "shareOfPLOfAssociates": {"type": ["number", "null"]},
                                        "profitLossBeforeTax": {"type": ["number", "null"]},
                                        "profitLossAfterTaxFromOrdinaryActivities": {"type": ["number", "null"]},
                                        "priorYearAdjustments": {"type": ["number", "null"]},
                                        "extraOrdinaryItems": {"type": ["number", "null"]},
                                        "profitLossForThePeriod": {"type": ["number", "null"]},
                                        "period": {"type": "string"}
                                    },
                                    "required": [
                                        "revenueFromOps", "depreciation", "financeCosts", "otherIncome", "totalExpenses",
                                        "profitLossBeforeExceptionalItemsAndTax", "exceptionalItems",
                                        "shareOfPLOfAssociates", "profitLossBeforeTax", "profitLossAfterTaxFromOrdinaryActivities",
                                        "priorYearAdjustments", "extraOrdinaryItems", "profitLossForThePeriod",
                                        "period"
                                    ]
                                },
                                "revenue-format": {
                                    "type": "string",
                                    "enum": ["Lakhs", "Crores", "Millions"]
                                }
                            },
                            "required": ["currentQuarter", "previousYearQuarter", "revenue-format"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            #logger.info(f"Response: {response}")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # For chat.completions.create(), the response structure is:
            # response.choices[0].message.content contains the JSON string
            structured_data = json.loads(response.choices[0].message.content)
            
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