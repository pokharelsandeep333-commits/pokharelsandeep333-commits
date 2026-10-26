# Contribution artwork

The skyline uses the account's anonymously visible GitHub contribution calendar. Each building represents one active day, and its height is proportional to that day's contribution count. Blue and gold follow the portfolio palette.

The image is a dated snapshot. It does not update automatically. The source range, retrieval time, source URLs, and all 168 day counts are preserved in calendar.json. GitHub contribution dates use UTC.

From the repository root, refresh to an explicit calendar date:

    python "scripts/update-activity-art.py" --through "2026-10-25"

Rebuild the existing snapshot without a network request:

    python "scripts/update-activity-art.py" --through "2026-10-25" --from-cache

The script uses only Python's standard library and public HTTPS requests. It uses no credentials, GitHub token, workflow, or scheduled job. Missing calendar days or changed tooltip formats stop generation rather than inventing data.

The layout takes inspiration from contribution-based profile artwork such as [Platane's README](https://github.com/Platane/Platane). The skyline renderer and visual design are original.
