# CLAUDE.docx Formatting Guide

This guide provides exact specifications for formatting the `CLAUDE.docx` file according to the Document Style Preferences outlined in `CLAUDE.md`.

---

## Color Specifications

### Primary Blue (Imbue Blue)

**RGB Values**: 32, 76, 141

**Hex Code**: #204C8D

**Use For**:
- All heading text (H1, H2, H3)
- Bold emphasis on key terms (when styling in blue)
- Document headers and section titles

**How to Apply in Word**:
1. Select the text to color
2. Go to `Home` tab → `Font Color` dropdown
3. Click `More Colors...`
4. Go to `Custom` tab
5. Enter RGB: R: 32, G: 76, B: 141
6. Click OK

### Black Text

**RGB Values**: 0, 0, 0

**Use For**:
- Body text
- Regular paragraph text
- Non-emphasized content

---

## Font Specifications

### Primary Font: Montserrat

**Used For**: All text in the document (titles, headers, body, bullets, captions)

**Note**: If Montserrat is not available on your system:
- Fallback 1: Calibri
- Fallback 2: Arial
- Do NOT use: Cambria, Times New Roman, or system defaults

**How to Apply in Word**:
1. Select all text (Ctrl+A on Windows, Cmd+A on Mac)
2. Go to `Home` tab → `Font` dropdown
3. Select `Montserrat`
4. Apply to entire document

---

## Heading Specifications

### Title (H1) - Document Title

**Formatting**:
- Font: Montserrat
- Size: 16pt
- Weight: Bold
- Color: Blue (RGB 32, 76, 141)
- Spacing: 6pt after

**Example**:
```
CLAUDE.md
```

**How to Apply**:
1. Select the title text at the beginning of document
2. Font: Montserrat
3. Size: 16pt
4. Make Bold (Ctrl+B / Cmd+B)
5. Font Color: RGB 32, 76, 141
6. Paragraph spacing: 6pt after

---

### Heading 1 (H2) - Major Sections

**Formatting**:
- Font: Montserrat
- Size: 13pt
- Weight: Bold
- Color: Blue (RGB 32, 76, 141)
- Spacing: 6pt after
- Note: Should be preceded by horizontal line/page break in original

**Examples**:
```
## Project Overview
## CLAUDE.md file updates
## Document Style Preferences
## Common Development Commands
```

**How to Apply**:
1. Select the H2 heading text
2. Font: Montserrat
3. Size: 13pt
4. Make Bold (Ctrl+B / Cmd+B)
5. Font Color: RGB 32, 76, 141
6. Paragraph spacing: 6pt after

---

### Heading 2 (H3) - Subsections

**Formatting**:
- Font: Montserrat
- Size: 12pt
- Weight: Bold
- Color: Blue (RGB 32, 76, 141)
- Spacing: 6pt after

**Examples**:
```
### Setup & Installation
### Running the Server
### Testing the Server
### Fonts
### Headers
```

**How to Apply**:
1. Select the H3 heading text
2. Font: Montserrat
3. Size: 12pt
4. Make Bold (Ctrl+B / Cmd+B)
5. Font Color: RGB 32, 76, 141
6. Paragraph spacing: 6pt after

---

## Spacing Specifications

### Line Spacing

**Value**: 1.0 (Single spacing)

**Applied To**: All text in document

**How to Apply in Word**:
1. Select all text (Ctrl+A / Cmd+A)
2. Go to `Home` tab → `Line Spacing` dropdown
3. Select `1.0`

---

### Paragraph Spacing

**After Paragraph**: 6pt
**Before Paragraph**: 0pt (none)

**Applied To**: All paragraphs, headings, bullet points

**How to Apply in Word**:
1. Select the paragraph(s)
2. Go to `Home` tab → `Paragraph Spacing` dropdown
3. Or right-click → `Paragraph...`
4. Set:
   - `Spacing Before`: 0pt
   - `Spacing After`: 6pt
5. Apply

**Keyboard Shortcut** (Mac):
- Cmd+0 to remove spacing before
- Then manually set 6pt after

---

## Bullet Point Specifications

### Bullet Style

**Type**: Circle bullets (•)

**Not Allowed**: Hyphens (-) or dashes (—)

**Indentation**:
- First level: 0.25 inches from left margin
- Second level: 0.5 inches from left margin
- Do NOT exceed 2 nesting levels

**How to Apply in Word**:
1. Select the bulleted list
2. Go to `Home` tab → `Bullet List` dropdown
3. Look for circle bullet (•) option
4. If not available: `Define New Bullet...`
5. Select "●" symbol
6. Click OK

**Alternative - Manual Bullet**:
1. Type the bullet character directly (copy from below)
2. Adjust indentation using Tab key

**Copy this circle bullet**: •

---

## Text Formatting Examples

### Bold Text (Key Terms)

**Format**: `**text**` in markdown → **text** in Word

**How to Apply**:
- Select text
- Press Ctrl+B (Windows) or Cmd+B (Mac)
- Or click Bold button in toolbar

**Example**: The **QueryPlanner** class analyzes queries.

---

### Italic Text (Rare)

**Format**: Used only for Latin terms, variables

**How to Apply**:
- Select text
- Press Ctrl+I (Windows) or Cmd+I (Mac)
- Or click Italic button in toolbar

**Example**: The variable *x* represents count.

---

### Code/Monospace (Inline)

**Format**: `` `text` `` in markdown → `code` in Word

**Font**: Courier New or Consolas (monospace font)

**How to Apply**:
1. Select the code text
2. Change font to Courier New or Consolas
3. Optional: Light gray background for visibility

**Example**: Use the `search_federal_awards()` function.

---

## Code Block Specifications

### Code Block Formatting

**Font**: Courier New or Consolas (monospace)
**Size**: 10pt (smaller than body text)
**Background**: Light gray (#F5F5F5 or similar)
**Padding**: 6pt on all sides

**How to Apply in Word**:
1. Select the code block text
2. Font: Courier New or Consolas
3. Size: 10pt
4. Right-click → `Paragraph...` → `Borders and Shading`
5. Set background color to light gray
6. Add 6pt padding

---

## Table Specifications

### Table Formatting

**Font**: Montserrat (same as body)
**Font Size**: 11pt (slightly smaller)
**Header Row**: Bold, blue background or bold blue text
**Borders**: Visible borders between cells

**How to Apply in Word**:
1. Insert table or convert markdown table
2. Select header row
3. Make text **Bold** and color **Blue (RGB 32, 76, 141)**
4. Ensure all borders are visible
5. Set cell padding to 4pt

---

## Step-by-Step Formatting Workflow

### Phase 1: Font Application (5 minutes)
1. Open `CLAUDE.docx` in Microsoft Word
2. Select all text: Ctrl+A (Windows) or Cmd+A (Mac)
3. Change font to **Montserrat**
4. Keep at default 11pt for now

### Phase 2: Spacing Setup (3 minutes)
1. Select all text: Ctrl+A / Cmd+A
2. Set line spacing to **1.0** (single)
3. Set paragraph spacing to **6pt after, 0pt before**

### Phase 3: Header Formatting (10 minutes)
1. Find first H1 (document title - "CLAUDE.md")
   - Size: 16pt, Bold, Blue (RGB 32, 76, 141)

2. Find all H2 sections (starts with "##")
   - Size: 13pt, Bold, Blue (RGB 32, 76, 141)
   - Examples: "Project Overview", "CLAUDE.md file updates", etc.

3. Find all H3 subsections (starts with "###")
   - Size: 12pt, Bold, Blue (RGB 32, 76, 141)
   - Examples: "Setup & Installation", "Running the Server", etc.

### Phase 4: Bullet Points (5 minutes)
1. Find all bulleted lists
2. Ensure bullets are circles (•), not hyphens or dashes
3. Check indentation is clean
4. Remove any inconsistent bullet styles

### Phase 5: Code Blocks (5 minutes)
1. Find all code blocks (bash, python, etc.)
2. Change font to Courier New or Consolas
3. Reduce font size to 10pt
4. Add light gray background: #F5F5F5

### Phase 6: Tables (3 minutes)
1. Find all tables
2. Make header row bold and blue
3. Ensure all borders are visible
4. Check alignment and padding

### Phase 7: Final Review (5 minutes)
1. Skim through entire document
2. Check consistency of formatting
3. Verify no Cambria, Arial, or Times New Roman text
4. Ensure all text is Montserrat
5. Save as `CLAUDE.docx`

**Total Time**: ~35 minutes

---

## Quick Reference Checklist

- [ ] Font: Montserrat throughout document
- [ ] H1 Title: 16pt, bold, blue (RGB 32, 76, 141)
- [ ] H2 Sections: 13pt, bold, blue (RGB 32, 76, 141)
- [ ] H3 Subsections: 12pt, bold, blue (RGB 32, 76, 141)
- [ ] Line spacing: 1.0 (single)
- [ ] Paragraph spacing: 6pt after, 0pt before
- [ ] Bullets: Circle (•), not hyphens
- [ ] Code blocks: Courier New/Consolas, 10pt, gray background
- [ ] No Cambria, Arial, or Times New Roman
- [ ] No extra spacing or blank lines
- [ ] Tables: Header row bold and blue
- [ ] All links formatted consistently

---

## Troubleshooting

### Montserrat Font Not Found

**Problem**: Montserrat font is not installed on your system

**Solution**:
1. Download Montserrat from [Google Fonts](https://fonts.google.com/specimen/Montserrat)
2. Install the font on your system
3. Restart Microsoft Word
4. Apply Montserrat to the document

**Temporary Fallback**: Use Calibri or Arial (not ideal)

---

### Colors Not Appearing Correctly

**Problem**: Blue color looks different than expected

**Solution**:
1. Double-check RGB values: R: 32, G: 76, B: 141
2. Verify you're using RGB mode, not HSL or other
3. Try entering Hex code: #204C8D
4. Ensure document is in "Edit Mode" not "Read Mode"

---

### Bullets Not Converting Properly

**Problem**: Bullets appear as dashes or wrong character

**Solution**:
1. Delete incorrect bullets
2. Go to Home tab → Bullet List dropdown
3. Select circle bullet (●)
4. Manually retype bullets if needed
5. Copy circle from this guide: •

---

### Code Font Issues

**Problem**: Code blocks look misaligned

**Solution**:
1. Select the code block
2. Change font to Courier New (consistent monospace)
3. Ensure size is 10pt
4. Add background color: #F5F5F5
5. Add 6pt padding on all sides

---

## Formatting Specifications Summary

| Element | Font | Size | Weight | Color | Spacing |
|---------|------|------|--------|-------|---------|
| **Title (H1)** | Montserrat | 16pt | Bold | RGB 32,76,141 | 6pt after |
| **Section (H2)** | Montserrat | 13pt | Bold | RGB 32,76,141 | 6pt after |
| **Subsection (H3)** | Montserrat | 12pt | Bold | RGB 32,76,141 | 6pt after |
| **Body Text** | Montserrat | 11pt | Regular | Black | 6pt after |
| **Bold Emphasis** | Montserrat | 11pt | Bold | Black | 6pt after |
| **Code (inline)** | Courier New | 11pt | Regular | Black | — |
| **Code (block)** | Courier New | 10pt | Regular | Black | Gray bg |
| **Bullets** | Montserrat | 11pt | Regular | Black | 6pt after |
| **Table Header** | Montserrat | 11pt | Bold | RGB 32,76,141 | — |

---

## Color Reference Card

### Blue (Imbue Blue)
- **RGB**: 32, 76, 141
- **Hex**: #204C8D
- **Use**: Headers H1-H3, emphasis
- **NOT for**: Body text, regular bullets

### Black (Text)
- **RGB**: 0, 0, 0
- **Hex**: #000000
- **Use**: All body text, bullets, emphasis

### Light Gray (Code Background)
- **RGB**: 245, 245, 245
- **Hex**: #F5F5F5
- **Use**: Code block backgrounds

---

## Need Help?

If you encounter formatting issues:

1. **Reference this guide** - Check the specific element type
2. **Use the Quick Reference Checklist** - Verify each item
3. **Check the Troubleshooting section** - Find your issue
4. **Compare with examples** - See how it should look
5. **Start over** if needed - Format one section at a time

---

Last Updated: November 23, 2025

This guide ensures consistent, professional formatting for all CLAUDE.docx documents across the project.
