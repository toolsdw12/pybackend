import statistics
from typing import List, Dict
import os
from dotenv import load_dotenv
import re
import logging
from services.analysis.result_type_config import ResultTypeConfig

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class PageClassifier:
    # Configuration parameters loaded from environment variables
    # These can be customized through .env file
    MIN_FINANCIAL_TERMS = int(os.getenv('MIN_FINANCIAL_TERMS', 7))  # Minimum number of financial terms to consider a page
    ZSCORE_THRESHOLD = float(os.getenv('ZSCORE_THRESHOLD', 1.0))    # Threshold for identifying outliers
    GAP_PERCENTAGE_THRESHOLD = float(os.getenv('GAP_PERCENTAGE_THRESHOLD', 30.0))  # Threshold for significant gap between z-scores

    # Classification terms for determining page types
    CLASSIFICATION_TERMS = {
        'Standalone': r'\bStandalone\b',
        'Consolidated': r'^(?!.*\bseparat\w*\b).*?\b(Consolidat\w*)\b.*$',
        'SEGMENT': r'\bSEGMENT\b',
        'AnyConsolidated': r'\bConsolidat\w*\b'  # Pattern to match any Consolidated term without the separate-word filter
    }

    @staticmethod
    def calculate_statistics(unique_terms_counts: List[int]) -> Dict:
        """
        Calculate statistical measures for unique term counts across pages.
        
        Steps:
        1. Check if there are any counts to analyze
        2. Calculate mean of unique term counts
        3. Calculate standard deviation (if more than one count)
        4. Calculate z-scores for each count
        """
        if not unique_terms_counts:
            return {
                "mean": 0,
                "std_dev": 0,
                "z_scores": []
            }
        
        mean = statistics.mean(unique_terms_counts)
        std_dev = statistics.stdev(unique_terms_counts) if len(unique_terms_counts) > 1 else 0
        z_scores = [(count - mean) / std_dev if std_dev > 0 else 0 for count in unique_terms_counts]
        
        return {
            "mean": mean,
            "std_dev": std_dev,
            "z_scores": z_scores
        }

    @staticmethod
    def _analyze_text_content(text: str) -> str:
        """
        Analyze text content to determine its classification type.
        
        Returns:
            str: Classification type based on text content analysis
        """
        has_standalone = bool(re.search(PageClassifier.CLASSIFICATION_TERMS['Standalone'], text, re.IGNORECASE))
        has_consolidated = any(
            bool(re.search(PageClassifier.CLASSIFICATION_TERMS['Consolidated'], line, re.IGNORECASE | re.MULTILINE))
            for line in text.split('\n')
        )
        has_any_consolidated = bool(re.search(PageClassifier.CLASSIFICATION_TERMS['AnyConsolidated'], text, re.IGNORECASE))
        has_segment = bool(re.search(PageClassifier.CLASSIFICATION_TERMS['SEGMENT'], text, re.IGNORECASE))
        
        if has_segment:
            if has_standalone:
                if has_consolidated:
                    return "Rare Case (Segment)"
                elif has_any_consolidated:
                    return "Standalone (Segment, with fake Consolidated term)"
                else:
                    return "Standalone (Segment)"
            elif has_consolidated:
                return "Consolidated (Segment)"
            else:
                return "Segment"
        elif has_standalone:
            if has_consolidated:
                return "Rare Case"
            elif has_any_consolidated:
                return "Standalone (probability of fake Conxxlidated term used)"
            else:
                return "Standalone"
        elif has_consolidated:
            return "Consolidated"
        else:
            return "Classification Failed"

    @staticmethod
    def classify_pages(analyzed_pages: List[Dict], stats: Dict, result_type_config: ResultTypeConfig) -> List[Dict]:
        """
        Classify pages based on their z-scores and unique terms count.
        
        Classification Rules:
        1. All pages start as "Not Relevant"
        2. Pages with high z-scores (> threshold) are marked as outliers
        3. Classification logic varies based on result_type_config:
           - single_page: Identify exactly one result page
           - multi_page: Identify multiple result pages based on content type
        """
        # Step 1: Calculate z-scores and mark outliers
        for page in analyzed_pages:
            page['zScore'] = stats['z_scores'][analyzed_pages.index(page)]
            page['isOutlier'] = page['zScore'] > PageClassifier.ZSCORE_THRESHOLD
            page['classification'] = "Not Relevant with zScore"

        # Step 2: Get all pages with high z-scores
        high_zscore_pages = [page for page in analyzed_pages if page['isOutlier']]
        
        if not high_zscore_pages:
            return analyzed_pages

        # Step 3: Sort pages by z-score in descending order
        high_zscore_pages.sort(key=lambda x: x['zScore'], reverse=True)

        if result_type_config.result_type == "single_page":
            # Step 4: Handle single high z-score page case
            if len(high_zscore_pages) == 1:
                page = high_zscore_pages[0]
                if page['uniqueTermsCount'] >= PageClassifier.MIN_FINANCIAL_TERMS:
                    page['classification'] = "Results Page"
                else:
                    page['classification'] = "Relevant Financial Content"
                return analyzed_pages

            # Step 5: Handle multiple high z-score pages
            highest_zscore = high_zscore_pages[0]['zScore']
            second_highest_zscore = high_zscore_pages[1]['zScore']
            gap_percentage = ((highest_zscore - second_highest_zscore) / highest_zscore) * 100

            # Step 6: Apply classification based on gap percentage
            if gap_percentage > PageClassifier.GAP_PERCENTAGE_THRESHOLD:
                # Large gap: Only highest z-score page can be Results Page
                if high_zscore_pages[0]['uniqueTermsCount'] >= PageClassifier.MIN_FINANCIAL_TERMS:
                    high_zscore_pages[0]['classification'] = "Results Page"
                else:
                    high_zscore_pages[0]['classification'] = "Relevant Financial Content"
                for page in high_zscore_pages[1:]:
                    page['classification'] = "Relevant Financial Content"
            else:
                # Small gap: All high z-score pages can be More Results Pages
                for page in high_zscore_pages:
                    if page['uniqueTermsCount'] >= PageClassifier.MIN_FINANCIAL_TERMS:
                        page['classification'] = "More Results Pages"
                    else:
                        page['classification'] = "Relevant Financial Content"

        elif result_type_config.result_type == "multi_page":
            # For multiple result type, analyze text content for each high z-score page
            for page in high_zscore_pages:
                if page['uniqueTermsCount'] >= PageClassifier.MIN_FINANCIAL_TERMS:
                    # Analyze text content to determine classification
                    content_type = PageClassifier._analyze_text_content(page.get('text', ''))
                 
                    logger.info(f"Analyzed page {page['page_number']} with content type: {content_type}")
                    
                    if result_type_config.multi_page_type == "consolidated":
                        if "Consolidated" in content_type:
                            page['classification'] = "Results Page"
                        else:
                            page['classification'] = content_type
                    else:  # standalone
                        if "Standalone" in content_type:
                            page['classification'] = "Results Page"
                        else:
                            page['classification'] = content_type
                else:
                    page['classification'] = "Relevant Financial Content"
            
        # Special case handling: exactly 2 high z-score pages without "Results Page" classification
        if len(high_zscore_pages) == 2 and not any(page['classification'] == "Results Page" for page in high_zscore_pages):
            page1, page2 = high_zscore_pages[0], high_zscore_pages[1]
            
            # Check if one is Consolidated or Standalone and update the other to Results Page if it meets criteria
            if (("Consolidated" in page1['classification'] and page2['uniqueTermsCount'] >= 10) or
                ("Standalone" in page1['classification'] and page2['uniqueTermsCount'] >= 10)):
                page2['classification'] = "Results Page"
            elif (("Consolidated" in page2['classification'] and page1['uniqueTermsCount'] >= 10) or
                    ("Standalone" in page2['classification'] and page1['uniqueTermsCount'] >= 10)):
                page1['classification'] = "Results Page"
            
            logger.info(f"Applied special case handling for 2 high z-score pages: page {page1['page_number']} is now {page1['classification']}, page {page2['page_number']} is now {page2['classification']}")

        # Handle multiple "Results Page" classifications - prevent duplicate results pages
        result_pages = [page for page in analyzed_pages if page['classification'] == "Results Page"]
        if len(result_pages) > 1:
            # Sort by z-score in descending order
            result_pages.sort(key=lambda x: x['zScore'], reverse=True)
            
            # Check if top page meets minimum terms requirement and has sufficient gap
            top_has_min_terms = result_pages[0]['uniqueTermsCount'] >= 14
            sufficient_gap = len(result_pages) >= 2 and result_pages[1]['zScore'] != 0 and \
                           ((result_pages[0]['zScore'] - result_pages[1]['zScore']) / abs(result_pages[1]['zScore'])) * 100 >= 30
            
            if not (top_has_min_terms and sufficient_gap):
                # Reclassify ALL if criteria not met
                for page in result_pages:
                    page['classification'] = "Duplicate Results Page"
                    logger.info(f"Reclassified page {page['page_number']} to 'Duplicate Results Page' due to not meeting criteria")
            else:
                # Keep only top page if criteria met
                for page in result_pages[1:]:
                    page['classification'] = "Duplicate Results Page"
                    logger.info(f"Reclassified page {page['page_number']} to 'Duplicate Results Page'")
        
        return analyzed_pages 