"""Analyzer for SEC filing documents (10-K, 10-Q)."""
import re
from typing import Dict, Optional, List
from loguru import logger


class FilingAnalyzer:
    """Analyze SEC filings to extract key sections and metrics."""
    
    def __init__(self):
        """Initialize the filing analyzer with section patterns."""
        # More tolerant regex patterns for common 10-K/10-Q sections
        # Allow different punctuation, newlines, multiple spaces, and unicode dashes
        self.section_patterns = {
            'business': r'item\s*1\s*[\.:\-–—]*\s*business',
            'risk_factors': r'item\s*1a\s*[\.:\-–—]*\s*risk\s*factors',
            'unresolved_staff_comments': r'item\s*1b\s*[\.:\-–—]*\s*unresolved\s*staff\s*comments',
            'properties': r'item\s*2\s*[\.:\-–—]*\s*properties',
            'legal_proceedings': r'item\s*3\s*[\.:\-–—]*\s*legal\s*proceedings',
            'mda': r'item\s*7\s*[\.:\-–—]*\s*management.*?discussion.*?analysis',
            'financials': r'item\s*8\s*[\.:\-–—]*\s*financial\s*statements',
            'controls': r'item\s*9a\s*[\.:\-–—]*\s*controls\s*and\s*procedures'
        }
        
        logger.info("Initialized FilingAnalyzer")
    
    def extract_section(self, text: str, section_key: str) -> Optional[str]:
        """
        Extract a specific section from the filing text.
        
        Args:
            text: Full filing text
            section_key: Key from section_patterns dict
            
        Returns:
            Extracted section text or None if not found
        """
        pattern = self.section_patterns.get(section_key)
        if not pattern:
            logger.warning(f"Unknown section key: {section_key}")
            return None
        
        # Find section start (case-insensitive)
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            logger.debug(f"Section '{section_key}' not found in filing")
            return None
        
        start = match.end()
        
        # Find next section (end boundary) using a broad 'Item <number/letter>' pattern
        next_section = re.search(r'\bitem\s+\d+[a-z]?\b', text[start:], re.IGNORECASE)
        end = start + next_section.start() if next_section else len(text)
        
        section_text = text[start:end].strip()
        logger.debug(f"Extracted section '{section_key}': {len(section_text)} chars")
        
        return section_text
    
    def extract_all_sections(self, text: str) -> Dict[str, str]:
        """
        Extract all standard sections from the filing.
        
        Args:
            text: Full filing text
            
        Returns:
            Dictionary mapping section names to extracted text
        """
        sections = {}
        
        for section_key in self.section_patterns.keys():
            content = self.extract_section(text, section_key)
            if content:
                sections[section_key] = content
        
        # Fallback: if nothing found, try simpler phrase-based extraction for MD&A
        if not sections:
            m = re.search(r'management[\u2019\']?s\s+discussion\s+and\s+analysis', text, re.IGNORECASE)
            if m:
                start = m.start()
                nxt = re.search(r'\bitem\s+\d+[a-z]?\b', text[start:], re.IGNORECASE)
                end = start + nxt.start() if nxt else len(text)
                sections['mda'] = text[start:end]
        
        logger.info(f"Extracted {len(sections)} sections from filing")
        return sections
    
    def extract_financial_mentions(self, text: str) -> Dict[str, List[str]]:
        """
        Extract mentions of financial metrics from text.
        
        Args:
            text: Text to analyze (typically MD&A section)
            
        Returns:
            Dictionary of metric types to found values
        """
        metrics = {
            'revenue': [],
            'net_income': [],
            'earnings': [],
            'cash': [],
            'debt': []
        }
        
        # Revenue patterns
        revenue_pattern = r'(?:revenue|sales|net\s+sales).*?\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand)'
        for match in re.finditer(revenue_pattern, text, re.IGNORECASE):
            value = f"${match.group(1)} {match.group(2)}"
            metrics['revenue'].append(value)
        
        # Net income patterns
        income_pattern = r'net\s+income.*?\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand)'
        for match in re.finditer(income_pattern, text, re.IGNORECASE):
            value = f"${match.group(1)} {match.group(2)}"
            metrics['net_income'].append(value)
        
        # Earnings per share
        eps_pattern = r'earnings\s+per\s+share.*?\$\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(eps_pattern, text, re.IGNORECASE):
            value = f"${match.group(1)}"
            metrics['earnings'].append(value)
        
        # Cash
        cash_pattern = r'cash\s+and\s+cash\s+equivalents.*?\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand)'
        for match in re.finditer(cash_pattern, text, re.IGNORECASE):
            value = f"${match.group(1)} {match.group(2)}"
            metrics['cash'].append(value)
        
        # Debt
        debt_pattern = r'(?:total\s+)?debt.*?\$\s*(\d+(?:\.\d+)?)\s*(billion|million|thousand)'
        for match in re.finditer(debt_pattern, text, re.IGNORECASE):
            value = f"${match.group(1)} {match.group(2)}"
            metrics['debt'].append(value)
        
        # Remove duplicates and limit
        for key in metrics:
            metrics[key] = list(set(metrics[key]))[:5]  # Keep top 5 unique mentions
        
        return metrics
    
    def calculate_section_stats(self, section_text: str) -> Dict:
        """
        Calculate statistics about a text section.
        
        Args:
            section_text: Text to analyze
            
        Returns:
            Dictionary of statistics
        """
        words = section_text.split()
        sentences = re.split(r'[.!?]+', section_text)
        
        stats = {
            'char_count': len(section_text),
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0
        }
        
        return stats
    
    def _normalize(self, text: str) -> str:
        """Normalize filing text for robust regex matching."""
        if not text:
            return ''
        # Replace non-breaking spaces and fancy quotes, collapse whitespace
        text = text.replace('\xa0', ' ')
        text = text.replace('\u2019', "'").replace('\u2013', '-').replace('\u2014', '-')
        # Collapse multiple spaces/newlines
        text = re.sub(r'[\s\u00A0]+', ' ', text)
        return text

    def analyze_filing(self, filing_text: str, ticker: str, filing_type: str, filing_date: str) -> Dict:
        """
        Perform complete analysis of a filing.
        
        Args:
            filing_text: Full text of the filing
            ticker: Stock ticker symbol
            filing_type: Type of filing (10-K, 10-Q)
            filing_date: Date of filing
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Analyzing {filing_type} filing for {ticker} dated {filing_date}")
        
        analysis = {
            'ticker': ticker,
            'filing_type': filing_type,
            'filing_date': filing_date,
            'sections': {},
            'financial_mentions': {},
            'metadata': {
                'total_char_count': len(filing_text),
                'total_word_count': len(filing_text.split())
            }
        }
        
        # Normalize text for better matching
        filing_text = self._normalize(filing_text)
        
        # Extract all sections
        sections = self.extract_all_sections(filing_text)
        
        for section_name, section_text in sections.items():
            stats = self.calculate_section_stats(section_text)
            analysis['sections'][section_name] = {
                'stats': stats,
                'preview': section_text[:200]  # First 200 chars for preview
            }
        
        # Extract financial mentions from MD&A
        mda_text = sections.get('mda', '')
        if mda_text:
            analysis['financial_mentions'] = self.extract_financial_mentions(mda_text)
        
        # Analysis summary
        analysis['metadata']['sections_found'] = len(sections)
        analysis['metadata']['total_mentions'] = sum(
            len(v) for v in analysis['financial_mentions'].values()
        )
        
        logger.info(
            f"Analysis complete: {analysis['metadata']['sections_found']} sections, "
            f"{analysis['metadata']['total_mentions']} financial mentions"
        )
        
        return analysis
    
    def extract_risk_keywords(self, risk_factors_text: str) -> List[str]:
        """
        Extract common risk-related keywords from risk factors section.
        
        Args:
            risk_factors_text: Text from Risk Factors section
            
        Returns:
            List of risk keywords found
        """
        risk_keywords = [
            'uncertainty', 'volatile', 'fluctuate', 'decline', 'adverse',
            'litigation', 'competition', 'regulatory', 'compliance', 'cybersecurity',
            'breach', 'pandemic', 'recession', 'economic downturn', 'supply chain',
            'inflation', 'interest rate', 'foreign exchange', 'geopolitical'
        ]
        
        text_lower = risk_factors_text.lower()
        found_keywords = []
        
        for keyword in risk_keywords:
            if keyword in text_lower:
                # Count occurrences
                count = text_lower.count(keyword)
                found_keywords.append({'keyword': keyword, 'count': count})
        
        # Sort by frequency
        found_keywords.sort(key=lambda x: x['count'], reverse=True)
        
        logger.info(f"Found {len(found_keywords)} risk keywords in text")
        return found_keywords
