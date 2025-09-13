from dataclasses import dataclass
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ResultTypeConfig:
    """Configuration for result page type detection"""
    result_type: str  # "single_page" or "multi_page"
    multi_page_type: Optional[str] = None  # "consolidated" or "standalone" (only used when result_type is "multi_page")

    @classmethod
    def from_stock_data(cls, stock_data: str) -> 'ResultTypeConfig':
        """
        Create a ResultTypeConfig instance from stock data JSON string
        
        Args:
            stock_data: JSON string containing stock data with resultPageConfig
            
        Returns:
            ResultTypeConfig instance
            
        Raises:
            ValueError: If stock_data is invalid or missing required fields
        """
        if not stock_data:
            logger.warning("No stock data provided, using default configuration")
            return cls(result_type="single_page")
            
        try:
            data = json.loads(stock_data)
            result_config = data.get('resultPageConfig', {})
            
            # Map the input type to our internal types
            type_mapping = {
                "Single": "single_page",
                "Multi": "multi_page"
            }
            
            result_type = type_mapping.get(result_config.get('type', 'Single'), "single_page")
            
            # For multi-page, determine the sub-type
            multi_page_type = None
            if result_type == "multi_page":
                page_type = result_config.get('pageType', 'Consolidated')
                multi_page_type = page_type.lower() if page_type else "consolidated"
                
            return cls(
                result_type=result_type,
                multi_page_type=multi_page_type
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid stock data JSON: {str(e)}")
            raise ValueError("Invalid stock data format")
        except Exception as e:
            logger.error(f"Error parsing stock data: {str(e)}")
            raise ValueError("Failed to parse stock data") 