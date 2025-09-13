from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FinancialCalculations:
    """Utility class for shared financial calculations"""
    
    @staticmethod
    def calculate_operating_income(current: Dict) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Operating Income and Operating Income %
        
        Args:
            current: Dictionary containing financial data for a quarter
            
        Returns:
            Tuple of (operating_income, operating_income_percent)
        """
        if current["revenueFromOps"] is None or current["totalExpenses"] is None:
            return None, None
        
        # Add negative shareOfPLOfAssociates to totalExpenses if it exists and is negative
        adjusted_total_expenses = current["totalExpenses"]
        if current.get("shareOfPLOfAssociates") is not None and current["shareOfPLOfAssociates"] < 0:
            adjusted_total_expenses += abs(current["shareOfPLOfAssociates"])
        
        operating_income = current["revenueFromOps"] - (adjusted_total_expenses - 
            (current["financeCosts"] or 0) - (current["depreciation"] or 0))  
        
        operating_income_percent = (operating_income / current["revenueFromOps"] * 100) if current["revenueFromOps"] != 0 else None
        
        return operating_income, operating_income_percent

    @staticmethod
    def calculate_growth(current: Optional[float], previous: Optional[float]) -> Tuple[str, str]:
        """
        Calculate growth percentage and direction
        
        Args:
            current: Current value
            previous: Previous value
            
        Returns:
            Tuple of (growth_percentage, growth_arrow)
        """
        if not previous or previous == 0:
            return "N/A", ""
            
        # Use absolute value of previous to determine correct growth direction
        growth = ((current - previous) / abs(previous) * 100)
        arrow = "↑" if current > previous else "↓" if current < previous else ""
        return f"{abs(growth):.2f}", arrow

    @staticmethod
    def calculate_tax_percentage(pbt: Optional[float], pat: Optional[float]) -> Optional[float]:
        """
        Calculate tax percentage
        
        Args:
            pbt: Profit before tax
            pat: Profit after tax
            
        Returns:
            Tax percentage or None if calculation not possible
        """
        if pbt is None or pat is None or pbt == 0:
            return None
        return ((pbt - pat) / abs(pbt)) * 100

    @staticmethod
    def calculate_exceptional_items(current: Dict) -> Optional[float]:
        """
        Calculate exceptional items with proper sign based on PBT comparison
        
        Args:
            current: Dictionary containing financial data for a quarter
            
        Returns:
            Exceptional items value with proper sign or None if data is missing
        """
        if (current.get("profitLossBeforeTax") is None or 
            current.get("profitLossBeforeExceptionalItemsAndTax") is None or
            current.get("exceptionalItems") is None):
            return None
            
        # Get absolute value of exceptional items
        abs_exceptional_items = abs(current["exceptionalItems"])
        
        # Determine sign based on PBT comparison
        if current["profitLossBeforeTax"] > current["profitLossBeforeExceptionalItemsAndTax"]:
            return abs_exceptional_items  # Positive sign
        else:
            return -abs_exceptional_items  # Negative sign

    @staticmethod
    def calculate_total_other_income(quarter_data: Dict) -> float:
        """
        Calculate total other income including all components
        
        Args:
            quarter_data: Dictionary containing financial data for a quarter
            
        Returns:
            Total other income value
        """
        total = sum(
            (quarter_data.get(key) or 0)
            for key in ["otherIncome", "extraOrdinaryItems"]
        )
        
        # Add shareOfPLOfAssociates only if it's positive
        share_of_pl = quarter_data.get("shareOfPLOfAssociates")
        if share_of_pl is not None and share_of_pl > 0:
            total += share_of_pl
            
        # Add exceptional items with proper sign
        exceptional_items = FinancialCalculations.calculate_exceptional_items(quarter_data)
        if exceptional_items is not None:
            total += exceptional_items
            
        return total

    @staticmethod
    def calculate_adjusted_pbt(quarter_data: Dict) -> Optional[float]:
        """
        Calculate adjusted PBT including extraordinary items
        
        Args:
            quarter_data: Dictionary containing financial data for a quarter
            
        Returns:
            Adjusted PBT value or None if data is missing
        """
        if quarter_data["profitLossBeforeTax"] is None:
            return None
            
        adjusted_pbt = quarter_data["profitLossBeforeTax"]
        if quarter_data.get("extraOrdinaryItems") is not None:
            adjusted_pbt += quarter_data["extraOrdinaryItems"]
            
        return adjusted_pbt 