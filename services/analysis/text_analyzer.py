import re
from typing import List, Dict, Set
import os
from dotenv import load_dotenv
from .page_classifier import PageClassifier
import logging
from services.analysis.result_type_config import ResultTypeConfig

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class TextAnalyzer:
    FINANCIAL_TERMS = [
        r'\bRevenue from operations\b',
        r'\bOther Income\b',
        r'\bTotal Income\b',
        r'\bExpense\b',
        r'\bFinance Costs\b',
        r'\bDepreciation\b',
        r'\bBefore Tax\b',
        r'\bProfit before tax\b',
        r'\bExceptional\b',
        r'\bTax Expense\b',
        r'\bCurrent Tax\b',
        r'\bDeferred Tax\b',
        r'\bNet Income\b',
        r'\bComprehensive Income\b',
        r'\bReclassified\b',
        r'\bAttributable to\b',
        r'\bControlling\b',
        r'\bDiluted\b',
        r'\bEquity Share\b', 
        r'\bProfit after tax\b',
        r'\bValue\b', 
        r'\b(lakhs?|Millions?|crores?)\b'
    ]
    
    # Configuration parameter loaded from environment variables
    MIN_FINANCIAL_TERMS = int(os.getenv('MIN_FINANCIAL_TERMS'))  # Minimum number of financial terms to consider a page relevant
    
    @staticmethod
    def find_unique_terms(text: str) -> Set[str]:
        """
        Find unique financial terms in a given text.
        
        Steps:
        1. Initialize an empty set to store found terms
        2. Search for each financial term in the text (case-insensitive)
        3. Store the actual matched term if found
        4. Return the set of unique terms found
        """
        found_terms: Set[str] = set()
        for term in TextAnalyzer.FINANCIAL_TERMS:
            if re.search(term, text, re.IGNORECASE):
                # Store the actual matched term
                found_term = re.search(term, text, re.IGNORECASE).group(0)
                found_terms.add(found_term)
        return found_terms

    @staticmethod
    def analyze_page(text: str, page_number: int, is_ocr: bool = False) -> Dict:
        """
        Analyze a single page of text for financial terms and classification.
        
        Steps:
        1. Clean and prepare the text
        2. Find unique financial terms in the text
        3. Count unique terms
        4. Determine if page is relevant based on term count
        5. Return analysis results with metadata
        """
        # Step 1: Clean and prepare text
        text = text.strip()
        
        # Step 2: Find unique financial terms
        found_terms = TextAnalyzer.find_unique_terms(text)
        unique_terms_count = len(found_terms)
        
        # Step 3: Determine if page is relevant
        is_relevant = unique_terms_count >= TextAnalyzer.MIN_FINANCIAL_TERMS
        
        # Step 4: Initialize classification (will be updated later by PageClassifier)
        classification = "Unknown"
        
        # Step 5: Return analysis results
        return {
            "page_number": page_number,  # Keep original page number
            "text": text,
            "isRelevant": is_relevant,
            "foundTerms": list(found_terms),
            "foundTermsCount": unique_terms_count,
            "uniqueTermsCount": unique_terms_count,  # Using unique count instead of frequency
            "classification": classification,
            "isOcr": is_ocr  # Preserve OCR flag
        }

    @staticmethod
    def analyze_document(pages: List[Dict[str, str]], result_type_config: ResultTypeConfig) -> Dict:
        """
        Analyze all pages in a document with statistical analysis.
        
        Steps:
        1. Analyze each page and collect unique term counts
        2. Check if any page meets minimum financial terms requirement
        3. If no relevant pages found, mark document for OCR processing
        4. Check if only one Relevant page in multi_page mode
        5. Check if difference between highest and second-highest term pages > 10 in multi_page mode
        6. Calculate statistics and classify pages using PageClassifier
        7. Check if any outlier page has "Classification Failed" status
        8. Return final analysis results

        Args:
            pages: List of page dictionaries containing text content
            result_type_config: Configuration for result page type detection
            
        Returns:
            Dictionary containing analysis results
        """
        analyzed_pages = []
        unique_terms_counts = []
        
        # Step 1: First pass - analyze pages and collect unique term counts
        for page in pages:
            page_number = page.get('page_number', 0)  # Keep original page number
            text = page.get('text', '')
            is_ocr = page.get('isOcr', False)
            analyzed_page = TextAnalyzer.analyze_page(text, page_number, is_ocr)
            analyzed_pages.append(analyzed_page)
            unique_terms_counts.append(analyzed_page['uniqueTermsCount'])
        
        # Step 2: Check if any page has financial terms >= MIN_FINANCIAL_TERMS, if not, return True for needs_ocr
        if not any(page['uniqueTermsCount'] >= TextAnalyzer.MIN_FINANCIAL_TERMS for page in analyzed_pages):
            return {
                "needs_ocr": True,
                "message": "PDF needs to be processed through OCR API to get data",
                "pages": analyzed_pages
            }
        '''
        # Step 3: Check for two Relevant pages in multi_page mode, if not, return True for needs_ocr
        if PageClassifier.RESULT_TYPE == "multi_page":
            # Step 3.1: Check if only one Relevant page in multi_page mode
            relevant_pages = [p for p in analyzed_pages if p['isRelevant']]
            if len(relevant_pages) == 1:
                return {
                    "needs_ocr": True,
                    "message": "Only one Relevant page found in multi_page mode, needs OCR processing",
                    "pages": analyzed_pages
                }
                
            # Step 3.2: Check if difference between highest and second-highest term pages > 10 and second-highest term pages < 10 in multi_page
            if len(relevant_pages) >= 2:
                # Sort relevant pages by unique terms count in descending order
                sorted_pages = sorted(relevant_pages, key=lambda x: x['uniqueTermsCount'], reverse=True)
                highest_terms = sorted_pages[0]['uniqueTermsCount']
                second_highest_terms = sorted_pages[1]['uniqueTermsCount']
                
                if (highest_terms - second_highest_terms) >= 10 and second_highest_terms < 9:
                    logger.info(f"OCR triggered: Difference between highest and second-highest term pages is {highest_terms - second_highest_terms} (> 10)")
                    return {
                        "needs_ocr": True,
                        "message": "Difference between highest and second-highest term pages > 10, needs OCR processing",
                        "pages": analyzed_pages
                    }
        '''   
        
        # Step 4: Calculate statistics and classify pages using PageClassifier
        stats = PageClassifier.calculate_statistics(unique_terms_counts)
        analyzed_pages = PageClassifier.classify_pages(analyzed_pages, stats, result_type_config)
        
        # Step 5: Check if document needs OCR based on Results Page criteria
        results_pages = [page for page in analyzed_pages if page.get('classification') == "Results Page"]
        if not results_pages:
            logger.info("OCR triggered: No 'Results Page' found in any analyzed page")
            return {
                "needs_ocr": True,
                "message": "No Results Page found, needs OCR processing",
                "pages": analyzed_pages
            }
        else:
            # Verify that Results Page has sufficient financial terms (>= 10)
            if not any(page.get('uniqueTermsCount', 0) >= 10 for page in results_pages):
                logger.info("OCR triggered: 'Results Page' found but doesn't have at least 10 unique terms")
                return {
                    "needs_ocr": True,
                    "message": "Results Page doesn't have enough unique terms, needs OCR processing",
                    "pages": analyzed_pages
                }
        
        # Step 6: Check if any outlier page has "Classification Failed" status
        '''
        for page in analyzed_pages:
            if page.get('isOutlier', False) and "Classification Failed" in page.get('classification', ''):
                logger.info(f"OCR triggered: Outlier page {page['page_number']} has 'Classification Failed' status")
                return {
                    "needs_ocr": True,
                    "message": "Classification failed for outlier page, needs OCR processing",
                    "pages": analyzed_pages
                }'''
        
        # Step 7: For multi_page mode, check if we have at least two non-"Not Relevant with zScore" pages
        '''
        if PageClassifier.RESULT_TYPE == "multi_page":
            relevant_pages = [page for page in analyzed_pages 
                             if page['classification'] != "Not Relevant with zScore"]
            
            if len(relevant_pages) <= 1:
                logger.info(f"OCR triggered: Not enough relevant pages found in multi_page mode. Found only {len(relevant_pages)} relevant page(s).")
                return {
                    "needs_ocr": True,
                    "message": "Not enough relevant pages found in multi_page mode, needs OCR processing",
                    "pages": analyzed_pages
                }
        '''
        
        # Step 8: Return final analysis results
        return {
            "needs_ocr": False,
            "message": "PDF processed successfully",
            "pages": analyzed_pages
        } 