from typing import Dict, List, Tuple
import re
from dataclasses import dataclass
import json

@dataclass
class ProductMatch:
    """Product matching result"""
    similarity_score: float
    brand_match: bool
    category_match: bool
    size_match: bool
    confidence: str  # low, medium, high
    reasoning: str

class LLMProductMatcher:
    """Simple rule-based product matcher (can be enhanced with actual LLM later)"""
    
    def __init__(self):
        self.category_keywords = {
            'sunglasses': ['sunglasses', 'eyewear', 'glasses', 'shades'],
            'bottle': ['bottle', 'flask', 'thermos', 'tumbler', 'hydration'],
            'mug': ['mug', 'cup', 'coffee', 'tea'],
            'stand': ['stand', 'holder', 'dock', 'mount'],
            'notebook': ['notebook', 'journal', 'diary', 'planner', 'book'],
            'lunchbox': ['lunchbox', 'lunch', 'container', 'bento'],
            'stole': ['stole', 'scarf', 'wrap', 'shawl', 'silk']
        }
        
        self.material_keywords = {
            'wood': ['wooden', 'wood', 'bamboo', 'timber'],
            'silk': ['silk', 'satin', 'fabric'],
            'metal': ['metal', 'steel', 'aluminum', 'stainless'],
            'cork': ['cork']
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        return re.sub(r'[^a-zA-Z0-9\s]', '', text.lower().strip())
    
    def extract_size_info(self, text: str) -> Dict[str, str]:
        """Extract size/capacity information"""
        size_info = {}
        
        # Volume patterns
        volume_pattern = r'(\d+)\s*(ml|l|oz|fl\s*oz)'
        volume_match = re.search(volume_pattern, text.lower())
        if volume_match:
            size_info['volume'] = f"{volume_match.group(1)}{volume_match.group(2)}"
        
        # Dimension patterns
        dimension_pattern = r'(\d+)\s*x\s*(\d+)\s*(cm|mm|inch|in)'
        dimension_match = re.search(dimension_pattern, text.lower())
        if dimension_match:
            size_info['dimensions'] = f"{dimension_match.group(1)}x{dimension_match.group(2)}{dimension_match.group(3)}"
        
        return size_info
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using word overlap"""
        words1 = set(self.normalize_text(text1).split())
        words2 = set(self.normalize_text(text2).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def match_category(self, target_product: str, scraped_title: str) -> Tuple[bool, str]:
        """Match product category"""
        target_norm = self.normalize_text(target_product)
        scraped_norm = self.normalize_text(scraped_title)
        
        for category, keywords in self.category_keywords.items():
            target_has_category = any(keyword in target_norm for keyword in keywords)
            scraped_has_category = any(keyword in scraped_norm for keyword in keywords)
            
            if target_has_category and scraped_has_category:
                return True, category
        
        return False, "unknown"
    
    def match_material(self, target_product: str, scraped_title: str) -> Tuple[bool, str]:
        """Match product material"""
        target_norm = self.normalize_text(target_product)
        scraped_norm = self.normalize_text(scraped_title)
        
        for material, keywords in self.material_keywords.items():
            target_has_material = any(keyword in target_norm for keyword in keywords)
            scraped_has_material = any(keyword in scraped_norm for keyword in keywords)
            
            if target_has_material and scraped_has_material:
                return True, material
        
        return False, "unknown"
    
    def match_brand(self, target_brand: str, scraped_brand: str) -> bool:
        """Match brand names"""
        if not target_brand or not scraped_brand:
            return False
        
        target_norm = self.normalize_text(target_brand)
        scraped_norm = self.normalize_text(scraped_brand)
        
        # Exact match
        if target_norm == scraped_norm:
            return True
        
        # Partial match
        return target_norm in scraped_norm or scraped_norm in target_norm
    
    def match_size(self, target_product: str, scraped_title: str) -> bool:
        """Match size/capacity information"""
        target_size = self.extract_size_info(target_product)
        scraped_size = self.extract_size_info(scraped_title)
        
        if not target_size or not scraped_size:
            return True  # No size info to compare
        
        # Compare volume if available
        if 'volume' in target_size and 'volume' in scraped_size:
            return target_size['volume'] == scraped_size['volume']
        
        # Compare dimensions if available
        if 'dimensions' in target_size and 'dimensions' in scraped_size:
            return target_size['dimensions'] == scraped_size['dimensions']
        
        return True
    
    def match_product(self, target_product: str, scraped_product: dict) -> ProductMatch:
        """Match a target product with a scraped product"""
        scraped_title = scraped_product.get('title', '')
        scraped_brand = scraped_product.get('brand', '')
        
        # Calculate text similarity
        similarity = self.calculate_text_similarity(target_product, scraped_title)
        
        # Check category match
        category_match, category = self.match_category(target_product, scraped_title)
        
        # Check material match
        material_match, material = self.match_material(target_product, scraped_title)
        
        # Check brand match (if available)
        brand_match = self.match_brand("", scraped_brand)  # We don't have target brand
        
        # Check size match
        size_match = self.match_size(target_product, scraped_title)
        
        # Calculate overall score
        score = similarity
        if category_match:
            score += 0.3
        if material_match:
            score += 0.2
        if brand_match:
            score += 0.1
        if size_match:
            score += 0.1
        
        # Determine confidence
        if score >= 0.8:
            confidence = "high"
        elif score >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Generate reasoning
        reasoning_parts = []
        if category_match:
            reasoning_parts.append(f"category match ({category})")
        if material_match:
            reasoning_parts.append(f"material match ({material})")
        if brand_match:
            reasoning_parts.append("brand match")
        if similarity > 0.5:
            reasoning_parts.append(f"high text similarity ({similarity:.2f})")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "low similarity"
        
        return ProductMatch(
            similarity_score=min(score, 1.0),
            brand_match=brand_match,
            category_match=category_match,
            size_match=size_match,
            confidence=confidence,
            reasoning=reasoning
        )

def create_product_matcher() -> LLMProductMatcher:
    """Factory function to create product matcher"""
    return LLMProductMatcher()
