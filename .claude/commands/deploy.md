---
description: Bump BUILD, commit, and push to main (GitHub Pages auto-deploys)
argument-hint: [optional commit message]
---
Deploy the current working changes to production (GitHub Pages).

1. Run `git status` and summarize what changed.
2. If `ferry.html` changed, bump `const BUILD = 'rNN'` to the next revision (e.g. r73 → r74). If only docs/config/scripts changed, skip the bump.
3. Stage everything: `git add -A`.
4. Commit. If a message was provided in "$ARGUMENTS", base the commit message on it; otherwise write a concise conventional-commit message inferred from the diff. End the commit body with:
   `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
5. Push: `git push origin main`.
6. Confirm the push succeeded. Note it goes live via GitHub Pages in ~30s, and that `?bust=N` on the URL forces a refresh on iOS Safari.
