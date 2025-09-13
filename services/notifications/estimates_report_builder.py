from typing import Dict, Optional
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class EstimatesReportBuilder:
    """Service for formatting estimates data into readable messages"""
    
    def __init__(self):
        pass

    def _format_number(self, num: Optional[float], format_type: str = "default") -> str:
        """Helper function to format numbers with commas and appropriate units"""
        if num is None:
            return "N/A"
        
        if format_type == "percentage":
            return f"{num:.2f}%"
        elif format_type == "currency":
            return f"₹{num:,.2f} Cr"
        else:
            return f"{num:,.2f}"

    def _format_classification(self, classification: Dict) -> str:
        """Helper function to format classification data with emoji indicators"""
        classification_level = classification['classification']
        position = classification['positionInRange']
        
        # Map classifications to emojis
        emoji_map = {
            "Below Avg": "🔴",
            "Avg": "🟠",
            "Good": "🟡",
            "Very Good": "🟢",
            "Blockbuster": "🔥"
        }
        
        emoji = emoji_map.get(classification_level, "")
        # Ensure the emoji is outside of any HTML tags and properly escape special characters
        return f"{emoji} <b>{classification_level}</b> ({position:.1f}%)"

    def format_estimates_data(self, estimates_data: Dict) -> str:
        """
        Format estimates data into a readable message
        
        Args:
            estimates_data: Dictionary containing estimates data with the following structure:
            {
                "stockData": {
                    "stockName": string,
                    "nodeElapsedMs": number,
                    "pythonStart": number
                },
                "sales": {
                    "actualGrowthPercentage": number,
                    "classification": string,
                    "positionInRange": number,
                    "boundaries": {
                        "below_avg": number,
                        "avg_good": number,
                        "good_vgood": number,
                        "vgood_blockbuster": number
                    }
                },
                "margin": {
                    "actualMarginValue": number,
                    "classification": string,
                    "positionInRange": number,
                    "boundaries": {
                        "below_avg": number,
                        "avg_good": number,
                        "good_vgood": number,
                        "vgood_blockbuster": number
                    }
                },
                "profit": {
                    "actualProfitValue": number,
                    "classification": string,
                    "positionInRange": number,
                    "boundaries": {
                        "below_avg": number,
                        "avg_good": number,
                        "good_vgood": number,
                        "vgood_blockbuster": number
                    }
                }
            }
            
        Returns:
            Formatted string containing the estimates data
        """
        try:
            # Create the formatted output
            stock_name = estimates_data.get('stockData', {}).get('stockName', 'Test Company')
            output_lines = [
                f"<b>{stock_name}</b>",
                "",
                "📊 ESTIMATES ANALYSIS",
                "",
                "📈 Sales Growth",
                f"Actual Growth: {self._format_number(estimates_data['sales']['actualGrowthPercentage'], 'percentage')}",
                f"Classification: {self._format_classification(estimates_data['sales'])}",
                "",
                "💰 Margin Performance",
                f"Actual Margin: {self._format_number(estimates_data['margin']['actualMarginValue'], 'percentage')}",
                f"Classification: {self._format_classification(estimates_data['margin'])}",
                "",
                "💵 Profit Analysis",
                f"Actual Profit: {self._format_number(estimates_data['profit']['actualProfitValue'], 'currency')}",
                f"Classification: {self._format_classification(estimates_data['profit'])}",
                "",
                "📊 Classification Boundaries",
                "Sales Growth:",
                f"Below Average: &lt; {self._format_number(estimates_data['sales']['boundaries']['below_avg'], 'percentage')}",
                f"Average: {self._format_number(estimates_data['sales']['boundaries']['below_avg'], 'percentage')} - {self._format_number(estimates_data['sales']['boundaries']['avg_good'], 'percentage')}",
                f"Good: {self._format_number(estimates_data['sales']['boundaries']['avg_good'], 'percentage')} - {self._format_number(estimates_data['sales']['boundaries']['good_vgood'], 'percentage')}",
                f"Very Good: {self._format_number(estimates_data['sales']['boundaries']['good_vgood'], 'percentage')} - {self._format_number(estimates_data['sales']['boundaries']['vgood_blockbuster'], 'percentage')}",
                f"Blockbuster: &gt; {self._format_number(estimates_data['sales']['boundaries']['vgood_blockbuster'], 'percentage')}",
                "",
                "Margin:",
                f"Below Average: &lt; {self._format_number(estimates_data['margin']['boundaries']['below_avg'], 'percentage')}",
                f"Average: {self._format_number(estimates_data['margin']['boundaries']['below_avg'], 'percentage')} - {self._format_number(estimates_data['margin']['boundaries']['avg_good'], 'percentage')}",
                f"Good: {self._format_number(estimates_data['margin']['boundaries']['avg_good'], 'percentage')} - {self._format_number(estimates_data['margin']['boundaries']['good_vgood'], 'percentage')}",
                f"Very Good: {self._format_number(estimates_data['margin']['boundaries']['good_vgood'], 'percentage')} - {self._format_number(estimates_data['margin']['boundaries']['vgood_blockbuster'], 'percentage')}",
                f"Blockbuster: &gt; {self._format_number(estimates_data['margin']['boundaries']['vgood_blockbuster'], 'percentage')}",
                "",
                "Profit:",
                f"Below Average: &lt; {self._format_number(estimates_data['profit']['boundaries']['below_avg'], 'currency')}",
                f"Average: {self._format_number(estimates_data['profit']['boundaries']['below_avg'], 'currency')} - {self._format_number(estimates_data['profit']['boundaries']['avg_good'], 'currency')}",
                f"Good: {self._format_number(estimates_data['profit']['boundaries']['avg_good'], 'currency')} - {self._format_number(estimates_data['profit']['boundaries']['good_vgood'], 'currency')}",
                f"Very Good: {self._format_number(estimates_data['profit']['boundaries']['good_vgood'], 'currency')} - {self._format_number(estimates_data['profit']['boundaries']['vgood_blockbuster'], 'currency')}",
                f"Blockbuster: &gt; {self._format_number(estimates_data['profit']['boundaries']['vgood_blockbuster'], 'currency')}"
            ]

            # Add current time in IST
            utc_now = datetime.now(pytz.utc)
            ist_tz = pytz.timezone("Asia/Kolkata")
            ist_time = utc_now.astimezone(ist_tz)
            formatted_time = ist_time.strftime("%I:%M:%S %p · %d %b %y")
            
            output_lines.append(f"\n<code>{formatted_time}</code>")
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"Error formatting estimates data: {str(e)}")
            raise 