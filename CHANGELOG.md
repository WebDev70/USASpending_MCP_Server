# Changelog

All notable changes to the USASpending MCP Server project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2025-11-26

### Changed

#### Project Structure Improvements
- **FAR Data Relocation**: Moved FAR JSON files from `docs/data/far/` to `src/usaspending_mcp/data/far/`
  - Clear separation: `docs/` for documentation, `src/*/data/` for runtime data
  - Follows Python packaging best practices
  - Data ships with package automatically
  - Benefits: Cleaner architecture, better organization

#### Configuration Updates
- Updated `src/usaspending_mcp/config.py`
  - `FAR_DATA_PATH` default changed to `src/usaspending_mcp/data/far`
  - Environment variable `FAR_DATA_PATH` still supported for customization
- Updated `src/usaspending_mcp/loaders/far.py`
  - Now uses `ServerConfig.FAR_DATA_PATH` instead of hard-coded path
  - Added `ServerConfig` import
  - Configurable via environment variables

#### Testing Configuration
- Updated `pytest.ini`
  - Changed `log_file` from `test.log` to `logs/test.log`
  - Centralized all pytest logs to `logs/` directory
  - Consistent log location regardless of execution directory

### Fixed

#### .gitignore Improvements
- Fixed overly broad ignore patterns
  - Changed `query_*.py` → `/query_*.py` (root directory only)
  - Changed `test_*.py` → `/test_*.py` (root directory only)
  - Prevents accidentally ignoring test files in `tests/` directory
  - Updated comment to clarify intent: "Ad-hoc analysis/test scripts in root directory only"

#### Documentation Updates
- Removed stale `GEMINI.md` reference from `CLAUDE.md`
  - File doesn't exist, reference was outdated

### Removed

#### Cleanup
- Deleted non-standard `coverage/` directory (2.3MB)
  - Standard `htmlcov/` location will be used for future coverage reports
  - Already properly ignored by `.gitignore`
- Deleted duplicate `test.log` files
  - Removed `./test.log` (root directory)
  - Removed `./tests/scripts/test.log` (empty placeholder)
  - Kept single source: `logs/test.log`

### Added

#### Documentation Maintenance Policy
- Added comprehensive "Documentation Maintenance Policy" section to `CLAUDE.md`
  - Defines when CLAUDE.md, CHANGELOG.md, and README.md must be updated
  - Specifies update triggers (structure changes, config changes, new features, etc.)
  - Provides update checklist for each file
  - Includes semantic versioning guidelines
  - Example workflow demonstrating the policy
  - 81 lines of clear, actionable guidance for Claude Code

### Documentation

#### Updated Files (8 files)
- `CLAUDE.md` - Updated FAR data paths, project structure, removed stale references, added Documentation Maintenance Policy (102 lines changed)
- `README.md` - Updated project structure diagram with new data directory (20 lines changed)
- `docs/DOCUMENTATION_ROADMAP.md` - Updated FAR data location reference
- `docs/guides/QUICKSTART.md` - Updated project structure with new FAR data location
- `docs/archived/HIGH_SCHOOL_GUIDE.md` - Updated 4 FAR data path references
- `docs/archived/JUNIOR_DEVELOPER_GUIDE.md` - Updated FAR data loading example code
- `docs/reference/tools-catalog.json` - Auto-updated version timestamp

#### Created Files
- `src/usaspending_mcp/data/__init__.py` - Package marker for data directory
- `src/usaspending_mcp/data/far/__init__.py` - Package marker for FAR data directory

### Technical Details

**Files Modified**: 15 files
**Files Deleted**: 6 files (4 old FAR JSONs + 2 duplicate logs)
**Files Created**: 6 files (new data directory structure)
**Net Change**: -839 lines (cleaner, more organized structure)

**Verification**: All changes tested and verified operational
- ✅ FAR data loads correctly from new location (210 sections across 4 parts)
- ✅ Configuration properly uses `ServerConfig.FAR_DATA_PATH`
- ✅ All documentation updated and consistent
- ✅ Test files can be committed normally
- ✅ Pytest logs centralized to `logs/test.log`

---

## [2.1.0] - 2025-11-19

### Added

#### New Conversation Management Tools (4 tools)
- `get_conversation` - Retrieve complete conversation history by conversation ID with full context
- `list_conversations` - List all conversations for a user with pagination support
- `get_conversation_summary` - Get statistics and summary information for a specific conversation
- `get_tool_usage_stats` - Get tool usage patterns and statistics for a user across all conversations

#### New Utilities
- `conversation_logging.py` - Complete conversation tracking and analytics module
  - Conversation storage and retrieval
  - Conversation statistics and summaries
  - Tool usage pattern analysis
  - Comprehensive conversation management infrastructure

#### New Documentation
- `docs/guides/CONVERSATION_LOGGING_GUIDE.md` - Complete guide to conversation tracking and analytics
  - Conversation management tools documentation
  - Integration patterns
  - Privacy and data considerations
  - Analytics use cases

#### Docker Support (Production Ready)
- `Dockerfile` - Multi-stage production-ready Docker image
  - Optimized base image
  - Minimal final image size
  - Health checks included
- `docker-compose.yml` - Complete Docker Compose orchestration
  - Service configuration
  - Port mappings
  - Volume management
  - Environment variable setup
- `docker-entrypoint.sh` - Entry point script for Docker containers
  - Handles 0.0.0.0 binding for containerized environments
  - Environment variable injection
- `.dockerignore` - Docker build optimization
  - Excludes unnecessary files from build context
- `DOCKER_GUIDE.md` - Complete Docker deployment guide
  - Quick start for Docker deployment
  - Docker Compose usage
  - Environment configuration
  - Production deployment patterns
  - Troubleshooting

#### Documentation Updates
- Updated `CLAUDE.md` with:
  - New conversation management tools (4 tools)
  - Docker deployment section in Common Development Commands
  - Docker file references in Project Structure
  - Updated Architecture Overview with conversation_logging.py
  - New Documentation Resources sections for Docker and Conversation Tracking
  - Updated Common Pitfalls with Docker-specific guidance

- Updated `README.md` with:
  - Docker Quick Start section (Step 3)
  - Expanded "Available Tools" section showing all 26 tools
  - New "Conversation Management Tools" category
  - Updated Project Structure with Docker files
  - Updated Changelog with v2.1.0 release notes

- Updated `docs/DOCUMENTATION_ROADMAP.md` with:
  - Updated tool count references (25 → 26 tools)
  - Added Conversation Logging Guide to Tier 3 features
  - Added Docker Guide to Tier 4 operations
  - Added CHANGELOG.md reference to Tier 5
  - Updated learning paths for all roles with new features
  - Updated Quick Reference table
  - Updated documentation structure
  - Updated last modified date with recent additions

- Created `CHANGELOG.md` - Complete project changelog

### Changed

- **Tool Count Updated**: Now 26 total tools (was 22 federal spending + 5 FAR)
  - 22 Federal Spending Analysis tools
  - 5 FAR (Federal Acquisition Regulation) tools
  - 4 Conversation Management tools (NEW)

- **Performance Improvements**: server.py optimized for better response times (commit 6e33754)
  - Reduced latency in tool execution
  - More efficient API integration
  - Better resource utilization

### Updated

- All documentation cross-references updated to reflect new tool count and features
- Learning paths in DOCUMENTATION_ROADMAP updated for all roles (Developer, DevOps, Analyst, Architect)
- Project structure documentation reflects new Docker files and guides
- Common pitfalls section updated with Docker-specific guidance

### Documentation Quality Improvements

- All primary documentation (CLAUDE.md, README.md, DOCUMENTATION_ROADMAP.md) now synchronized
- Removed tool count discrepancies
- Added comprehensive cross-references between guides
- Improved discoverability of new features through updated roadmaps
- All 26 tools now properly documented and discoverable

---

## [2.0.0] - 2025-11-13

### Added

- Migrated to FastMCP framework for streamlined MCP protocol handling
- Dual transport support: stdio (testing/debugging) and HTTP (Claude Desktop)
- Dedicated MCP test client for easy testing and validation
- Comprehensive tool definitions with @app.tool decorator pattern
- Enhanced documentation with multiple specialized guides

### Changed

- Replaced manual MCP implementation with FastMCP
- Improved MCP protocol compliance and stability
- Refactored server architecture for better maintainability

### Removed

- Deprecated manual MCP protocol handling code
- Legacy test utilities

### Fixed

- JSON logging in stdio mode no longer breaks MCP protocol
- Improved rate limiting reliability across transport modes

---

## [1.0.0] - 2025-10-15

### Added

#### Initial Release with Core Features

**Federal Spending Analysis Tools (22 tools)**
- Award Discovery & Lookup (5 tools)
  - search_federal_awards
  - get_award_by_id
  - get_award_details
  - get_recipient_details
  - get_vendor_by_uei

- Spending Analysis & Trends (5 tools)
  - analyze_federal_spending
  - get_spending_trends
  - get_spending_by_state
  - compare_states
  - emergency_spending_tracker

- Agency & Vendor Profiles (2 tools)
  - get_agency_profile
  - get_vendor_profile

- Classification & Breakdown Analysis (4 tools)
  - get_top_naics_breakdown
  - get_naics_psc_info
  - get_object_class_analysis
  - get_budget_functions

- Advanced Analytics & Data Export (6 tools)
  - analyze_small_business
  - spending_efficiency_metrics
  - get_disaster_funding
  - download_award_data
  - get_subaward_data
  - get_field_documentation

**FAR (Federal Acquisition Regulation) Tools (5 tools)**
- search_far_regulations - Keyword search across FAR Parts 14, 15, 16, 19
- get_far_section - Direct section lookup
- get_far_topic_sections - Topic-based searching
- get_far_analytics_report - Regulatory usage analytics
- check_far_compliance - Compliance requirement checking

**Core Utilities**
- Rate limiting with configurable request throttling
- Exponential backoff retry logic for resilience
- Structured JSON logging for HTTP mode
- Search analytics tracking
- FAR data loading and caching

**Documentation Suite**
- README.md with quick start guide
- CLAUDE.md with developer guidance
- QUICKSTART.md for getting started
- Multiple specialized guides (Logging, Rate Limiting, FAR Analytics, MCP Best Practices)
- Architecture and testing documentation
- Server management and production monitoring guides

**Integration Features**
- Natural language querying of federal spending data
- Smart currency formatting (B/M/K notations)
- Real-time data from USASpending.gov API
- Claude Desktop integration
- Comprehensive error handling and validation

---

## Version History Summary

| Version | Date | Type | Focus |
|---------|------|------|-------|
| 2.1.0 | 2025-11-19 | Feature | Conversation management, Docker support |
| 2.0.0 | 2025-11-13 | Major | FastMCP migration, dual transport |
| 1.0.0 | 2025-10-15 | Initial | Core tools and basic documentation |

---

## Known Issues

### Current Release (2.1.0)

None currently reported.

### Previous Releases

- **v2.0.0**: JSON logging in stdio mode could interfere with MCP protocol (fixed in 2.1.0)
- **v1.0.0**: Manual MCP implementation had compliance issues (resolved by FastMCP migration)

---

## Deprecations

None currently. All features from v1.0.0 and v2.0.0 are forward compatible.

---

## Future Roadmap

See [`docs/guides/FUTURE_RECOMMENDATIONS.md`](docs/guides/FUTURE_RECOMMENDATIONS.md) for planned enhancements and improvements.

### Planned Features (Next Releases)
- Advanced conversation analytics dashboard
- Multi-user conversation isolation and privacy controls
- Enhanced Docker deployment with Kubernetes support
- Performance benchmarking and optimization
- Extended USASpending.gov API integrations
- Additional FAR parts coverage (Parts 1-13, 20-49)

---

## Contributing

For information about contributing to this project, please see the documentation in [`CLAUDE.md`](CLAUDE.md) and the guidelines in individual guides.

---

## Support

For issues, questions, or feedback:
- 📧 [GitHub Issues](https://github.com/WebDev70/USASpending_MCP_Server/issues)
- 📚 [MCP Documentation](https://modelcontextprotocol.io/)
- 🌐 [USASpending API Docs](https://api.usaspending.gov/)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Data from [USASpending.gov](https://www.usaspending.gov/)
- Model Context Protocol by [Anthropic](https://www.anthropic.com/)
