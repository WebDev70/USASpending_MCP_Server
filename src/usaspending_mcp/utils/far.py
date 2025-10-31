"""
Federal Acquisition Regulation (FAR) utilities and search functionality.

Provides access to FAR Parts 14, 15, 16, and 19 with comprehensive
search, lookup, and compliance checking capabilities.
"""

import json
import os
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from functools import lru_cache

from usaspending_mcp.utils.logging import get_logger

logger = get_logger("far_utils")


class FARDatabase:
    """FAR Parts database with search and lookup capabilities."""

    def __init__(self):
        """Initialize FAR database."""
        self.parts = {}
        self.all_sections = {}
        self.topics_index = {}
        self._load_far_data()

    def _load_far_data(self):
        """Load FAR data from JSON files."""
        # Get the project root directory
        # From src/usaspending_mcp/utils/far.py, go up 3 levels to project root
        package_root = Path(__file__).resolve().parent.parent.parent.parent
        docs_dir = package_root / "docs"

        # Try multiple possible locations
        far_paths = [
            docs_dir / "far_part14.json",
            docs_dir / "far_part15.json",
            docs_dir / "far_part16.json",
            docs_dir / "far_part19.json",
            # Fallback to /tmp/ if docs files not found
            Path("/tmp/part14_full.json"),
            Path("/tmp/part15_full.json"),
            Path("/tmp/part16_full.json"),
            Path("/tmp/part19_full.json"),
        ]

        for path in far_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        # Extract part number from filename (far_part14.json -> 14)
                        part_num = path.stem.split('_')[-1].replace("part", "")
                        self.parts[f"Part {part_num}"] = data
                        # Data is already in sections format (section_number: {title, content})
                        self._index_sections(part_num, data)
                        logger.info(f"Loaded {len(data)} sections from Part {part_num}")
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")

        # Build topics index
        self._build_topics_index()

    def _index_sections(self, part_num: str, sections: Dict):
        """Index sections for fast lookup."""
        for section_num, section_data in sections.items():
            key = section_num
            self.all_sections[key] = {
                "part": part_num,
                "number": section_num,
                "title": section_data.get("title", ""),
                "content": section_data.get("content", "")
            }

    def _build_topics_index(self):
        """Build a topics index from section titles and content."""
        topics_map = {
            "sealed bidding": "14",
            "competitive sealed": "14",
            "invitation for bids": "14",
            "ifb": "14",
            "negotiation": "15",
            "request for proposal": "15",
            "rfp": "15",
            "best value": "15",
            "source selection": "15",
            "proposal evaluation": "15",
            "cost or pricing data": "15",
            "contract type": "16",
            "fixed price": "16",
            "cost reimbursement": "16",
            "cost-plus": "16",
            "time and materials": "16",
            "indefinite quantity": "16",
            "small business": "19",
            "small disadvantaged business": "19",
            "sdb": "19",
            "woman-owned": "19",
            "wosb": "19",
            "set-aside": "19",
            "8a": "19",
            "hubzone": "19",
        }

        for topic, part in topics_map.items():
            if topic not in self.topics_index:
                self.topics_index[topic] = {"part": part, "sections": []}

    def search_keyword(self, keyword: str, part: Optional[str] = None) -> List[Dict]:
        """
        Search for FAR sections by keyword.

        Args:
            keyword: Search term
            part: Optional part number to restrict search (14, 15, 16, 19)

        Returns:
            List of matching sections with relevance scores
        """
        keyword_lower = keyword.lower()
        results = []

        for section_num, section in self.all_sections.items():
            # Filter by part if specified
            if part and section["part"] != str(part):
                continue

            title = section.get("title", "").lower()
            content = section.get("content", "").lower()

            # Calculate relevance score
            title_matches = title.count(keyword_lower)
            content_matches = content.count(keyword_lower)

            if title_matches > 0 or content_matches > 0:
                relevance_score = (title_matches * 3) + content_matches
                results.append({
                    "section": section_num,
                    "part": section["part"],
                    "title": section.get("title", ""),
                    "relevance": relevance_score,
                    "preview": self._get_preview(content, keyword_lower),
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:20]  # Return top 20 results

    def get_section(self, section_number: str) -> Optional[Dict]:
        """
        Get a specific FAR section by number (e.g., '15.203').

        Args:
            section_number: Section number like '15.203'

        Returns:
            Section data or None if not found
        """
        if section_number in self.all_sections:
            section = self.all_sections[section_number]
            return {
                "section": section_number,
                "part": section["part"],
                "title": section["title"],
                "content": section["content"],
                "url": f"https://www.acquisition.gov/far/part-{section['part']}#{section_number}"
            }
        return None

    def get_topic_sections(self, topic: str, part: Optional[str] = None) -> List[Dict]:
        """
        Get FAR sections related to a topic.

        Args:
            topic: Topic keyword
            part: Optional part to restrict search

        Returns:
            List of relevant sections
        """
        topic_lower = topic.lower()

        # Check predefined topics first
        if topic_lower in self.topics_index:
            target_part = self.topics_index[topic_lower]["part"]
            if part and str(part) != target_part:
                return []
            results = []
            for section_num, section in self.all_sections.items():
                if section["part"] == target_part:
                    results.append({
                        "section": section_num,
                        "part": section["part"],
                        "title": section["title"]
                    })
            return results

        # Fall back to keyword search
        return self.search_keyword(topic, part)

    def check_compliance(self, method: str, requirements: List[str]) -> Dict:
        """
        Check compliance with FAR requirements for a contracting method.

        Args:
            method: Contracting method (sealed_bidding, negotiation, etc.)
            requirements: List of requirements to verify

        Returns:
            Compliance report
        """
        compliance_rules = {
            "sealed_bidding": {
                "part": "14",
                "requires": ["IFB", "competitive range", "evaluation criteria"],
                "prohibits": ["negotiations", "best value trade-offs"]
            },
            "negotiation": {
                "part": "15",
                "requires": ["RFP", "source selection", "evaluation factors"],
                "prohibits": ["sealed bidding procedures"]
            },
            "small_business": {
                "part": "19",
                "requires": ["size determination", "North American Industry Classification System (NAICS)"],
                "prohibits": []
            }
        }

        method_key = method.lower().replace(" ", "_")
        rules = compliance_rules.get(method_key, {})

        if not rules:
            return {
                "method": method,
                "compliant": False,
                "message": f"Unknown contracting method: {method}",
                "issues": [f"Unknown method: {method}"]
            }

        # Check requirements
        issues = []
        for req in requirements:
            req_lower = req.lower()
            if req_lower in rules.get("prohibits", []):
                issues.append(f"Prohibited for {method}: {req}")

        # Get relevant FAR sections
        part = rules.get("part")
        relevant_sections = [s for s in self.all_sections.values() if s["part"] == part][:5]

        return {
            "method": method,
            "compliant": len(issues) == 0,
            "part": part,
            "issues": issues if issues else ["No compliance issues found"],
            "relevant_sections": [
                {"section": s["number"], "title": s["title"]}
                for s in relevant_sections
            ]
        }

    def _get_preview(self, text: str, keyword: str, context_length: int = 100) -> str:
        """Get a preview of text around keyword match."""
        idx = text.find(keyword)
        if idx == -1:
            return text[:context_length] + "..."

        start = max(0, idx - context_length // 2)
        end = min(len(text), idx + context_length // 2)
        preview = text[start:end]

        if start > 0:
            preview = "..." + preview
        if end < len(text):
            preview = preview + "..."

        return preview

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        return {
            "total_parts": len(self.parts),
            "total_sections": len(self.all_sections),
            "parts_indexed": {
                f"Part {part_num}": len(sections.get("sections", {}))
                for part_num, sections in self.parts.items()
            }
        }


# Global FAR database instance
_far_db: Optional[FARDatabase] = None


def initialize_far_database() -> FARDatabase:
    """Initialize the global FAR database."""
    global _far_db
    if _far_db is None:
        _far_db = FARDatabase()
        logger.info(f"Initialized FAR database with {_far_db.get_statistics()['total_sections']} sections")
    return _far_db


def get_far_database() -> FARDatabase:
    """Get the global FAR database instance."""
    global _far_db
    if _far_db is None:
        initialize_far_database()
    return _far_db
