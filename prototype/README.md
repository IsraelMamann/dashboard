# Enrollment pulse prototype

Open `index.html` in a browser. It is self-contained and requires no installation or network access. `preview.png` shows the overview with fictional data.

## Try it

- Start in **Fictional comparison demo** to explore renewal/new group metrics, the leaderboard, state/carrier breakdowns, and employee follow-up lists.
- Choose **Uploaded 2026 sample** to inspect actual baseline aggregates. It contains 14,850 source rows, 8,236 ENROLLED employees, and 11,925 covered lives for those employees. No 2027 performance is inferred from this sample alone.
- Click a group. The employee list defaults to **Not yet returned**; switch categories or export contacts.
- Switch the role to Viewer to see the export restriction and admin restriction. Viewers can see contact details.
- In Administration, use the supplied sample as a provisional baseline or upload a replacement baseline. Upload a complete current-year CSV to compute comparisons. Nothing uploads to a server. Uploaded data, assignments, and history last only for the open session.
- Edit account manager assignments. They apply to both years. New groups without assignments remain Unassigned.

## Implemented comparison rules

- Baseline active population: ENROLLED only. Company January 1, 2026 benchmark: ENROLLED/TERMINATED rows with effective dates on/before that date and termination dates after it (or no termination date). Date-boundary semantics should be confirmed against the finalized export.
- Current full snapshot: ENROLLED, APPLICATION_READY, PAYMENT_READY, STUCK. Current uploads are assumed to be the intended January 1, 2027 report; production must validate coverage dates and year.
- One row is one employee. Covered lives are summed, with the employee already included.
- Email matching is lowercase, trimmed, with every `delete` substring removed. Status still determines whether a row counts.
- Groups absent from the baseline report are new. This sample has no explicit group ID column, so company_name is the provisional group key.
- Company renewal growth uses the January 1 benchmark, including prior groups without current enrollment. New-group totals are separate.
- Group/account-manager growth uses the baseline ENROLLED population, with only groups that have qualifying current enrollment included in the ranking. Growth defaults to covered lives, with an employee-count toggle. Weighted growth is net additions divided by the fixed company-wide starting population of started renewal groups; ordinary growth uses the manager's own starting population. The retention opportunity view separately includes all renewal groups, including not-started groups.
- Employee moves count as new enrollment in the receiving group. Any qualifying current enrollment under a normalized email means the employee is retained company-wide, including in the original group's follow-up list. No transfer metric is shown.
- State comparisons use the employee's current home state, falling back to the prior state if not returned. State breakdowns count employees only.
- Carrier switches match by normalized email across groups, ignore missing carrier pairs, and compare carrier names only. Carrier shares use whole-company employee denominators even when filtered. Carrier mix is not shown in employee detail rows.

## Prototype boundaries

Authentication, email verification, real invitations, secure role enforcement, durable storage, historical reruns, and automatic January churn finalization are not connected. The role selector and invitation controls are demonstrations. Current report completeness and status/date conventions need validation with the finalized reports.

Only a subset of the provided CSV fields is embedded: employee name/email/phone, company, status, lives, state, carrier, coverage effective date, termination date, consent timestamp, monthly ICHRA allowance/applied amounts, full premium, plan tier, and numeric employee age. SSNs, income, birthdays, street addresses, and dependent details are omitted. This local HTML includes real sample contact data; the default fictional comparison uses example.com addresses.

No deployment, publication, or environment configuration changes were made.


## Website branding

The visual redesign follows [thebigplan.com](https://thebigplan.com), inspected directly in Chromium:

- Raspberry accent: `#C33067`; warm cream background: `#F7F5ED`; near-black type; aqua illustration/chart accents.
- Original squirrel/wordmark SVG: `https://d19uxpqb6unwnr.cloudfront.net/files/6667596c819c70000803ef05/8lachu0ix-tbp-logo.svg`.
- Original aqua illustration: `https://d19uxpqb6unwnr.cloudfront.net/files/66675d06ab9edf0008915ed5/8lacg52kt-9l9poaior-9l6o0da70-Vector.png`.
- Website typography: Brother XS headings, Sweet Sans Pro interface, Ivy Journal introductory text. Source stylesheet: `https://use.typekit.net/dml8sus.css`. Adobe copyright and font licensing references are retained in the HTML stylesheet.
- Fonts, logo, and illustration are embedded so the downloaded prototype remains self-contained. Production should use the site's licensed font delivery configuration.

Brand changes affect presentation and markup; enrollment calculation rules are unchanged. Rechecked in Chromium: navigation, sample totals, role previews, upload replacement, normalized email matching, employee category filters, CSV downloads, and no horizontal overflow at 390px. The HTML remains a local prototype, not a deployed application.


## Growth and enrollment pace

- **Same-date open enrollment:** the overview now compares cumulative employees and covered lives by `consent_granted_date` through today’s New York calendar day, inclusive. For a November 4, 2026 cutoff it compares November 4, 2025 for the 2026 coverage season against November 4, 2026 for the 2027 coverage season. The cutoff is always today in America/New_York; it is not editable. February 29 maps to February 28 in a non-leap prior year. Dates use their recorded calendar day without shifting timestamps across time zones.
- **Source limitations:** these are retrospective consent-date counts within the qualifying loaded report populations, not historical status snapshots or completed enrollment timestamps. Missing/invalid dates are excluded and their counts shown. If a population has no usable consent dates, the pace result is Unavailable rather than a misleading zero. The prior population is the January 1, 2026 company benchmark (including employees now terminated), and the current population uses the four qualifying statuses.
- **All-in company totals:** a separate table shows last year's January 1 employees/lives, this year's renewal enrollment, this year's new-group enrollment, combined totals, net change, and growth. With filters active the table explicitly represents the selected portfolio.
- **Manager weighting:** the shared denominator includes all managers' started renewal groups, including Unassigned, and remains fixed when filtering managers. A manager starting at 1,000 lives and adding 400 has 40% ordinary growth; one starting at 600 and adding 400 has 66.7%. Both contribute 25% weighted growth against a shared 1,600-life baseline. New groups do not affect ranking. Unassigned groups are not ranked.
- **Opportunity:** for each manager show prior active employees, employees returned in any group, return rate, employees not yet returned, their prior covered lives, and groups not started. Follow-up opens a contact list using the existing role-based export preview. A cross-group move is retained, not churn; no automatic churn declaration happens before the January outcome. Covered lives outstanding are prior-year lives, not guaranteed future enrollment.

Validation: `python prototype/test_metrics.py` from the repository root, with Playwright and Chromium installed. This browser check verifies equal-addition weighting, manager filter denominator stability, return matching across groups, missing-date handling, inclusive and leap-day cutoffs, automatic daily cutoff changes, full-company benchmarks, and responsive layouts. It refreshes the two fictional preview screenshots.


## Employer assignment template and parent accounts

In Administration, download the assignment CSV after loading a baseline report. There is one row per known employer, including new groups from the current report. The columns are `employer_account`, `account_manager`, and `parent_account`. Employer names come from the report and must be preserved exactly. A sample template for the uploaded sample's 465 employers is also supplied as `sample-employer-assignments.csv`; regenerate it through Administration when the finalized baseline arrives.

Fill each location's `parent_account` with the same label (for example, Recover Care), and fill its current `account_manager`. Leave the parent blank for standalone accounts. Upload the completed CSV; it applies managers and hierarchy atomically. Unknown and duplicate employers are rejected without partial changes. Partial imports preserve unlisted accounts. A blank manager clears ownership to Unassigned; a blank parent clears that employer's parent. One parent level is supported. CSV quoting handles commas and quotes in employer names.

The Groups page defaults to parent rollups. Click a parent to see every location, including not-started locations; click a location to open employee follow-up. Use the back-to-parent button to return. An Individual employer groups view and parent filter are available. A parent may span multiple managers; manager filters select only the locations assigned to that manager. Counts sum employee rows once. Parent renewal-growth rates use only started renewal children, while the separate opportunity list keeps all prior active employees. Group classification and the weighted ranking remain at the individual employer level.

The fictional demo includes Evergreen Group (three employers) and Northstar Group (two employers) to demonstrate the hierarchy. No hierarchy is inferred for the actual uploaded sample. In this prototype imports and edits last only for the browser session; the downloaded CSV can be retained and re-uploaded.

## Office TV and enrollment over time

Use **Office TV** in the top toolbar. Choose slides, a 10/15/20/30-second interval, whole-company or dashboard-filtered scope, and optional native fullscreen. The eleven slides cover the 2026 benchmark, 2027 totals, same-date pace, renewal/new groups, manager growth, reenrollment opportunities, home states, carriers, enrollment over time, Fun Facts averages, and plan-tier percentages. Controls support previous/next, pause/play, settings, fullscreen/windowed, and exit. Arrow keys navigate, Space pauses, Escape exits. Each slide labels its data source; the TV displays aggregate information and manager names, not employee contacts. Sample-only mode does not imply current-year results. The slideshow uses the reports loaded in this session; it does not synchronize with another device.

**Enrollment momentum** is now called **Enrollment over time**. Each dated bar represents the full number of qualifying enrolled employees in a complete uploaded report, not that day's new additions. A change from 600 to 650 means 50 net more employees. The card shows actual counts, first/latest dates, and net change from the preceding snapshot. With one snapshot it explicitly says there is not yet a trend. Demo bars are illustrative. The chart always uses whole-company counts and states that dashboard filters do not affect it.

Administration lets you enter the date represented by each current report. Uploading a replacement for the same date replaces that day's point rather than creating duplicates. Snapshot counts and upload times are kept in memory for the session; retained production history still requires a backend.

Additional validation commands: `python prototype/test_tv.py` and `python prototype/test_parent_accounts.py`. TV checks cover all slides at 1920×1080 and 1280×720, automatic rotation, pause/navigation, timer cleanup, native fullscreen/windowed, scopes, and dated snapshot replacement. Hierarchy checks exercise CSV download/import including quoted names, a 27-location rollup with not-started locations, parent→child→employee drill-down, exact employee/life totals, atomic error handling, partial updates, admin-only controls, all 465 sample employers, and the mobile editor.


## Data minimization and Fun Facts

The report parser now constructs records using an explicit allowlist before normalization. The application retains only 16 normalized fields: `group`, `email`, `name`, `phone`, `status`, `lives`, `state`, `carrier`, `effective`, `termination`, `consent`, `erAllowance`, `erApplied`, `fullPremium`, `tier`, and `age`. Full CSV contents are parsed transiently in-browser; only the selected normalized records and aggregate snapshot history are retained by the prototype. No raw report is saved to browser storage or sent to a server. This change does not delete the user's original attachment from the chat/workspace.

SSNs, dependent records/names/identifiers, street addresses, city/ZIP/county, dates of birth, income, citizenship, smoker information, and other unused columns do not enter retained application records. State and numeric age are kept; age is not derived from retained birthdays. Employee names, email and phone remain relevant for the previously requested follow-up lists and exports. The embedded sample is also limited to this same normalized schema. Employer assignment imports retain only their three required template columns.

**Fun Facts** replaces Enrollment Insights in navigation. It includes side-by-side 2026/2027 comparisons for:

- Average monthly employer contribution, defaulting to `ichra_consumed` (applied to premiums), with an allowance-offered switch using `ichra_allotted`.
- Average full monthly plan premium from `full_premium`.
- Plan-tier employee percentages from `level`, including an Unknown category and separate Bronze/Expanded Bronze tiers. Year-over-year share changes use percentage points.
- Average numeric employee age supplied in each report.
- Average application size, defined as covered lives per employee/application (`sum(total_lives_on_plan) / number of applications with valid lives counts`). Each report row is an employee application, and covered lives already include that employee.

2026 facts use the January 1 company benchmark, including employees now terminated. Current facts use the four qualifying statuses. All dashboard filters apply. Each report supplies its own cost and age values; these are not reconstructed historical measurements. Blank/invalid amounts and ages are excluded, while valid zero-dollar values are included. Coverage sub-counts are hidden on the Fun Facts cards; averages still use only available numeric values. Administrators can inspect counts in the stored-field audit. Application-size averages exclude missing or invalid lives counts. Tier percentages retain unknowns in the denominator. No comparable current report means Awaiting report, not fabricated 2027 values.

Existing carrier-retention, carrier-movement, and state breakdowns remain available in a collapsible section on Fun Facts. No additional individual employee fields were added to contact tables or exports.

Validation: `python prototype/test_fun_facts.py` checks source and import schemas, excluded-field sentinels, exact means for each year, zero/missing-value handling, tier shares, contribution-basis selection, state filters, absent current data, and mobile layout. It generates `fun-facts-preview.png` using fictional demo data. Regression checks for metrics, CSV assignments/parent accounts, and TV mode also passed after the parser change.


## Renewal-employer lives and automatic comparison dates

The Account managers page includes a **New lives by renewal employer** table with employer, parent account, current manager, prior active lives, current lives, new-enrollee lives, and net lives gained/lost. New-enrollee lives sum the employee and covered dependents for current applications whose normalized email was absent from that employer's prior active population. Cross-employer moves count as new at the receiving employer, while remaining retained company-wide. Net lives additionally reflect family-size changes and employees not yet returned. Click any employer to open its employee detail.

The leaderboard also shows **Net new lives / renewal employer**: net covered lives gained divided by started renewal employers managed. This lives-based measure stays in lives when the ranking's Employees/Covered lives toggle changes. Not-started employers stay outside this growth calculation and remain visible in the reenrollment opportunity section.

Same-date comparison cutoffs are now always **today in America/New_York**, for both the dashboard and TV mode. Manual date selectors and the hardcoded cutoff were removed. The corresponding prior-year cutoff is the same calendar date last year (February 29 clamps to February 28). An open page checks for date rollover every 30 seconds and when returning to a visible/focused tab. A paused TV slide also refreshes its date and comparison counts on rollover. This advances the cutoff, not the report contents; new enrollment still requires a new complete report upload. The separately entered report snapshot date remains editable because it identifies which day an uploaded report represents.

Validation: `python prototype/test_live_date_and_lives.py` verifies New York midnight (including the UTC day already being different), automatic dashboard/TV rollover, absent manual cutoff controls, new-enrollee versus net lives, covered-family changes, cross-employer retention, per-employer averages, employee drill-down and mobile layout. Updated metric checks also pass with the automatic date policy.

The overview begins with the four renewal/new enrollment summary cards, followed by same-date and full-season comparisons. State labels use State (including the TV slide selector). Fun Facts averages and plan-tier percentages are included in the TV rotation by default and can be independently selected.
