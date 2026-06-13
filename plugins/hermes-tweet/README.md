# Hermes Tweet Plugin

Hermes Tweet is a native Hermes Agent plugin for safe X/Twitter research,
analysis, and explicitly gated action workflows through Xquik.

## Install

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Hermes prompts for `XQUIK_API_KEY` during interactive install. For
non-interactive installs, set `XQUIK_API_KEY` in the process environment or
`~/.hermes/.env` before running read tools.

## Capabilities

- Search tweets, profiles, timelines, and tweet context.
- Use read-first workflows for research and monitoring.
- Keep write actions disabled unless `HERMES_TWEET_ENABLE_ACTIONS=true`.
- Review the upstream guide before production use:
  <https://github.com/Xquik-dev/hermes-tweet#readme>.
