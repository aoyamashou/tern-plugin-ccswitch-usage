# Tern CC Switch Usage Plugin

**English** | [简体中文](README_ZH.md)

Show usage for the **current provider** in each CC Switch app in Tern's status bar. Click a status segment, or run **打开 CC Switch 额度** (Open CC Switch Quotas) from the command palette, to open a native detail pane with all plans and a Refresh button. The plugin queries every five minutes. If it cannot read the database, it keeps the last loaded results and shows an error.

## Requirements

- Tern with window plugin support
- CC Switch data on the same computer as the Tern window
- Python 3 and Node.js available in Tern's `PATH`

The plugin opens `~/.cc-switch/cc-switch.db` in read-only mode. If CC Switch uses a custom configuration directory, set `CC_SWITCH_CONFIG_DIR` in Tern's environment to that directory. The plugin does not change CC Switch data.

## Install

```sh
tern plugin link /path/to/tern-plugin-ccswitch-usage
tern plugin list
```

Enable the usage query for a provider in CC Switch to display it in Tern. If the status segment is not visible, enable Tern's status bar.

## Supported queries

The plugin runs saved **General**, **New API**, and **Custom JavaScript** usage scripts for current providers. It displays up to three providers in the status bar and all queried providers in the detail pane.

CC Switch handles `official_subscription`, `token_plan`, `balance`, and `github_copilot` through app-internal queries. CC Switch does not expose those results through a local API, so this plugin shows an explanation for those query types instead of an allowance. It does not query providers that are not current.

Enabled scripts run locally and send requests to their configured usage endpoints. Only enable scripts from sources you trust. The plugin does not print or save API keys.
