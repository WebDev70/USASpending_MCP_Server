"""
Configurable search analytics for tracking usage patterns across different tools.

Logs all searches to identify trends, improve topic mappings,
and enhance user experience over time. Supports FAR, USASpending, and other tools.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default analytics file location
ANALYTICS_BASE_DIR = Path("/tmp/mcp_analytics")


class SearchAnalytics:
    """Track and analyze search patterns for any tool type."""

    def __init__(
        self,
        tool_name: str = "far",
        analytics_file: Optional[Path] = None,
        config: Optional[Dict] = None,
    ):
        """
        Initialize analytics tracker.

        Args:
            tool_name: Name of the tool (far, usaspending, etc.)
            analytics_file: Optional custom path for analytics file
            config: Optional configuration dict with keys:
                - filter_name: Name of the filter field (default: "part")
                - analytics_dir: Directory for analytics files (default: /tmp/mcp_analytics)
        """
        self.tool_name = tool_name
        self.config = config or {}

        # Determine analytics file path
        if analytics_file:
            self.analytics_file = analytics_file
        else:
            analytics_dir = Path(self.config.get("analytics_dir", ANALYTICS_BASE_DIR))
            analytics_dir.mkdir(parents=True, exist_ok=True)
            self.analytics_file = analytics_dir / f"{tool_name}_analytics.jsonl"

        self.analytics_file.parent.mkdir(parents=True, exist_ok=True)

        # Configuration defaults
        self.filter_name = self.config.get("filter_name", "part")
        logger.debug(f"SearchAnalytics initialized for {tool_name} with filter: {self.filter_name}")

    def log_search(
        self,
        keyword: str,
        results_count: int,
        filter_value: Optional[str] = None,
        search_type: str = "keyword",
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Log a search event for analytics.

        Args:
            keyword: Search term used
            results_count: Number of results returned
            filter_value: Optional filter value (part number, agency, etc. depending on tool)
            search_type: Type of search (keyword, topic, section, award, etc.)
            user_id: Optional user identifier
            metadata: Optional additional metadata to log
        """
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": self.tool_name,
            "keyword": keyword,
            "search_type": search_type,
            "results_count": results_count,
            self.filter_name: filter_value,  # Dynamically use configured filter name
            "user_id": user_id or "anonymous",
            "success": results_count > 0,
        }

        # Add optional metadata
        if metadata:
            record.update(metadata)

        try:
            with open(self.analytics_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(f"[{self.tool_name}] Logged search: {keyword}")
        except Exception as e:
            logger.error(f"[{self.tool_name}] Failed to log search analytics: {e}")

    def get_trending_topics(self, limit: int = 20) -> List[Dict]:
        """
        Get most popular search terms.

        Returns:
            List of (keyword, count, success_rate) tuples
        """
        if not self.analytics_file.exists():
            return []

        search_counts = {}
        success_counts = {}

        try:
            with open(self.analytics_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    keyword = record.get("keyword", "").lower()

                    if not keyword:
                        continue

                    search_counts[keyword] = search_counts.get(keyword, 0) + 1
                    if record.get("success"):
                        success_counts[keyword] = success_counts.get(keyword, 0) + 1

            # Calculate success rates and sort
            trending = []
            for keyword, count in sorted(search_counts.items(), key=lambda x: -x[1]):
                success_rate = success_counts.get(keyword, 0) / count
                trending.append(
                    {
                        "keyword": keyword,
                        "searches": count,
                        "success_rate": success_rate,
                        "failures": count - success_counts.get(keyword, 0),
                    }
                )

            return trending[:limit]
        except Exception as e:
            logger.error(f"Failed to get trending topics: {e}")
            return []

    def get_zero_result_searches(self) -> List[Dict]:
        """
        Get searches that returned zero results.

        Useful for identifying missing topic mappings.
        """
        if not self.analytics_file.exists():
            return []

        zero_results = {}

        try:
            with open(self.analytics_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    if not record.get("success"):
                        keyword = record.get("keyword", "").lower()
                        if keyword:
                            zero_results[keyword] = zero_results.get(keyword, 0) + 1

            # Return sorted by frequency
            return [
                {"keyword": k, "count": v}
                for k, v in sorted(zero_results.items(), key=lambda x: -x[1])
            ]
        except Exception as e:
            logger.error(f"Failed to get zero result searches: {e}")
            return []

    def get_cross_filter_searches(self, min_count: int = 3) -> List[Dict]:
        """
        Get searches that match content without filter specification.

        Useful for identifying multi-category/multi-part topics that work across filters.

        Args:
            min_count: Minimum occurrences to include (default 3)

        Returns:
            List of keywords searched without filter, sorted by frequency
        """
        if not self.analytics_file.exists():
            return []

        filter_searches = {}

        try:
            with open(self.analytics_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    # Find searches with no filter value that succeeded
                    if not record.get(self.filter_name) and record.get("success"):
                        keyword = record.get("keyword", "").lower()
                        if keyword:
                            filter_searches[keyword] = filter_searches.get(keyword, 0) + 1

            # Return high-frequency searches
            return [
                {"keyword": k, "count": v}
                for k, v in sorted(filter_searches.items(), key=lambda x: -x[1])
                if v >= min_count
            ]
        except Exception as e:
            logger.error(f"[{self.tool_name}] Failed to get cross-filter searches: {e}")
            return []

    # Backward compatibility alias
    def get_cross_part_searches(self, min_count: int = 3) -> List[Dict]:
        """Deprecated: Use get_cross_filter_searches() instead."""
        return self.get_cross_filter_searches(min_count)

    def generate_report(self) -> Dict:
        """Generate analytics summary report."""
        trending = self.get_trending_topics(limit=10)
        zero_results = self.get_zero_result_searches()
        cross_filter = self.get_cross_filter_searches()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": self.tool_name,
            "filter_name": self.filter_name,
            "trending_topics": trending,
            "zero_result_searches": zero_results[:10],
            "cross_filter_topics": cross_filter,
            "summary": {
                "total_searches": len(self._read_all_records()),
                "avg_results_per_search": self._avg_results(),
                "zero_result_percentage": self._zero_result_percentage(),
            },
        }

    def _read_all_records(self) -> List[Dict]:
        """Helper: Read all analytics records."""
        if not self.analytics_file.exists():
            return []
        try:
            with open(self.analytics_file, "r") as f:
                return [json.loads(line) for line in f]
        except Exception:
            return []

    def _avg_results(self) -> float:
        """Helper: Calculate average results per search."""
        records = self._read_all_records()
        if not records:
            return 0.0
        return sum(r.get("results_count", 0) for r in records) / len(records)

    def _zero_result_percentage(self) -> float:
        """Helper: Calculate % of zero-result searches."""
        records = self._read_all_records()
        if not records:
            return 0.0
        zero_count = sum(1 for r in records if not r.get("success"))
        return (zero_count / len(records)) * 100


# Global analytics instances dictionary
_analytics_instances: Dict[str, SearchAnalytics] = {}


def initialize_analytics(tool_name: str = "far", config: Optional[Dict] = None) -> SearchAnalytics:
    """
    Initialize analytics instance for a specific tool.

    Args:
        tool_name: Name of the tool (far, usaspending, etc.)
        config: Optional configuration dict

    Returns:
        SearchAnalytics instance for the tool
    """
    global _analytics_instances
    if tool_name not in _analytics_instances:
        _analytics_instances[tool_name] = SearchAnalytics(tool_name=tool_name, config=config)
        logger.info(f"Initialized analytics for tool: {tool_name}")
    return _analytics_instances[tool_name]


def get_analytics(tool_name: str = "far") -> SearchAnalytics:
    """
    Get analytics instance for a specific tool.

    Args:
        tool_name: Name of the tool (far, usaspending, etc.)

    Returns:
        SearchAnalytics instance for the tool
    """
    global _analytics_instances
    if tool_name not in _analytics_instances:
        initialize_analytics(tool_name)
    return _analytics_instances[tool_name]


def get_all_analytics() -> Dict[str, SearchAnalytics]:
    """Get all analytics instances."""
    return _analytics_instances.copy()
