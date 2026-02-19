# Research Auditor — Documentation

## ARCHITECTURE.md

The main architecture document covers:

- Purpose and function
- Data structures
- Workflows (with Mermaid diagrams)
- Orchestrator–Researcher–Critic communication
- Logfire observability
- Supabase tables and data paths

## Generating a PDF

To produce a PDF from `ARCHITECTURE.md` with rendered Mermaid diagrams:

### Option 1: md-to-pdf (Node.js)

```bash
npx md-to-pdf ARCHITECTURE.md
```

### Option 2: Mermaid CLI + Pandoc

```bash
# Render Mermaid to SVG (extract diagrams first), then use pandoc
npx @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o diagram.svg
pandoc ARCHITECTURE.md -o ARCHITECTURE.pdf
```

### Option 3: VS Code / Cursor

Use an extension such as "Markdown PDF" to export the markdown file to PDF. Mermaid diagrams in the document will be rendered if the extension supports them.
