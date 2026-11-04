# Publishing the dashboard preview

The selected host is **GitHub Pages**, using the already connected `IsraelMamann/dashboard` repository. The `gh-pages` branch contains only the public fictional-data HTML and `.nojekyll`. Publishing does not require a new Vercel account or token.

## One-time external step

Open https://github.com/IsraelMamann/dashboard/settings/pages while signed in to GitHub with repository settings access. Under Build and deployment, choose Source → Deploy from a branch; choose Branch → gh-pages and folder → / (root); click Save. GitHub then builds the site and displays its URL. Enabling Pages is required before the site can be called live. Verify the resulting published site after the build completes.

## Updating the preview

1. Make and test changes to the local prototype.
2. Run `python deployment/prepare_preview.py` to remove embedded real records and generate `deployment/public/index.html`.
3. Run `python deployment/test_public_preview.py` to check the output.
4. Fetch the current publishing tip with `git fetch origin refs/heads/gh-pages:refs/remotes/origin/gh-pages`, then run `python deployment/prepare_github_pages.py` to create a commit containing exactly the sanitized HTML and `.nojekyll`, without changing the working branch.
5. Push the exact SHA printed by the previous command to `refs/heads/gh-pages` using the existing HTTPS Git authentication. Do not force-push; diagnose concurrent changes first.
6. Verify GitHub Pages' build and the published site before claiming the update is live.

The public preview is a demonstration, not the private production application. Sign-in and roles remain simulated, uploaded reports are processed only in the current browser session, and no real employee sample is embedded. A private team application still needs real verified sign-in, enforced permissions and durable data storage. Do not deploy the private prototype directory or its archives.

The Vercel configuration and API deployment helper are an alternative only; they require a separately configured hosting credential and have not been used to deploy this preview. GitHub Pages does not honor custom HTTP headers from vercel.json. Privacy for this preview comes from removing private records before deployment, not from those headers.

The public setup helper at `/setup/` provides a one-click copy button for the database schema. It contains no employee records or secret credentials. For the authenticated release, use `--workspace` after completing the Supabase setup in `backend/SETUP.md`.
