# Skills Discovery Web App - Design Document

A web application for discovering and installing Hummingbot skills, inspired by [skills.sh](https://skills.sh).

## Overview

The webapp provides a searchable directory of Hummingbot skills with install counts, categories, and one-click installation commands. Built with the Hummingbot HBUI theme.

## Target URL

`https://skills.hummingbot.org`

## UI Components

### 1. Header

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Hummingbot Logo]  / Skills                                      Docs  │
└─────────────────────────────────────────────────────────────────────────┘
```

- Hummingbot logo (links to hummingbot.org)
- "Skills" title
- "Docs" link (to documentation)

### 2. Hero Section

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   ███████╗██╗  ██╗██╗██╗     ██╗     ███████╗                          │
│   ██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝                          │
│   ███████╗█████╔╝ ██║██║     ██║     ███████╗                          │
│   ╚════██║██╔═██╗ ██║██║     ██║     ╚════██║                          │
│   ███████║██║  ██╗██║███████╗███████╗███████║                          │
│   ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝                          │
│                                                                         │
│   THE OPEN AGENT SKILLS ECOSYSTEM                                       │
│                                                                         │
│   Skills are reusable capabilities for AI agents.                       │
│   Install them with a single command to enhance your                    │
│   agents with access to procedural knowledge.                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Install Command + Supported Agents

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INSTALL IN ONE COMMAND              AVAILABLE FOR THESE AGENTS         │
│  ┌─────────────────────────────┐                                        │
│  │ $ npx @hummingbot/skills add│ [Copy]   [Claude] [Cursor] [VSCode]   │
│  └─────────────────────────────┘          [Goose] [Gemini] [OpenCode]  │
└─────────────────────────────────────────────────────────────────────────┘
```

- Install command with copy button
- Agent icons showing supported platforms

### 4. Skills Leaderboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SKILLS LEADERBOARD                                                     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🔍 Search skills...                                           / │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [All Time (X)] [Trending (24h)] [Hot] [Categories ▼]                  │
│                                                                         │
│  #   SKILL                                              INSTALLS        │
│  ─────────────────────────────────────────────────────────────────     │
│  1   executors          hummingbot/skills                  12.4K        │
│  2   keys               hummingbot/skills                   8.2K        │
│  3   candles            hummingbot/skills                   6.1K        │
│  4   setup              hummingbot/skills                   5.8K        │
│  5   test-spot          hummingbot/skills                   3.2K        │
│  6   test-perp          hummingbot/skills                   2.9K        │
│  7   test-gateway       hummingbot/skills                   2.1K        │
│  8   create-pmm         hummingbot/skills                   1.8K        │
│  9   hbui-theme         hummingbot/skills                   1.5K        │
│  10  presentation       hummingbot/skills                   1.2K        │
│                                                                         │
│  [Load More]                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Leaderboard Features

- **Search**: Filter skills by name, description, or keywords
- **Tabs**:
  - All Time - total installs
  - Trending (24h) - recent activity
  - Hot - combination of installs + recent growth
- **Categories dropdown**: Filter by category (Trading, QA, Frontend, Bots, etc.)
- **Skill row**: Rank, name, repo owner, install count

### 5. Skill Detail Modal

When clicking a skill:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  executors                                              [X Close]       │
│  hummingbot/skills                                                      │
│                                                                         │
│  Create and manage trading executors (position, grid, DCA, TWAP)       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ $ npx @hummingbot/skills add -s executors                 [Copy]│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Category: Trading                                                      │
│  Installs: 12,432                                                       │
│  Last Updated: 2 days ago                                               │
│                                                                         │
│  TRIGGERS                                                               │
│  • "create executor"                                                    │
│  • "position executor"                                                  │
│  • "grid trading"                                                       │
│  • "dca order"                                                          │
│                                                                         │
│  [View on GitHub] [View SKILL.md]                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Model

### Skill Registry (`skills.json`)

```json
{
  "skills": [
    {
      "id": "executors",
      "name": "hummingbot-executors",
      "description": "Create and manage trading executors",
      "category": "trading",
      "triggers": ["create executor", "position executor", "grid trading"],
      "repo": "hummingbot/skills",
      "path": "skills/executors",
      "installs": 12432,
      "trending_24h": 234,
      "last_updated": "2026-01-27T00:00:00Z"
    }
  ],
  "categories": [
    {"id": "trading", "name": "Trading", "icon": "chart"},
    {"id": "qa", "name": "QA & Testing", "icon": "check"},
    {"id": "frontend", "name": "Frontend", "icon": "layout"},
    {"id": "bots", "name": "Bots", "icon": "bot"},
    {"id": "infrastructure", "name": "Infrastructure", "icon": "server"}
  ]
}
```

### Expected Skills (Future)

| Skill | Category | Description |
|-------|----------|-------------|
| `executors` | Trading | Create trading executors |
| `keys` | Configuration | Manage API credentials |
| `candles` | Data | Market data and indicators |
| `setup` | Infrastructure | Deploy Hummingbot |
| `test-spot` | QA | Test spot connector (keys, prices, candles) |
| `test-perp` | QA | Test perpetual connector |
| `test-gateway` | QA | Test gateway/router connector |
| `create-pmm` | Bots | Create PMM controller |
| `hbui-theme` | Frontend | Hummingbot UI theme |
| `presentation` | Frontend | Create Hummingbot presentations |

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS + HBUI theme
- **State**: React Query for data fetching
- **Testing**: Playwright for E2E tests
- **Deployment**: Vercel

## Theme: HBUI

Use the Hummingbot UI design system:
- Dark background (`#0a0a0a`)
- Accent green (`#00d395`)
- Monospace fonts for code
- Minimal, terminal-inspired aesthetic

## API Endpoints

### `GET /api/skills`

List all skills with optional filtering.

Query params:
- `category`: Filter by category
- `search`: Search term
- `sort`: `installs` | `trending` | `hot`
- `limit`: Number of results
- `offset`: Pagination offset

### `GET /api/skills/:id`

Get skill details.

### `POST /api/skills/:id/install`

Track install (called when user copies command).

## Implementation Phases

### Phase 1: Static Site
- [ ] Next.js app with HBUI theme
- [ ] Static skills data from `skills.json`
- [ ] Search and filter functionality
- [ ] Responsive design

### Phase 2: Analytics
- [ ] Install tracking (anonymous)
- [ ] Trending calculations
- [ ] Category filtering

### Phase 3: Dynamic Content
- [ ] Fetch skill metadata from GitHub repos
- [ ] Auto-update from SKILL.md files
- [ ] Community skill submissions

## File Structure

```
webapp/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Home/leaderboard
│   ├── api/
│   │   └── skills/
│   │       └── route.ts
│   └── [skill]/
│       └── page.tsx          # Skill detail
├── components/
│   ├── Header.tsx
│   ├── Hero.tsx
│   ├── InstallCommand.tsx
│   ├── SkillsLeaderboard.tsx
│   ├── SkillCard.tsx
│   ├── SkillModal.tsx
│   ├── SearchBar.tsx
│   └── AgentIcons.tsx
├── lib/
│   ├── skills.ts             # Data fetching
│   └── analytics.ts          # Install tracking
├── styles/
│   └── hbui.css              # HBUI theme
├── public/
│   └── icons/                # Agent logos
├── tests/
│   └── e2e/
│       ├── home.spec.ts
│       ├── search.spec.ts
│       └── install.spec.ts
├── skills.json               # Static skills data
├── package.json
├── tailwind.config.js
└── playwright.config.ts
```

## Playwright Test Plan

```typescript
// tests/e2e/home.spec.ts
test('homepage loads with skills leaderboard', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('SKILLS');
  await expect(page.locator('[data-testid="skills-list"]')).toBeVisible();
});

test('search filters skills', async ({ page }) => {
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'executor');
  await expect(page.locator('[data-testid="skill-row"]')).toHaveCount(1);
});

test('copy install command', async ({ page }) => {
  await page.goto('/');
  await page.click('[data-testid="copy-button"]');
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboard).toContain('npx @hummingbot/skills add');
});

test('category filter works', async ({ page }) => {
  await page.goto('/');
  await page.click('[data-testid="category-dropdown"]');
  await page.click('text=Trading');
  await expect(page.locator('[data-testid="skill-row"]')).toHaveCount(2);
});
```

## Next Steps

1. **Initialize Next.js app** with HBUI theme
2. **Create static skills.json** with current skills
3. **Build core components** (Header, Hero, Leaderboard)
4. **Add Playwright tests**
5. **Deploy to Vercel**
6. **Connect domain** (skills.hummingbot.org)
