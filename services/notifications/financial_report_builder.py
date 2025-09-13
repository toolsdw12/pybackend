from typing import Dict, List, Union, Optional
import logging
import time
from datetime import datetime
import pytz
from .financial_calculations import FinancialCalculations

logger = logging.getLogger(__name__)

class FinancialReportBuilder:
    """Service for aggregating and formatting financial data messages"""
    
    def __init__(self):
        pass

    def _format_number(self, num: Optional[float], revenue_format: str) -> str:
        """Helper function to format numbers with commas and convert to crores"""
        if num is None:
            return "N/A"
        
        # Convert to crores based on the Revenue-Format
        value_in_crores = num
        if revenue_format == "Lakhs":
            value_in_crores = num / 100  # 1 crore = 100 lakhs
        elif revenue_format == "Millions":
            value_in_crores = num / 10  # 1 crore = 10 million (approximately)
        
        return f"{value_in_crores:,.2f}"

    def _format_extraordinary_items(self, current: Dict, previous: Dict, revenue_format: str) -> str:
        """Helper function to format extraordinary items with YOY comparison"""
        extra_items_current = current.get('extraOrdinaryItems')
        if extra_items_current is None:
            return ""
            
        extra_items_prev = previous.get('extraOrdinaryItems')
        if extra_items_prev is not None:
            return f"Extraordinary Items: {self._format_number(extra_items_current, revenue_format)} Cr (vs {self._format_number(extra_items_prev, revenue_format)} Cr YOY)"
        return f"Extraordinary Items: {self._format_number(extra_items_current, revenue_format)} Cr"

    def _format_metric_line(self, label: str, value: Optional[float], growth_data: tuple, revenue_format: str) -> str:
        """
        Format a metric line with value and growth
        
        Args:
            label: The metric label
            value: The metric value
            growth_data: Tuple of (growth_percentage, growth_arrow)
            revenue_format: The revenue format to use for number formatting
            
        Returns:
            Formatted metric line
        """
        return f"{label}: {self._format_number(value, revenue_format)} Cr ({growth_data[1]} {growth_data[0]}%)"

    def format_financial_data(self, financial_data: Dict) -> str:
        """
        Format financial data into a readable message
        
        Args:
            financial_data: Dictionary containing financial data with the following structure:
            {
                "currentQuarter": {
                    "revenueFromOps": number or null,
                    "depreciation": number or null,
                    "financeCosts": number or null,
                    "otherIncome": number or null,
                    "profitLossBeforeExceptionalItemsAndTax": number or null,
                    "exceptionalItems": number or null,
                    "shareOfPLOfAssociates": number or null,
                    "profitLossBeforeTax": number or null,
                    "profitLossAfterTaxFromOrdinaryActivities": number or null,
                    "priorYearAdjustments": number or null,
                    "extraOrdinaryItems": number or null,
                    "profitLossForThePeriod": number or null,
                    "period": string
                },
                "previousYearQuarter": {
                    # Same structure as currentQuarter
                },
                "revenue-format": string,
                "processingTime": number
            }
            
        Returns:
            Formatted string containing the financial data
        """
        try:
            # Calculate growth rates only for metrics that will be displayed
            metrics_to_calculate = [
                "revenueFromOps", "depreciation", "financeCosts", "otherIncome",
                "profitLossBeforeExceptionalItemsAndTax", "profitLossBeforeTax",
                "profitLossAfterTaxFromOrdinaryActivities", "profitLossForThePeriod"
            ]
            
            growth_data = {
                metric: FinancialCalculations.calculate_growth(
                    financial_data["currentQuarter"][metric],
                    financial_data["previousYearQuarter"][metric]
                )
                for metric in metrics_to_calculate
            }
            
            # Calculate adjusted PBT (including extraordinary items)
            current_adjusted_pbt = FinancialCalculations.calculate_adjusted_pbt(financial_data["currentQuarter"])
            previous_adjusted_pbt = FinancialCalculations.calculate_adjusted_pbt(financial_data["previousYearQuarter"])
            
            adjusted_pbt_growth = FinancialCalculations.calculate_growth(current_adjusted_pbt, previous_adjusted_pbt)
            
            # Calculate Operating Income and Operating Income %
            current_operating_income, current_operating_income_percent = FinancialCalculations.calculate_operating_income(financial_data["currentQuarter"])
            prev_operating_income, prev_operating_income_percent = FinancialCalculations.calculate_operating_income(financial_data["previousYearQuarter"])
            
            operating_income_growth = FinancialCalculations.calculate_growth(current_operating_income, prev_operating_income)
            
            # Calculate tax percentage
            current_tax_percentage = FinancialCalculations.calculate_tax_percentage(
                current_adjusted_pbt,
                financial_data['currentQuarter']['profitLossForThePeriod']
            )
            prev_tax_percentage = FinancialCalculations.calculate_tax_percentage(
                previous_adjusted_pbt,
                financial_data['previousYearQuarter']['profitLossForThePeriod']
            )
            
            # Create the formatted output
            stock_name = financial_data.get('stockData', {}).get('stockName', 'Test Company')
            output_lines = [
                f"<b>{stock_name}</b>",
                "",
                "📊 Q4 FY25 RESULTS",
                "",
                "💰 Revenue & Income",
                f"Revenue: {self._format_number(financial_data['currentQuarter']['revenueFromOps'], financial_data['revenue-format'])} Cr ({growth_data['revenueFromOps'][1]} {growth_data['revenueFromOps'][0]}%)"
            ]
            
            # Handle Other Income based on whether it has subcategories
            has_other_income_subcategories = (
                financial_data["currentQuarter"].get("exceptionalItems") is not None or
                financial_data["currentQuarter"].get("shareOfPLOfAssociates") is not None or
                financial_data["currentQuarter"].get("extraOrdinaryItems") is not None
            )
            
            if has_other_income_subcategories:
                output_lines.extend([
                    "",
                    "💵 Other Income"
                ])
                
                if financial_data["currentQuarter"].get("otherIncome") is not None:
                    output_lines.append(
                        f"Other Income: {self._format_number(financial_data['currentQuarter']['otherIncome'], financial_data['revenue-format'])} Cr ({growth_data['otherIncome'][1]} {growth_data['otherIncome'][0]}%)"
                    )
                
                if financial_data["currentQuarter"].get("exceptionalItems") is not None:
                    exceptional_items = FinancialCalculations.calculate_exceptional_items(financial_data["currentQuarter"])
                    output_lines.append(
                        f"Exceptional Items: {self._format_number(exceptional_items, financial_data['revenue-format'])} Cr"
                    )
                
                if financial_data["currentQuarter"].get("shareOfPLOfAssociates") is not None:
                    share_of_pl = financial_data["currentQuarter"]["shareOfPLOfAssociates"]
                    if share_of_pl > 0:
                        output_lines.append(
                            f"Share of P&L of Associates: {self._format_number(share_of_pl, financial_data['revenue-format'])} Cr"
                        )
                
                if financial_data["currentQuarter"].get("extraOrdinaryItems") is not None:
                    output_lines.append(self._format_extraordinary_items(
                        financial_data["currentQuarter"],
                        financial_data["previousYearQuarter"],
                        financial_data['revenue-format']
                    ))
                
                # Calculate total other income
                total_other_income = FinancialCalculations.calculate_total_other_income(financial_data["currentQuarter"])
                prev_total_other_income = FinancialCalculations.calculate_total_other_income(financial_data["previousYearQuarter"])

                # Calculate growth for total other income
                total_other_income_growth = FinancialCalculations.calculate_growth(total_other_income, prev_total_other_income)
                
                output_lines.append(f"💰 Total Other Income: {self._format_number(total_other_income, financial_data['revenue-format'])} Cr ({total_other_income_growth[1]} {total_other_income_growth[0]}%) 💰")

                # Add Other section if there are negative Share of P&L of Associates
                if financial_data["currentQuarter"].get("shareOfPLOfAssociates") is not None and financial_data["currentQuarter"]["shareOfPLOfAssociates"] < 0:
                    output_lines.extend([
                        "",
                        "📉 Other",
                        f"Share of P&L of Associates: {self._format_number(financial_data['currentQuarter']['shareOfPLOfAssociates'], financial_data['revenue-format'])} Cr"
                    ])
            else:
                output_lines.append(
                    f"Other Income: {self._format_number(financial_data['currentQuarter']['otherIncome'], financial_data['revenue-format'])} Cr ({growth_data['otherIncome'][1]} {growth_data['otherIncome'][0]}%)"
                )
            
            output_lines.extend([
                "",
                "📉 Expenses",
                self._format_metric_line("Fin Costs", financial_data['currentQuarter']['financeCosts'], growth_data['financeCosts'], financial_data['revenue-format']),
                self._format_metric_line("Dep", financial_data['currentQuarter']['depreciation'], growth_data['depreciation'], financial_data['revenue-format']),
                "",
                "📈 Operating Performance",
                self._format_metric_line("Operating Income", current_operating_income, operating_income_growth, financial_data['revenue-format']),
                f"OPM %: {current_operating_income_percent:.2f}% (vs {prev_operating_income_percent:.2f}% YOY)" if current_operating_income_percent is not None and prev_operating_income_percent is not None else "Operating Income %: N/A",
                "",
                "📊 Profitability",
                self._format_metric_line("PBT", current_adjusted_pbt, adjusted_pbt_growth, financial_data['revenue-format']),
            ])

            # Check if Extraordinary Items are present
            if financial_data['currentQuarter'].get('extraOrdinaryItems') is not None:
                # For PAT from Ordinary Activities - this always has growth data
                pat_ord_line = f"PAT from Ord. Act.: {self._format_number(financial_data['currentQuarter']['profitLossAfterTaxFromOrdinaryActivities'], financial_data['revenue-format'])} Cr ({growth_data['profitLossAfterTaxFromOrdinaryActivities'][1]} {growth_data['profitLossAfterTaxFromOrdinaryActivities'][0]}%)"
                
                # Use the helper method for extraordinary items
                extra_items_line = self._format_extraordinary_items(
                    financial_data["currentQuarter"],
                    financial_data["previousYearQuarter"],
                    financial_data['revenue-format']
                )
                
                # For Final PAT - this always has growth data
                final_pat_line = f"Final PAT: {self._format_number(financial_data['currentQuarter']['profitLossForThePeriod'], financial_data['revenue-format'])} Cr ({growth_data['profitLossForThePeriod'][1]} {growth_data['profitLossForThePeriod'][0]}%)"
                
                output_lines.extend([pat_ord_line, extra_items_line, final_pat_line])
            else:
                output_lines.append(
                    f"PAT: {self._format_number(financial_data['currentQuarter']['profitLossForThePeriod'], financial_data['revenue-format'])} Cr ({growth_data['profitLossForThePeriod'][1]} {growth_data['profitLossForThePeriod'][0]}%)"
                )

            output_lines.extend([
                "",
                f"Tax %: {current_tax_percentage:.2f}% (vs {prev_tax_percentage:.2f}% YOY)" if current_tax_percentage is not None and prev_tax_percentage is not None else "Tax %: N/A",
                "",
                f"⏱️ Processing Time: {round((financial_data.get('stockData', {}).get('nodeElapsedMs', 0) / 1000) + (time.perf_counter() - financial_data.get('stockData', {}).get('pythonStart', time.perf_counter())), 2)}s"
            ])

            # Add current time in IST
            utc_now = datetime.now(pytz.utc)
            ist_tz = pytz.timezone("Asia/Kolkata")
            ist_time = utc_now.astimezone(ist_tz)
            formatted_time = ist_time.strftime("%I:%M:%S %p · %d %b %y")
            
            output_lines.append(f"\n<code>{formatted_time}</code>")
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"Error formatting financial data: {str(e)}")
            raise 