# Documentation Roadmap

This guide helps you navigate the documentation and understand the USASpending MCP Server project based on your role and needs.

## Quick Navigation

| Role | Time | Path |
|------|------|------|
| **First-Time User** | 15 min | [Getting Started](#tier-1-foundation-start-here) |
| **Developer** | 1-2 hours | [Foundation](#tier-1-foundation-start-here) → [Architecture](#tier-2-architecture--core-understanding) → [Features](#tier-3-key-features-as-needed) → [Development](#tier-5-development) |
| **DevOps/Operations** | 1 hour | [Foundation](#tier-1-foundation-start-here) → [Architecture](#tier-2-architecture--core-understanding) → [Operations](#tier-4-operations--best-practices) → [Production](#tier-5-development) |
| **Analyst/Power User** | 30 min | [Foundation](#tier-1-foundation-start-here) → [Features](#tier-3-key-features-as-needed) |
| **Complete Understanding** | 4-6 hours | All tiers in order |

---

## Tier 1: Foundation (Start Here)

**Estimated Time: 15-20 minutes**

These documents give you the overall picture and get the system running.

### 1. [`../README.md`](../README.md)
- **What**: Project overview, features, installation, and usage
- **Why**: Essential for understanding what the project does and how to use it
- **Read if**: Everyone (mandatory)
- **Key sections**:
  - Features overview
  - Quick start setup
  - Project structure
  - Available tools

### 2. [`guides/QUICKSTART.md`](guides/QUICKSTART.md)
- **What**: Step-by-step guide to get the server running
- **Why**: Get hands-on experience with the system
- **Read if**: Everyone (recommended after README)
- **Key sections**:
  - Installation steps
  - Running the test client
  - Example queries
  - Integration with Claude Desktop

---

## Tier 2: Architecture & Core Understanding

**Estimated Time: 45-60 minutes**

Deep dive into how the system is designed and what capabilities it offers.

### 3. [`dev/ARCHITECTURE_GUIDE.md`](dev/ARCHITECTURE_GUIDE.md)
- **What**: System design, component relationships, data flow
- **Why**: Understand how everything connects and works together
- **Read if**: Developers, architects, anyone making design decisions
- **Key sections**:
  - Component architecture
  - FastMCP server structure
  - Tool registration and execution
  - Data flow diagrams
  - Transport modes (stdio vs HTTP)

### 4. [`reference/tools-catalog.json`](reference/tools-catalog.json)
- **What**: Complete catalog of all 26 MCP tools with parameters and examples
- **Why**: Reference for all available functionality
- **Read if**: Developers, power users, anyone building queries
- **Key sections**:
  - Federal spending tools (22 tools)
  - FAR regulation tools (5 tools)
  - Conversation management tools (4 tools)
  - Parameter specifications
  - Usage examples
  - Expected response formats

---

## Tier 3: Key Features (As Needed)

**Estimated Time: 1-2 hours (read only what's relevant)**

Detailed guides for specific features and capabilities.

### 5. [`reference/api-mappings.json`](reference/api-mappings.json)
- **What**: How MCP tools map to USASpending API endpoints
- **Why**: Understand the integration with USASpending.gov
- **Read if**: Developers building custom integrations or debugging API issues
- **Key sections**:
  - Endpoint mappings
  - Parameter transformations
  - Known issues and workarounds

### 6. [`guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md`](guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md)
- **What**: Analytics capabilities and multi-tool workflows
- **Why**: Learn how to combine multiple tools for complex analyses
- **Read if**: Analysts, power users, developers building analytics features
- **Key sections**:
  - Multi-tool workflows
  - Analytics patterns
  - Performance optimization
  - Real-world analysis examples

### 7. [`guides/FAR_ANALYTICS_GUIDE.md`](guides/FAR_ANALYTICS_GUIDE.md)
- **What**: FAR (Federal Acquisition Regulation) regulatory tools and analysis
- **Why**: Learn how to use Parts 14, 15, 16, and 19 for compliance
- **Read if**: Government contractors, procurement professionals, compliance officers
- **Key sections**:
  - FAR structure and tools
  - Compliance checking
  - Regulatory analysis patterns
  - Use cases for each FAR part

### 8. [`reference/query-templates.json`](reference/query-templates.json)
- **What**: Pre-built query patterns for common analyses
- **Why**: Copy-paste templates for frequent analyses
- **Read if**: Users who want quick patterns to start from
- **Key sections**:
  - Analysis templates
  - FY trends
  - Spending breakdowns
  - Agency-specific queries

### 9. [`guides/CONVERSATION_LOGGING_GUIDE.md`](guides/CONVERSATION_LOGGING_GUIDE.md)
- **What**: Conversation tracking, retrieval, and analytics capabilities
- **Why**: Learn how to leverage conversation history for audit trails and analytics
- **Read if**: System administrators, analytics users, anyone tracking conversation data
- **Key sections**:
  - Conversation management tools
  - Tracking conversation history
  - Analytics and statistics
  - Integration patterns
  - Privacy and data considerations

---

## Tier 4: Operations & Best Practices

**Estimated Time: 1-1.5 hours**

Operational guides for running and maintaining the system.

### 9. [`guides/STRUCTURED_LOGGING_GUIDE.md`](guides/STRUCTURED_LOGGING_GUIDE.md)
- **What**: Logging system architecture and log analysis techniques
- **Why**: Monitor system health and debug issues
- **Read if**: DevOps, operations, developers troubleshooting issues
- **Key sections**:
  - Logging configuration
  - Log formats and fields
  - Log analysis queries
  - Performance monitoring

### 10. [`guides/RATE_LIMITING_AND_RETRY_GUIDE.md`](guides/RATE_LIMITING_AND_RETRY_GUIDE.md)
- **What**: Request throttling, retry strategies, and resilience
- **Why**: Understand limits and how to handle failures gracefully
- **Read if**: Anyone deploying to production, DevOps, developers
- **Key sections**:
  - Rate limiting configuration
  - Retry strategies
  - Error handling
  - Capacity planning

### 11. [`guides/MCP_BEST_PRACTICES_REVIEW.md`](guides/MCP_BEST_PRACTICES_REVIEW.md)
- **What**: Best practices and architectural patterns
- **Why**: Learn recommended patterns for efficiency and maintainability
- **Read if**: Developers, architects, anyone improving the codebase
- **Key sections**:
  - Code organization
  - API usage patterns
  - Performance best practices
  - Security considerations

### 12. [`../DOCKER_GUIDE.md`](../DOCKER_GUIDE.md)
- **What**: Complete Docker setup, deployment, and orchestration guide
- **Why**: Deploy the server in containerized environments
- **Read if**: DevOps engineers, system administrators, deployment engineers
- **Key sections**:
  - Docker image building
  - Docker Compose orchestration
  - Environment configuration
  - Volume management
  - Production deployment patterns

---

## Tier 5: Development & Operations

**Estimated Time: 1-2 hours**

Guides for development, testing, deployment, and monitoring.

### 13. [`dev/TESTING_GUIDE.md`](dev/TESTING_GUIDE.md)
- **What**: Testing strategies and test execution
- **Why**: Ensure code quality and catch regressions
- **Read if**: Developers, QA engineers
- **Key sections**:
  - Unit testing
  - Integration testing
  - Manual testing procedures
  - Test client usage

### 14. [`dev/SERVER_MANAGER_GUIDE.md`](dev/SERVER_MANAGER_GUIDE.md)
- **What**: Server setup, configuration, and deployment
- **Why**: Deploy and configure the server in different environments
- **Read if**: DevOps, system administrators, deployment engineers
- **Key sections**:
  - Installation options
  - Configuration management
  - Environment setup
  - Claude Desktop integration

### 15. [`dev/PRODUCTION_MONITORING_GUIDE.md`](dev/PRODUCTION_MONITORING_GUIDE.md)
- **What**: Monitoring, alerting, and production readiness
- **Why**: Keep the system healthy and performant in production
- **Read if**: DevOps, operations engineers, SREs
- **Key sections**:
  - Monitoring metrics
  - Health checks
  - Performance tuning
  - Troubleshooting guide

### 16. [`../CHANGELOG.md`](../CHANGELOG.md)
- **What**: Complete project changelog with all releases and improvements
- **Why**: Track changes, understand what's new, plan upgrades
- **Read if**: Everyone (reference document for understanding project evolution)
- **Key sections**:
  - Version history
  - Features by release
  - Performance improvements
  - Bug fixes
  - Breaking changes

### 17. [`guides/FUTURE_RECOMMENDATIONS.md`](guides/FUTURE_RECOMMENDATIONS.md)
- **What**: Suggestions for future enhancements and improvements
- **Why**: Understand the roadmap and planned improvements
- **Read if**: Project maintainers, stakeholders, long-term contributors
- **Key sections**:
  - Planned features
  - Architectural improvements
  - Performance enhancements
  - Community contributions

---

## Reference Materials

### Data & Configuration Files

Located in `docs/reference/` - These are for reference and don't need sequential reading:

- **`api-mappings.json`** - API endpoint mappings (covered in Tier 3)
- **`tools-catalog.json`** - Tool reference (covered in Tier 2)
- **`query-templates.json`** - Query patterns (covered in Tier 3)
- **`field-dictionary.json`** - Field definitions and types
- **`sample-responses.json`** - Example API responses
- **`query-optimization.json`** - Query optimization techniques
- **`reference-data.json`** - Static lookup data
- **`usaspending-api-spec.json`** - Complete OpenAPI spec for USASpending API

### Active Data Files

Located in `src/usaspending_mcp/data/far/`:

- **FAR regulatory files** - JSON files for Federal Acquisition Regulation Parts 14, 15, 16, and 19
- Used by the application for FAR lookups and compliance checking

---

## Learning Paths by Use Case

### 👤 First-Time User
1. README.md (5 min)
2. guides/QUICKSTART.md (10 min)
3. Try the test client (5 min)

**Total: ~20 minutes** - You're ready to use the system!

---

### 👨‍💻 Developer (New to Project)
1. README.md
2. guides/QUICKSTART.md
3. dev/ARCHITECTURE_GUIDE.md
4. reference/tools-catalog.json (26 tools with examples)
5. guides/CONVERSATION_LOGGING_GUIDE.md (new - conversation management)
6. dev/TESTING_GUIDE.md
7. guides/MCP_BEST_PRACTICES_REVIEW.md

**Total: ~2.5 hours** - Ready to contribute code and understand conversation tracking!

---

### 🔧 DevOps/Operations Engineer
1. README.md
2. guides/QUICKSTART.md
3. dev/ARCHITECTURE_GUIDE.md
4. dev/SERVER_MANAGER_GUIDE.md
5. DOCKER_GUIDE.md (new - Docker deployment)
6. guides/RATE_LIMITING_AND_RETRY_GUIDE.md
7. guides/STRUCTURED_LOGGING_GUIDE.md
8. guides/CONVERSATION_LOGGING_GUIDE.md (new - conversation tracking)
9. dev/PRODUCTION_MONITORING_GUIDE.md

**Total: ~2.5 hours** - Ready to deploy, monitor, and manage conversations!

---

### 📊 Government Analyst/Procurement Professional
1. README.md
2. guides/QUICKSTART.md
3. reference/tools-catalog.json
4. guides/FAR_ANALYTICS_GUIDE.md
5. reference/query-templates.json
6. guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md

**Total: ~1.5 hours** - Ready to analyze spending and FAR compliance!

---

### 🏗️ Architect/Technical Lead
1. README.md
2. dev/ARCHITECTURE_GUIDE.md
3. guides/MCP_BEST_PRACTICES_REVIEW.md
4. guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md
5. dev/PRODUCTION_MONITORING_GUIDE.md
6. guides/FUTURE_RECOMMENDATIONS.md

**Total: ~2 hours** - Understand the full system and roadmap!

---

## Documentation Structure

```
docs/
├── guides/                      # User guides and tutorials
│   ├── QUICKSTART.md           # 👈 Start here!
│   ├── STRUCTURED_LOGGING_GUIDE.md
│   ├── CONVERSATION_LOGGING_GUIDE.md    # ✨ NEW - Conversation tracking
│   ├── RATE_LIMITING_AND_RETRY_GUIDE.md
│   ├── FAR_ANALYTICS_GUIDE.md
│   ├── MCP_BEST_PRACTICES_REVIEW.md
│   ├── MULTI_TOOL_ANALYTICS_ARCHITECTURE.md
│   └── FUTURE_RECOMMENDATIONS.md
├── dev/                         # Developer documentation
│   ├── ARCHITECTURE_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── SERVER_MANAGER_GUIDE.md
│   └── PRODUCTION_MONITORING_GUIDE.md
├── data/                        # Application data files
│   └── far/                     # FAR regulatory data (Parts 14-19)
├── reference/                   # Reference documentation
│   ├── tools-catalog.json
│   ├── api-mappings.json
│   ├── query-templates.json
│   ├── field-dictionary.json
│   ├── sample-responses.json
│   ├── query-optimization.json
│   ├── reference-data.json
│   └── usaspending-api-spec.json
└── DOCUMENTATION_ROADMAP.md     # This file!

Root level:
├── DOCKER_GUIDE.md              # ✨ NEW - Docker deployment
├── CHANGELOG.md                 # ✨ NEW - Project changelog
├── CLAUDE.md                    # Claude Code instructions
└── README.md                    # Project overview
```

---

## Tips for Effective Learning

1. **Start with README.md** - Always begin here regardless of role
2. **Follow your role path** - Jump to the relevant tier for your use case
3. **Use the Quick Navigation table** - Jump to specific sections quickly
4. **Cross-reference the JSON files** - They provide concrete examples
5. **Test as you learn** - Use QUICKSTART.md to get hands-on experience
6. **Ask questions** - The documentation is comprehensive but reach out if something is unclear

---

## Quick Reference

| Document | Best For | Time |
|----------|----------|------|
| README.md | Overview | 5 min |
| guides/QUICKSTART.md | Getting started | 10 min |
| dev/ARCHITECTURE_GUIDE.md | Understanding design | 20 min |
| reference/tools-catalog.json | Finding tools (26 tools) | 10 min |
| guides/CONVERSATION_LOGGING_GUIDE.md | Conversation tracking | 15 min |
| DOCKER_GUIDE.md | Docker deployment | 15 min |
| guides/MULTI_TOOL_ANALYTICS_ARCHITECTURE.md | Advanced workflows | 20 min |
| guides/FAR_ANALYTICS_GUIDE.md | FAR compliance | 15 min |
| guides/STRUCTURED_LOGGING_GUIDE.md | Logging & debugging | 15 min |
| guides/RATE_LIMITING_AND_RETRY_GUIDE.md | Production setup | 10 min |
| dev/TESTING_GUIDE.md | Writing tests | 15 min |
| dev/SERVER_MANAGER_GUIDE.md | Deployment | 15 min |
| dev/PRODUCTION_MONITORING_GUIDE.md | Monitoring | 15 min |
| CHANGELOG.md | Project history | 10 min |

---

## Last Updated

November 19, 2025

Recent updates:
- Added Conversation Logging Guide (NEW)
- Added Docker deployment guide (NEW)
- Updated tool count to 26 (added conversation management tools)
- Updated all learning paths with new features
- Added CHANGELOG.md reference

## Contributing

If you find documentation unclear or have suggestions for improvements, please open an issue or pull request!
