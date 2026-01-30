# MCP Server Integration for Skills

Skills can reference MCP (Model Context Protocol) server tools to provide Claude with direct API access. This document explains the integration pattern used by the Notion skills and how to apply it to Hummingbot.

## How Skills Use MCP Servers

Skills are **instructions** that tell Claude how to use available tools. They don't implement the tools themselves.

### Pattern

```markdown
# My Skill

When asked to do something:

1. **Step 1**: Use `ServerName:tool-name` to search
2. **Step 2**: Use `ServerName:another-tool` to fetch details
3. **Step 3**: Use `ServerName:create-tool` to create items
```

### Example from Notion Skills

The notion-spec-to-implementation skill references:
- `Notion:notion-search` - Search for pages
- `Notion:notion-fetch` - Read page content
- `Notion:notion-create-pages` - Create new pages
- `Notion:notion-update-page` - Update existing pages

## Hummingbot MCP Integration

If a Hummingbot MCP server is installed, skills can reference its tools directly.

### Potential Hummingbot MCP Tools

Based on the API endpoints, a Hummingbot MCP server might expose:

**Account/Credentials**
- `Hummingbot:list-connectors` - List available exchanges
- `Hummingbot:list-accounts` - List trading accounts
- `Hummingbot:add-credentials` - Add exchange credentials
- `Hummingbot:get-connector-config` - Get required credential fields

**Executors**
- `Hummingbot:list-executor-types` - Available executor types
- `Hummingbot:get-executor-schema` - Get config schema for executor type
- `Hummingbot:create-executor` - Create a new executor
- `Hummingbot:list-executors` - List/search executors
- `Hummingbot:stop-executor` - Stop an executor
- `Hummingbot:get-executor` - Get executor details

**Market Data**
- `Hummingbot:get-candles` - Fetch OHLCV data
- `Hummingbot:get-prices` - Current prices
- `Hummingbot:list-candle-connectors` - Connectors supporting candles

### Example Skill with MCP

```markdown
---
name: executor-creator
description: Create trading executors via Hummingbot
---

# Executor Creator

## Quick Start

When asked to create a trading position:

1. **List executor types**: Use `Hummingbot:list-executor-types`
2. **Get schema**: Use `Hummingbot:get-executor-schema` with type
3. **Create executor**: Use `Hummingbot:create-executor` with config
4. **Verify**: Use `Hummingbot:get-executor` to confirm

## Without MCP Server

If MCP is not available, fall back to bash scripts:

```bash
./scripts/list_executor_types.sh
./scripts/get_executor_schema.sh --type position_executor
./scripts/create_executor.sh --config '{...}'
```
```

## Dual-Mode Skills

Skills can support both MCP and script-based workflows:

1. **Primary**: Reference MCP tools if available
2. **Fallback**: Provide bash script commands

This allows skills to work whether or not the MCP server is installed.

## MCP Server Configuration

Users install the MCP server separately:

**Via Claude Code Plugin**
```
/plugin install hummingbot-mcp@some-marketplace
```

**Via MCP Settings** (in `.claude/settings.json`)
```json
{
  "mcpServers": {
    "hummingbot": {
      "command": "npx",
      "args": ["-y", "@hummingbot/mcp-server"],
      "env": {
        "API_URL": "http://localhost:8000",
        "API_USER": "admin",
        "API_PASS": "admin"
      }
    }
  }
}
```

## Reference Skills

See `reference/notion-skills/` for examples of how Notion skills reference MCP tools:

- `notion-spec-to-implementation/` - Complex workflow with search, fetch, create
- `notion-knowledge-capture/` - Content extraction and page creation
- `notion-research-documentation/` - Multi-page research synthesis
- `notion-meeting-intelligence/` - Meeting prep with multiple document types

These demonstrate best practices for skill documentation that leverages MCP servers.
