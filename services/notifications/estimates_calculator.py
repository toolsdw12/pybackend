from typing import Dict, Optional
import logging
from datetime import datetime
from .financial_calculations import FinancialCalculations

logger = logging.getLogger(__name__)

class EstimatesCalculator:
    """Service for calculating estimates and classifications"""
    
    def __init__(self):
        pass

    def _convert_to_crores(self, value: Optional[float], revenue_format: str) -> Optional[float]:
        """
        Convert a value to crores based on the revenue format
        
        Args:
            value: The value to convert
            revenue_format: The format of the value ("Lakhs", "Crores", or "Millions")
            
        Returns:
            Value converted to crores
        """
        if value is None:
            return None
            
        if revenue_format == "Lakhs":
            return value / 100  # 1 crore = 100 lakhs
        elif revenue_format == "Millions":
            return value / 10  # 1 crore = 10 million (approximately)
        else:  # Already in crores
            return value

    def _validate_required_fields(self, data: Dict, path: str, required_fields: Dict[str, str]) -> None:
        """
        Validate that all required fields exist and are not null
        
        Args:
            data: Dictionary to validate
            path: Path to the data for error messages
            required_fields: Dictionary of field names and their descriptions
            
        Raises:
            ValueError: If any required field is missing or null
        """
        for field, description in required_fields.items():
            if field not in data or data[field] is None:
                raise ValueError(f"{description} in {path} is missing or null")

    def prepare_input_data(self, financial_data: Dict, stock_data: Dict) -> Dict:
        """
        Prepare input data for estimates calculation by combining financial data and stock data
        
        Args:
            financial_data: Dictionary containing financial data with currentQuarter
            stock_data: Dictionary containing stock data with estimates
            
        Returns:
            Dictionary containing prepared input data for estimates calculation
            
        Raises:
            ValueError: If any required field is missing or null
        """
        try:
            # Validate financial data
            if "currentQuarter" not in financial_data:
                raise ValueError("Current quarter data is missing")
                
            current_quarter = financial_data["currentQuarter"]
            revenue_format = financial_data.get("revenue-format", "Crores")
            
            # Convert only the specific fields needed for operating income calculation
            fields_to_convert = ["revenueFromOps", "totalExpenses", "depreciation", "financeCosts"]
            converted_quarter = current_quarter.copy()
            for field in fields_to_convert:
                if field in current_quarter:
                    converted_quarter[field] = self._convert_to_crores(current_quarter[field], revenue_format)
            
            # Validate required financial fields
            self._validate_required_fields(converted_quarter, "currentQuarter", {
                "revenueFromOps": "Revenue from operations",
                "totalExpenses": "Total expenses",
                "depreciation": "Depreciation",
                "financeCosts": "Finance costs"
            })
            
            # Validate stock data
            if "estimates" not in stock_data:
                raise ValueError("Estimates data is missing")
                
            estimates = stock_data["estimates"]
            
            # Validate baseline sales data
            if "baselineSalesData" not in estimates:
                raise ValueError("Baseline sales data is missing")
            self._validate_required_fields(estimates["baselineSalesData"], "baselineSalesData", {
                "previousSalesNumber": "Previous sales number"
            })
            
            # Validate sales growth estimates
            if "salesGrowthEstimates" not in estimates:
                raise ValueError("Sales growth estimates are missing")
            self._validate_required_fields(estimates["salesGrowthEstimates"], "salesGrowthEstimates", {
                "lowestSalesGrowthPercent": "Lowest sales growth estimate",
                "highestSalesGrowthPercent": "Highest sales growth estimate"
            })
            
            # Validate margin estimates
            if "marginEstimatesValue" not in estimates:
                raise ValueError("Margin estimates are missing")
            self._validate_required_fields(estimates["marginEstimatesValue"], "marginEstimatesValue", {
                "lowestMarginEstimate": "Lowest margin estimate",
                "highestMarginEstimate": "Highest margin estimate"
            })
            
            # Calculate actual margin using shared calculation with converted values
            actual_profit, actual_margin = FinancialCalculations.calculate_operating_income(converted_quarter)
            if actual_margin is None:
                raise ValueError("Could not calculate operating margin")
            
            # Get estimates data
            baseline_sales = estimates["baselineSalesData"]
            sales_growth = estimates["salesGrowthEstimates"]
            margin_estimates = estimates["marginEstimatesValue"]
            
            return {
                "stockData": {
                    "stockName": stock_data.get("stockName", ""),
                    "nodeElapsedMs": financial_data.get("nodeElapsedMs", 0),
                    "pythonStart": financial_data.get("pythonStart", 0)
                },
                "lowestEstimate": sales_growth["lowestSalesGrowthPercent"],
                "highestEstimate": sales_growth["highestSalesGrowthPercent"],
                "previousSales": baseline_sales["previousSalesNumber"],
                "actualSales": converted_quarter["revenueFromOps"],
                "lowestMarginEstimate": margin_estimates["lowestMarginEstimate"],
                "highestMarginEstimate": margin_estimates["highestMarginEstimate"],
                "actualMargin": actual_margin,
                "actualProfit": actual_profit
            }
            
        except Exception as e:
            logger.error(f"Error preparing input data: {str(e)}")
            raise

    def _calculate_boundaries(self, lowest: float, highest: float) -> Dict[str, float]:
        """Calculate classification boundaries based on lowest and highest estimates"""
        span = highest - lowest
        return {
            "below_avg": lowest,
            "avg_good": lowest + (span * 0.50),
            "good_vgood": lowest + (span * 0.80),
            "vgood_blockbuster": lowest + (span * 0.90)
        }

    def _classify_value(self, value: float, boundaries: Dict[str, float], highest_estimate: float) -> Dict:
        """Classify a value based on boundaries and highest estimate"""
        range_span = highest_estimate - boundaries["below_avg"]
        position_in_range = ((value - boundaries["below_avg"]) / range_span) * 100
        
        if value < boundaries["below_avg"]:
            classification = "Below Avg"
        elif value >= boundaries["below_avg"] and value < boundaries["avg_good"]:
            classification = "Avg"
        elif value >= boundaries["avg_good"] and value < boundaries["good_vgood"]:
            classification = "Good"
        elif value >= boundaries["good_vgood"] and value < boundaries["vgood_blockbuster"]:
            classification = "Very Good"
        else:
            classification = "Blockbuster"
            
        return {
            "classification": classification,
            "positionInRange": position_in_range
        }

    def _validate_inputs(self, inputs: Dict) -> Dict:
        """Validate input parameters"""
        if inputs["previousSales"] <= 0:
            return {"valid": False, "message": "Previous Sales Number must be greater than zero."}
            
        if inputs["lowestEstimate"] >= inputs["highestEstimate"]:
            return {"valid": False, "message": "Highest Sales Growth Estimate must be greater than Lowest Sales Growth Estimate."}
            
        if inputs["lowestEstimate"] < 0 or inputs["highestEstimate"] < 0:
            return {"valid": False, "message": "Sales Growth estimates cannot be negative."}
            
        if inputs["lowestMarginEstimate"] >= inputs["highestMarginEstimate"]:
            return {"valid": False, "message": "Highest Margin Estimate must be greater than Lowest Margin Estimate."}
            
        return {"valid": True}

    def calculate_estimates(self, inputs: Dict) -> Dict:
        """
        Calculate estimates and classifications based on input parameters
        
        Args:
            inputs: Dictionary containing the following parameters:
            {
                "stockData": {
                    "stockName": string,
                    "nodeElapsedMs": number,
                    "pythonStart": number
                },
                "lowestEstimate": number,
                "highestEstimate": number,
                "previousSales": number,
                "actualSales": number,
                "lowestMarginEstimate": number,
                "highestMarginEstimate": number,
                "actualMargin": number
            }
            
        Returns:
            Dictionary containing calculated estimates and classifications
        """
        try:
            # Validate inputs
            validation = self._validate_inputs(inputs)
            if not validation["valid"]:
                raise ValueError(validation["message"])

            # Calculate actual growth percentage
            actual_growth = ((inputs["actualSales"] - inputs["previousSales"]) / inputs["previousSales"]) * 100

            # Calculate sales boundaries and classification
            sales_boundaries = self._calculate_boundaries(inputs["lowestEstimate"], inputs["highestEstimate"])
            sales_classification = self._classify_value(actual_growth, sales_boundaries, inputs["highestEstimate"])

            # Calculate margin boundaries and classification
            margin_boundaries = self._calculate_boundaries(inputs["lowestMarginEstimate"], inputs["highestMarginEstimate"])
            margin_classification = self._classify_value(inputs["actualMargin"], margin_boundaries, inputs["highestMarginEstimate"])

            # Calculate profit estimates
            lowest_estimated_sales = inputs["previousSales"] * (1 + (inputs["lowestEstimate"] / 100))
            highest_estimated_sales = inputs["previousSales"] * (1 + (inputs["highestEstimate"] / 100))
            lowest_estimated_profit = lowest_estimated_sales * (inputs["lowestMarginEstimate"] / 100)
            highest_estimated_profit = highest_estimated_sales * (inputs["highestMarginEstimate"] / 100)

            # Calculate profit boundaries and classification
            profit_boundaries = self._calculate_boundaries(lowest_estimated_profit, highest_estimated_profit)
            profit_classification = self._classify_value(inputs["actualProfit"], profit_boundaries, highest_estimated_profit)

            return {
                "stockData": inputs["stockData"],
                "sales": {
                    "actualGrowthPercentage": actual_growth,
                    "classification": sales_classification["classification"],
                    "positionInRange": sales_classification["positionInRange"],
                    "boundaries": sales_boundaries
                },
                "margin": {
                    "actualMarginValue": inputs["actualMargin"],
                    "classification": margin_classification["classification"],
                    "positionInRange": margin_classification["positionInRange"],
                    "boundaries": margin_boundaries
                },
                "profit": {
                    "actualProfitValue": inputs["actualProfit"],
                    "classification": profit_classification["classification"],
                    "positionInRange": profit_classification["positionInRange"],
                    "boundaries": profit_boundaries
                }
            }

        except Exception as e:
            logger.error(f"Error calculating estimates: {str(e)}")
            raise 