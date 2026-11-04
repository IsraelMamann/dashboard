# The Big Plan enrollment dashboard

A private, email-verified enrollment workspace hosted on GitHub Pages, with Supabase shared-report storage and database-enforced roles. A fictional demo is available at `/demo/` once the authenticated release is published. Public frontend files do not include real employee records.

## Sources

- `app/core.html`: sanitized dashboard source, including branded assets and calculation/UI logic. It contains fictional comparison data and an empty embedded real-report array.
- `app/cloud.js` and `cloud.css`: real Supabase verified-email sign-in (code or secure link), session handling, shared report/assignment operations, member management, and server-checked exports.
- `app/config.js`: public project connection settings. This file may contain only a publishable/anon key, never a secret/service-role key.
- `backend/schema.sql`: tables, database field allowlist, authenticated membership, report operations, permissions, and row-level security.
- `backend/SETUP.md`: external project, database and email-delivery steps. Live mail delivery and owner sign-in must be validated separately from local tests.

## Build and test

Use Python 3, Node, Playwright and Chromium for local verification. `npm ci --prefix backend` installs the pinned PostgreSQL test engine.

```
python deployment/prepare_preview.py
python deployment/prepare_workspace.py
npm test --prefix backend
python app/test_workspace.py
python deployment/test_public_preview.py
```

The browser contract test uses a mocked authentication/API service; database tests exercise real PostgreSQL functions and permissions locally. Neither proves that live SMTP email delivery is configured. Follow `backend/SETUP.md` for production activation and live verification.

When an original private prototype is present locally, the preview builder strips its real sample records and synchronizes the sanitized core. On a clean clone it builds from `app/core.html`. Real local CSVs, prototype HTML with employee data, screenshots, archives and generated release folders are ignored by Git.

## Deploy

Fetch the current publishing branch, build/test, run `python deployment/prepare_github_pages.py --workspace`, then push the exact generated commit to `gh-pages` without force. See `deployment/README.md`. The temporary Git index includes only the approved release files; it does not stage local private data or switch the working branch.

New-group totals are current-year only: identifying a 2026 new-business cohort requires earlier enrollment or activation history. No absent history is represented as zero growth.
