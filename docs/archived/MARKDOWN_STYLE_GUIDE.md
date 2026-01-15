# Markdown Style Guide

This document provides comprehensive styling conventions for all `.md` files in the USASpending MCP Server project.

---

## File Structure & Hierarchy

### 1. Main Title (H1)

- **Only one H1 per file** - Use `# Title` for the main document title
- Should be at the very top of the file
- No other content should be at the same level as H1

```markdown
# My Document Title

Content starts here...
```

### 2. Major Sections (H2)

- Use `## Section Title` for major section divisions
- Separate H2 sections with a horizontal line (`---`) for clarity
- Each major section should address a distinct topic

```markdown
---

## Section One

Content here...

---

## Section Two

Content here...
```

### 3. Subsections (H3)

- Use `### Subsection Title` for subsections under H2
- No line breaks required between H3 sections
- Use for grouping related content within a major section

```markdown
## Major Topic

### Related Subtopic 1

Content...

### Related Subtopic 2

Content...
```

### 4. Sub-subsections (H4)

- Use `#### Sub-subsection Title` sparingly
- Avoid going deeper than H4 in most documents
- If you need H4, consider reorganizing into separate H3 sections instead

---

## Text Formatting

### Bold Text

- Use `**text**` for emphasis on key concepts
- Use bold for:
  - Important terms on first mention
  - Parameter names in descriptions
  - Key decision points
  - Emphasis in explanations

```markdown
The **QueryPlanner** class analyzes queries before execution.
```

### Italic Text

- Use `*text*` sparingly, only for:
  - Latin terms (e.g., *et al.*, *i.e.*)
  - Variables in mathematical expressions
  - File paths that are being mentioned in passing

```markdown
The variable *x* represents the request count.
```

### Code (Inline)

- Use backticks for:
  - Function names: `search_federal_awards()`
  - Class names: `QueryPlanner`
  - Variable names: `query_type`
  - File names: `server.py`
  - Command names: `pip install`
  - Constant values: `None`, `True`, `False`

```markdown
Use the `QueryPlanner` class to analyze query feasibility.
```

### Links

- Use standard markdown link format: `[Link Text](URL)`
- Keep link text descriptive (not "click here")
- Use relative paths for internal project links
- Use full URLs for external links

```markdown
[CLAUDE.md](CLAUDE.md) - Internal link to project file
[Documentation](docs/guides/QUICKSTART.md) - Link to guide
[Python Docs](https://docs.python.org/) - External link
```

---

## Lists

### Bullet Lists (Unordered)

- Use `-` or `*` consistently (project standard: `*`)
- One space after bullet marker
- Use two spaces for nested items

```markdown
* First item
* Second item
  * Nested item 1
  * Nested item 2
* Third item
```

### Numbered Lists (Ordered)

- Use `1.` for numbered lists (markdown will auto-number)
- Use for step-by-step procedures or ranked items
- Maintain consistent indentation for nested items

```markdown
1. First step
2. Second step
   * Sub-point A
   * Sub-point B
3. Third step
```

### Mixed Lists

- When combining bullets and numbers, use bullets for non-sequential and numbers for sequential
- Maintain consistent nesting levels

```markdown
1. First procedure
   * Detail A
   * Detail B
2. Second procedure
   * Detail A
```

---

## Code Blocks

### Syntax-Highlighted Code

- Use triple backticks with language specification
- Always specify the language (python, bash, json, etc.)
- Include a blank line before and after code blocks

```python
# Python code example
def example():
    return "Hello World"
```

```bash
# Bash command example
pip install -e ".[dev]"
```

```json
# JSON configuration example
{
  "key": "value",
  "number": 42
}
```

### Command Examples

For bash/shell commands:

```bash
# Commands to run
./start_mcp_server.sh

# Or with environment variables
PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.server
```

---

## Tables

### Table Formatting

- Use standard markdown table syntax
- Include header separator with dashes
- Align columns using `:` in separator row
- Left-align text columns (default)
- Center-align category columns

```markdown
| Feature | Description | Status |
|---------|-------------|--------|
| Layer 1 | Query Planning | ✅ Active |
| Layer 2 | Error Handling | ✅ Active |
```

### Table Best Practices

- Keep tables readable (not too many columns)
- Use checkmarks (✅) and crosses (❌) for status
- Use version numbers (v2.2.0) for versioning tables
- Keep column widths reasonable in source markdown

---

## Special Elements

### Blockquotes

- Use `>` for important notes or quotes
- Use sparingly, only for significant callouts

```markdown
> **Important**: This is a critical note that readers should pay attention to.
```

### Horizontal Rules

- Use `---` on its own line to separate major sections
- Place before and after H2 sections for visual clarity
- Never use multiple in a row

```markdown
## Previous Section

Content here...

---

## Next Section

Content here...
```

### Line Breaks

- Use blank lines to separate logical sections within content
- Don't use excessive blank lines (max 1 blank line between paragraphs)
- Use 2 blank lines around major structural breaks

```markdown
Paragraph 1.

Paragraph 2.

---

## New Section

Content begins...
```

---

## Document Patterns

### Introduction/Overview

- Start with a brief one-line description
- Follow with context about the document's purpose
- End intro section with a horizontal rule

```markdown
# Document Title

Brief description of what this document covers.

Additional context about why this matters and how to use it.

---

## Main Content Begins...
```

### Key Concepts Section

- Use clear heading like "## Key Concepts" or "## Overview"
- Explain terms and concepts before diving into details
- Use bold for key terms

```markdown
## Key Concepts

**QueryPlanner**: Analyzes query feasibility before execution.
**ResultVerifier**: Validates results against authoritative sources.
```

### Code Examples Section

- Use "## Examples" or "## Usage Examples"
- Include realistic, copy-paste-ready examples
- Comment code with explanations

```markdown
## Examples

### Example 1: Basic Usage

```python
# Your code example here
```

### Example 2: Advanced Usage

```python
# More complex example
```
```

### Reference/Table of Contents

- Use bulleted list with links for navigation
- Organize by topic or level
- Include descriptive text for each link

```markdown
## Documentation

- **[QUICKSTART.md](docs/guides/QUICKSTART.md)** - Get started in 5 minutes
- **[ARCHITECTURE_GUIDE.md](docs/dev/ARCHITECTURE_GUIDE.md)** - System design overview
- **[TESTING_GUIDE.md](docs/dev/TESTING_GUIDE.md)** - Testing strategies
```

---

## Emoji Usage

### When to Use Emojis

- Use emojis in lists for visual categorization (sparingly)
- Use emoji at start of section titles only in lists or tables
- Avoid excessive emoji in body text

### Common Project Emojis

```markdown
✅ - Completed, working, success
❌ - Not working, deprecated, failure
⚠️ - Warning, caution, attention needed
ℹ️ - Information, note
🔧 - Configuration, setup
📚 - Documentation, learning
🚀 - Features, launch
⚙️ - Technical, architecture
```

### Emoji in Lists

```markdown
- ✅ **Implemented**: QueryPlanner class
- ❌ **Not Yet**: Advanced caching
- ⚠️ **In Progress**: Performance optimization
```

---

## Specific Elements by Document Type

### README Files

- Start with project title and one-line description
- Include Features section early (with emojis for visual interest)
- Follow with Quick Start section
- End with links to other documentation
- Structure: Overview → Features → Quick Start → Detailed Sections → Resources

### Guide Files

- Start with purpose statement
- Include table of contents if lengthy (>500 lines)
- Use consistent H2 sections for topics
- End with Resources or References section
- Include "Last Updated" date at bottom

### Changelog Files

- Use H2 for version numbers (## [2.2.0] - 2025-11-23)
- Use H3 for section types (### Added, ### Changed, ### Fixed)
- Use bullet lists for individual changes
- Include impact information when relevant
- Keep versions in reverse chronological order (newest first)

### API/Reference Documentation

- Use H2 for major concepts
- Use H3 for methods/endpoints/tools
- Include parameter tables where relevant
- Use code blocks for request/response examples
- Use clear naming conventions

---

## Consistency Rules

### Capitalization

- Use Title Case for all headings (H1, H2, H3, H4)
- Use lowercase for inline references to code: `function_name()`, `ClassName`
- Use proper title case for proper nouns: Python, JavaScript, FastMCP, USASpending

### Terminology

- Use consistent terminology throughout the document
- Define non-standard terms on first use
- Use bold on first definition: **Term**: Definition here.

### Spacing

- No spaces inside inline code: `function()` not ` function() `
- One space after list markers: `* Item` not `*Item`
- No extra spaces around emphasis: `**word**` not `** word **`
- Blank line before and after code blocks

### Punctuation

- Use standard English punctuation
- Use em-dashes (—) instead of hyphens (-) for em-dash usage
- Use backticks, not quotes, for code: use `code` not "code"

---

## File-Specific Conventions

### README.md

```markdown
# Project Name

One-line description.

[![Badge](url)](link) - Optional status badges

## Features

- Feature with emoji
- Feature with emoji

## Quick Start

### 1. Setup
...

### 2. Run
...

## Documentation

Links to other docs

## Contributing

Contribution guidelines

## License

License information
```

### CHANGELOG.md

```markdown
# Changelog

Description of format.

---

## [Version] - Date

### Added
- New feature
- New tool

### Changed
- Behavioral change

### Fixed
- Bug fix

### Removed
- Deprecated feature

---

## Older Releases
```

### docs/guides/*

```markdown
# Guide Title

Brief description and purpose.

## Table of Contents

- [Section 1](#section-1)
- [Section 2](#section-2)

---

## Section 1

Content with H3 subsections

### Topic 1.1
...

### Topic 1.2
...

---

## Section 2

Content with H3 subsections

---

## Resources

Related documentation links

---

Last Updated: November 23, 2025
```

---

## Common Mistakes to Avoid

❌ **Don't:**
- Use multiple H1 headings in one document
- Use inconsistent list markers (mix `-` and `*`)
- Put code in quotes instead of backticks
- Use `__bold__` instead of `**bold**`
- Include trailing spaces at end of lines
- Mix tabs and spaces for indentation
- Create overly nested lists (more than 3 levels)

✅ **Do:**
- Use one H1 per file
- Stick to `*` for all bullet points
- Use backticks for all code
- Use `**bold**` consistently
- Keep lines clean with no trailing spaces
- Use spaces consistently for indentation
- Keep nesting to 2-3 levels maximum

---

## Validation

### Before Committing

- [ ] Single H1 at document start
- [ ] H2 sections separated by `---`
- [ ] All code blocks have language specification
- [ ] All links are valid (relative or absolute)
- [ ] No trailing spaces at line ends
- [ ] Consistent list markers throughout
- [ ] Bold used for emphasis and key terms
- [ ] Tables are properly formatted
- [ ] No excessive blank lines

### Markdown Linting

Consider using markdown linters to validate:

```bash
# Install markdownlint
npm install -g markdownlint-cli

# Lint all markdown files
markdownlint '**/*.md'
```

---

## Questions?

If you have questions about markdown style conventions not covered in this guide, please:

1. Check how similar elements are formatted in existing documents
2. Maintain consistency with the project's existing patterns
3. Refer to [CommonMark Specification](https://spec.commonmark.org/) for markdown standards

---

Last Updated: November 23, 2025
