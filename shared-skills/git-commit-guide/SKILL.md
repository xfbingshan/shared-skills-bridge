---
name: git-commit-guide
description: "Guidelines for writing clear, atomic Git commits and professional commit messages. Use when the user asks about Git commit best practices, writing commit messages, commit message conventions, or how to structure Git history."
---

# Git Commit Guide

## Core Principles

1. **Atomic commits** — Each commit should represent a single logical change.
2. **Self-contained messages** — A commit message should explain *why*, not just *what*.
3. **Readable history** — `git log` should tell a story that future developers can follow.

## Commit Message Format

Follow the conventional commit style:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Use when |
|------|----------|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `docs` | Documentation-only changes |
| `style` | Code style changes (formatting, semicolons, etc.) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or correcting tests |
| `chore` | Maintenance tasks (build, deps, tooling) |

### Subject Line Rules

- Use imperative mood: "Add feature" not "Added feature" or "Adds feature"
- Max 50 characters
- No trailing period
- Start with a capital letter

### Body Rules

- Wrap at 72 characters
- Explain *why* the change is needed
- Reference issues: `Closes #123`

## Examples

**Good:**
```
feat(auth): Add OAuth2 login with Google

Implement Google OAuth2 flow to replace legacy username/password
authentication. This reduces support tickets related to password
resets and improves security posture.

Closes #456
```

**Bad:**
```
update auth stuff

google login
```

## Atomic Commit Checklist

Before committing, ask:
- [ ] Does this commit mix unrelated changes? (If yes, split it.)
- [ ] Would reverting this commit break anything unrelated? (If yes, split it.)
- [ ] Can someone understand the change from the message alone?

## References

See [references/conventional-commits-spec.md](references/conventional-commits-spec.md) for the full specification.
