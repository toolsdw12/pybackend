import os
import json
import time
from typing import Dict
import anthropic
from ..base_assistant import BaseAssistant
import logging

logger = logging.getLogger(__name__)

class AnthropicAssistant(BaseAssistant):
    """Anthropic implementation of the AI assistant service"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.default_model = "claude-3-7-sonnet-latest"
            
    async def extract_financial_data(self, ocr_data: Dict) -> Dict:
        """
        Extract financial data directly from PDF bytes using Anthropic
        
        Args:
            pdf_bytes: The PDF bytes to analyze
            
        Returns:
            Dictionary containing extracted financial data and timing information
        """
        start_time = time.time()
        logger.info("Starting financial data extraction with Anthropic AI")
        
        try:
            system_prompt = """You are a financial analyst specializing in quarterly financial statements. 
Your primary task is to extract and structure financial metrics from company documents.
You must be precise and methodical in your analysis.
You understand financial reporting standards and number notation (lakhs, crores)."""
            
            user_prompt = f"""<task>
Extract financial metrics for both the latest quarter and its year-over-year (YoY) comparison from the provided PDF.
If any information is not found, return null for that field.
</task>

<output_format>
{{
    "currentQuarter": {{
        "revenueFromOps": "number or null",
        "depreciation": "number or null",
        "financeCosts": "number or null",
        "otherIncome": "number or null",
        "profitLossBeforeExceptionalItemsAndTax": "number or null",
        "exceptionalItems": "number or null",
        "shareOfPLOfAssociates": "number or null",
        "profitLossBeforeTax": "number or null",
        "profitLossAfterTaxFromOrdinaryActivities": "number or null",
        "priorYearAdjustments": "number or null",
        "extraOrdinaryItems": "number or null",
        "profitLossForThePeriod": "number or null",
        "period": "string" (e.g., 'Jan-Mar 2024', '1st Jan - 31st Mar 2024', etc.)
    }},
    "previousYearQuarter": {{
        "revenueFromOps": "number or null",
        "depreciation": "number or null",
        "financeCosts": "number or null",
        "otherIncome": "number or null",
        "profitLossBeforeExceptionalItemsAndTax": "number or null",
        "exceptionalItems": "number or null",
        "shareOfPLOfAssociates": "number or null",
        "profitLossBeforeTax": "number or null",
        "profitLossAfterTaxFromOrdinaryActivities": "number or null",
        "priorYearAdjustments": "number or null",
        "extraOrdinaryItems": "number or null",
        "profitLossForThePeriod": "number or null",
        "period": "string" (e.g., 'Jan-Mar 2023', '1st Jan - 31st Mar 2023', etc.)
    }},
    "revenue-format": "string" (e.g., 'Lakhs', 'Crores', 'Millions')
}}
</output_format>

<extraction_rules>
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

3. Output requirements:
   - Return ONLY a valid JSON object
   - No additional text or explanations
   - No markdown formatting
   - Must be valid JSON that can be parsed directly
</extraction_rules>

<ocr_data>
{ocr_data}
</ocr_data>
"""
            
            response = await self.client.messages.create(
                model=self.default_model,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.1
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Clean the response text before parsing
            response_text = response.content[0].text
            # Remove any markdown code block syntax
            response_text = response_text.replace("```json\n", "").replace("```\n", "")
            # Remove any leading/trailing whitespace
            response_text = response_text.strip()
            
            # Parse the response content
            try:
                structured_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing AI response: {str(e)}")
                logger.error(f"Raw response text: {response_text}")
                raise ValueError("Failed to parse AI response as JSON")
            
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













