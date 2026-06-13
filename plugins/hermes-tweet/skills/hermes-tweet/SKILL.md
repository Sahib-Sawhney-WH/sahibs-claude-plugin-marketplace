---
description: Guide Hermes Agent users through safe Hermes Tweet X/Twitter research and opt-in action workflows.
---

# Hermes Tweet

Use this skill when a user wants Hermes Agent support for X/Twitter research,
social listening, tweet analysis, profile context, timeline review, or
approval-gated X/Twitter actions through Hermes Tweet.

## Workflow

1. Confirm the user wants the Hermes Agent plugin, not a generic social media
   API wrapper.
2. Point installation to the upstream plugin:
   `hermes plugins install Xquik-dev/hermes-tweet --enable`.
3. Tell the user to set `XQUIK_API_KEY` through Hermes' interactive prompt, the
   process environment, or `~/.hermes/.env`. Never ask them to paste secrets
   into chat.
4. Prefer read-first tasks such as search, profile context, timeline review, and
   tweet analysis.
5. Treat write actions as opt-in only. They require
   `HERMES_TWEET_ENABLE_ACTIONS=true` in addition to `XQUIK_API_KEY`.
6. Use the upstream guide for current install and safety details:
   <https://github.com/Xquik-dev/hermes-tweet#readme>.
