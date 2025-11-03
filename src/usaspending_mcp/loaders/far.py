"""
FAR (Federal Acquisition Regulation) Data Loader

Loads FAR parts 14, 15, 16, and 19 from JSON files stored in the docs directory.
Uses LRU caching for efficient memory management.
"""

import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_far_all_parts() -> dict:
    """Load all FAR parts (14, 15, 16, 19) from JSON files.

    Returns:
        Dictionary with keys 'part14', 'part15', 'part16', 'part19'
        Each containing a dict of section_number -> {title, content}
    """
    far_data = {}

    parts = [14, 15, 16, 19]
    for part_num in parts:
        try:
            # Get the path relative to this file, then up to docs directory
            current_dir = os.path.dirname(__file__)
            project_root = os.path.dirname(os.path.dirname(current_dir))
            far_file = os.path.join(project_root, "docs", "data", "far", f"far_part{part_num}.json")

            with open(far_file, 'r') as f:
                part_data = json.load(f)
                far_data[f"part{part_num}"] = part_data
                logger.info(f"Loaded FAR Part {part_num}: {len(part_data)} sections")
        except FileNotFoundError:
            logger.warning(f"FAR Part {part_num} file not found at expected location")
        except json.JSONDecodeError:
            logger.warning(f"Could not parse FAR Part {part_num} JSON file")
        except Exception as e:
            logger.warning(f"Could not load FAR Part {part_num}: {e}")

    return far_data


def get_part_names() -> dict:
    """Get mapping of part numbers to display names."""
    return {
        14: "Sealed Bidding",
        15: "Contracting by Negotiation",
        16: "Types of Contracts",
        19: "Small Business Programs"
    }


def get_part_descriptions() -> dict:
    """Get mapping of part keys to descriptions."""
    return {
        "part14": "Alternative to negotiated procurement for competitive sealed bidding",
        "part15": "Negotiated procurement procedures and best value selection",
        "part16": "Contract types (fixed-price, cost-reimbursement, IDIQ, etc.)",
        "part19": "Small business set-asides and programs (8(a), HUBZone, WOSB, etc.)"
    }


def get_full_part_names() -> dict:
    """Get mapping of part keys to full display names."""
    return {
        "part14": "PART 14 - SEALED BIDDING",
        "part15": "PART 15 - CONTRACTING BY NEGOTIATION",
        "part16": "PART 16 - TYPES OF CONTRACTS",
        "part19": "PART 19 - SMALL BUSINESS PROGRAMS"
    }
