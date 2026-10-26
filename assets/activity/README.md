# Contribution artwork

The skyline uses the account's anonymously visible GitHub contribution calendar. Each building represents one active day, and its height is proportional to that day's contribution count. Blue and gold follow the portfolio palette.

The image refreshes daily at 5:23 a.m. in America/Chicago through the last completed UTC day. The source range, retrieval time, source URLs, and all 168 day counts are preserved in calendar.json. GitHub contribution dates use UTC.

The [refresh workflow](https://github.com/pokharelsandeep333-commits/pokharelsandeep333-commits/actions/workflows/refresh-activity.yml) also supports **Run workflow** on main. It validates the generator before fetching the public calendar and commits only README.md, calendar.json, and the four skyline images when those files change. Identical data preserves its original retrieval timestamp, so repeated runs do not create empty update commits.

From the repository root, refresh to an explicit calendar date:

    python "scripts/update-activity-art.py" --through "2026-10-25"

Rebuild the existing snapshot without a network request:

    python "scripts/update-activity-art.py" --through "2026-10-25" --from-cache

The generator uses only Python's standard library and anonymous public HTTPS requests. No personal access token or custom secret is needed. The publishing job uses GitHub's built-in token with contents write permission; pull-request validation has read-only permissions and no persisted checkout credentials. Official Actions are pinned to full commit SHAs, and generated updates never force-push.

Missing calendar days, invalid cached records, or changed tooltip formats stop generation rather than inventing data. The README caption and all artwork are validated before files are replaced. GitHub may delay scheduled runs; its normal inactivity rules for public repository schedules also apply.

Run the regression suite from the repository root:

    python -m unittest discover -s "scripts/tests" -p "test_*.py" -v

The layout takes inspiration from contribution-based profile artwork such as [Platane's README](https://github.com/Platane/Platane). The skyline renderer and visual design are original.
