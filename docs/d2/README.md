# Diagrams — D2 Source Files

All architecture diagrams in `design.md` are generated from these D2 source files using [Terrastruct D2](https://d2lang.com/) with **sketch** style.

## Files

| D2 Source | Generated SVG | Description |
|-----------|---------------|-------------|
| `architecture.d2` | `architecture.svg` | System architecture overview |
| `scan-flow.d2` | `scan-flow.svg` | Skill scanning flow |
| `install-flow.d2` | `install-flow.svg` | Forward install flow (copy/link) |
| `bidirectional-flow.d2` | `bidirectional-flow.svg` | Bidirectional sync flow |
| `check-flow.d2` | `check-flow.svg` | Diff detection flow |

## Prerequisites

Install D2 (v0.7.1+):

```bash
# Windows — download from GitHub releases
curl -L https://github.com/terrastruct/d2/releases/download/v0.7.1/d2-v0.7.1-windows-amd64.tar.gz -o d2.tar.gz
tar -xzf d2.tar.gz
# Add d2-v0.7.1/bin to PATH, or use full path

# macOS
brew install terrastruct/tap/d2

# Linux
curl -fsSL https://d2lang.com/install.sh | sh -s --
```

## Rendering

Render all diagrams with sketch style:

```bash
cd docs/d2
for f in *.d2; do
  d2 --sketch "$f" "${f%.d2}.svg"
done
```

Or individually:

```bash
d2 --sketch architecture.d2 architecture.svg
```

## Style Convention

- **Green (#4CAF50)**: Start / End / Success states
- **Blue (#2196F3)**: Process / Module boxes
- **Orange (#FF9800)**: Decision diamonds
- **Red (#F44336)**: Skip / Error paths
- **Purple (#9C27B0)**: Platform-specific adapters
- **Dashed arrows**: Optional / periodic flows

## When to Update

Re-render SVGs after modifying any `.d2` file:

1. Edit the `.d2` source
2. Run `d2 --sketch <file>.d2 <file>.svg`
3. Commit both `.d2` and `.svg`
