# Hummingbot Skills Web App - Design Document

A web application for discovering and installing Hummingbot trading skills, hosted at **skills.hummingbot.org**.

Users install skills using the official [skills.sh](https://skills.sh) CLI:
```bash
npx skills add https://github.com/hummingbot/skills --skill executors
```

## Design Inspiration

Based on [skills.sh](https://skills.sh) - the open agent skills ecosystem.

## Pages

### 1. Homepage (`/`)

The landing page showcasing all Hummingbot skills.

#### Header
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🐦 / Skills                                                          Docs  │
└─────────────────────────────────────────────────────────────────────────────┘
```
- Hummingbot logo (bird icon) links to hummingbot.org
- "Skills" title
- "Docs" link to documentation

#### Hero Section
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ██╗  ██╗██████╗                                                          │
│   ██║  ██║██╔══██╗   Skills are reusable capabilities for AI agents.       │
│   ███████║██████╔╝   Install them with a single command to enhance your    │
│   ██╔══██║██╔══██╗   trading agents with Hummingbot knowledge.             │
│   ██║  ██║██████╔╝                                                         │
│   ╚═╝  ╚═╝╚═════╝                                                          │
│                                                                             │
│   HUMMINGBOT SKILLS                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Install Command + Supported Agents
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INSTALL IN ONE COMMAND                    AVAILABLE FOR THESE AGENTS       │
│  ┌─────────────────────────────────────┐                                    │
│  │ $ npx skills add hummingbot/skills  │   [Claude] [Cursor] [Windsurf]    │
│  └─────────────────────────────────────┘   [Codex] [Goose] [Gemini] [+]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Skills Leaderboard
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SKILLS LEADERBOARD                                                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │ 🔍 Search skills...                                             / │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  [All Time (10)]  [Trending (24h)]  [Hot]                                  │
│                                                                             │
│  #   SKILL                                                    INSTALLS      │
│  ───────────────────────────────────────────────────────────────────────   │
│  1   executors              hummingbot/skills                    2.4K      │
│  2   candles                hummingbot/skills                    1.8K      │
│  3   keys                   hummingbot/skills                    1.2K      │
│  4   setup                  hummingbot/skills                    0.9K      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Skill Detail Page (`/hummingbot/skills/:skillId`)

Individual page for each skill with full documentation.

#### Layout
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🐦 / Skills                                                          Docs  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  skills / hummingbot / skills / executors                                  │
│                                                                             │
│  executors                                            │ WEEKLY INSTALLS     │
│  ┌───────────────────────────────────────────────┐   │ 2.4K                │
│  │ $ npx skills add hummingbot/skills            │   │                     │
│  │   --skill executors                       [📋]│   │ REPOSITORY          │
│  └───────────────────────────────────────────────┘   │ hummingbot/skills   │
│                                                       │                     │
│  📄 SKILL.md                                         │ FIRST SEEN          │
│  ─────────────────────────────────────────────────   │ 3 days ago          │
│                                                       │                     │
│  # Trading Executors                                 │ INSTALLED ON        │
│                                                       │ claude-code   1.2K  │
│  ## Overview                                         │ cursor        0.8K  │
│                                                       │ opencode      0.2K  │
│  Create and manage trading executors for automated   │ gemini-cli    0.1K  │
│  position management. Supports position, grid, DCA,  │ codex         0.1K  │
│  TWAP, and arbitrage executors.                      │                     │
│                                                       │                     │
│  ## Quick Start                                      │                     │
│                                                       │                     │
│  ```bash                                             │                     │
│  # Create a position executor                        │                     │
│  ./scripts/create_position.sh \                      │                     │
│    --connector binance_perpetual \                   │                     │
│    --pair BTC-USDT \                                 │                     │
│    --side LONG \                                     │                     │
│    --amount 100                                      │                     │
│  ```                                                 │                     │
│                                                       │                     │
│  ## Executor Types                                   │                     │
│                                                       │                     │
│  | Type | Description |                              │                     │
│  |------|-------------|                              │                     │
│  | position | Single entry with SL/TP |             │                     │
│  | grid | Grid trading |                            │                     │
│  | dca | Dollar cost averaging |                    │                     │
│  | twap | Time-weighted orders |                    │                     │
│                                                       │                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Components

**Breadcrumb Navigation**
- `skills` → homepage
- `hummingbot` → owner (links to GitHub)
- `skills` → repo name (links to GitHub repo)
- `executors` → current skill

**Install Command Box**
- Copyable command: `npx skills add hummingbot/skills --skill executors`
- Copy button with feedback

**SKILL.md Badge**
- Indicates content source
- Links to raw file on GitHub

**Main Content Area**
- Rendered markdown from SKILL.md
- Syntax highlighting for code blocks
- Table formatting

**Stats Sidebar**
- Weekly Installs: number with K/M suffix
- Repository: owner/repo link
- First Seen: relative time
- Installed On: breakdown by agent with counts

## Data Model

### skills.json
```json
{
  "skills": [
    {
      "id": "executors",
      "name": "hummingbot-executors",
      "description": "Create and manage trading executors (position, grid, DCA, TWAP)",
      "category": "trading",
      "triggers": ["create executor", "position executor", "grid trading", "dca order"],
      "path": "skills/executors",
      "installs": {
        "total": 2400,
        "weekly": 340,
        "by_agent": {
          "claude-code": 1200,
          "cursor": 800,
          "opencode": 200,
          "gemini-cli": 100,
          "codex": 100
        }
      },
      "first_seen": "2026-01-26T00:00:00Z",
      "status": "active"
    }
  ],
  "categories": [
    {"id": "trading", "name": "Trading", "icon": "chart-line"},
    {"id": "configuration", "name": "Configuration", "icon": "settings"},
    {"id": "data", "name": "Data", "icon": "database"},
    {"id": "infrastructure", "name": "Infrastructure", "icon": "server"},
    {"id": "qa", "name": "QA & Testing", "icon": "check-circle"},
    {"id": "bots", "name": "Bots", "icon": "bot"},
    {"id": "frontend", "name": "Frontend", "icon": "layout"}
  ],
  "repo": {
    "owner": "hummingbot",
    "name": "skills",
    "url": "https://github.com/hummingbot/skills"
  }
}
```

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS v4 + HBUI theme
- **Markdown**: next-mdx-remote or react-markdown
- **Analytics**: Vercel Analytics
- **Deployment**: Vercel
- **Testing**: Playwright

## HBUI Theme

```css
:root {
  --hb-bg: #0a0a0a;
  --hb-bg-secondary: #141414;
  --hb-bg-tertiary: #1a1a1a;
  --hb-text: #ffffff;
  --hb-text-secondary: #a0a0a0;
  --hb-text-muted: #666666;
  --hb-accent: #00d395;
  --hb-accent-hover: #00b380;
  --hb-border: #2a2a2a;
  --hb-code-bg: #1e1e1e;
}
```

- Dark background with green accent
- Monospace font for code and numbers
- Terminal-inspired aesthetic
- High contrast for readability

## File Structure

```
webapp/
├── app/
│   ├── layout.tsx                    # Root layout with header
│   ├── page.tsx                      # Homepage with leaderboard
│   ├── globals.css                   # HBUI theme styles
│   ├── [owner]/
│   │   └── [repo]/
│   │       └── [skill]/
│   │           └── page.tsx          # Skill detail page
│   └── api/
│       └── skills/
│           ├── route.ts              # GET all skills
│           └── [id]/
│               ├── route.ts          # GET skill by id
│               └── install/
│                   └── route.ts      # POST track install
├── components/
│   ├── Header.tsx                    # Site header
│   ├── Hero.tsx                      # ASCII art hero
│   ├── InstallCommand.tsx            # Copyable command box
│   ├── AgentIcons.tsx                # Supported agent logos
│   ├── SkillsLeaderboard.tsx         # Main skills list
│   ├── SkillRow.tsx                  # Individual skill row
│   ├── SearchBar.tsx                 # Search input
│   ├── TabFilter.tsx                 # All Time / Trending / Hot
│   ├── Breadcrumb.tsx                # Navigation breadcrumb
│   ├── SkillContent.tsx              # Rendered markdown
│   └── StatsSidebar.tsx              # Install stats sidebar
├── lib/
│   ├── skills.ts                     # Skills data operations
│   ├── markdown.ts                   # Markdown parsing
│   └── format.ts                     # Number formatting (1.2K)
├── public/
│   ├── icons/
│   │   ├── hummingbot.svg
│   │   ├── claude.svg
│   │   ├── cursor.svg
│   │   ├── windsurf.svg
│   │   ├── codex.svg
│   │   ├── goose.svg
│   │   └── gemini.svg
│   └── fonts/
│       └── geist-mono.woff2
├── content/
│   └── skills.json                   # Skills registry
├── tests/
│   └── e2e/
│       ├── homepage.spec.ts
│       ├── skill-page.spec.ts
│       └── search.spec.ts
├── package.json
├── tailwind.config.ts
├── next.config.ts
└── playwright.config.ts
```

## API Routes

### GET /api/skills
List all skills with filtering and sorting.

**Query Parameters:**
- `search` - Search term
- `category` - Filter by category
- `sort` - `installs` | `trending` | `hot`
- `limit` - Results per page (default: 20)
- `offset` - Pagination offset

**Response:**
```json
{
  "skills": [...],
  "total": 10,
  "has_more": false
}
```

### GET /api/skills/[id]
Get single skill with full details.

### POST /api/skills/[id]/install
Track install event (called when command is copied).

**Body:**
```json
{
  "agent": "claude-code"
}
```

## Playwright Tests

```typescript
// tests/e2e/homepage.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('displays hero and leaderboard', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="hero"]')).toBeVisible();
    await expect(page.locator('[data-testid="leaderboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="skill-row"]')).toHaveCount(4);
  });

  test('search filters skills', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="search"]', 'executor');
    await expect(page.locator('[data-testid="skill-row"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="skill-row"]')).toContainText('executors');
  });

  test('copy install command', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto('/');
    await page.click('[data-testid="copy-command"]');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboard).toContain('npx skills add hummingbot/skills');
  });

  test('tab filtering works', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="tab-trending"]');
    await expect(page.locator('[data-testid="tab-trending"]')).toHaveClass(/active/);
  });
});

// tests/e2e/skill-page.spec.ts
test.describe('Skill Detail Page', () => {
  test('displays skill content and stats', async ({ page }) => {
    await page.goto('/hummingbot/skills/executors');
    await expect(page.locator('[data-testid="breadcrumb"]')).toContainText('executors');
    await expect(page.locator('[data-testid="skill-content"]')).toBeVisible();
    await expect(page.locator('[data-testid="stats-sidebar"]')).toBeVisible();
  });

  test('breadcrumb navigation works', async ({ page }) => {
    await page.goto('/hummingbot/skills/executors');
    await page.click('[data-testid="breadcrumb-home"]');
    await expect(page).toHaveURL('/');
  });

  test('copy skill-specific install command', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto('/hummingbot/skills/executors');
    await page.click('[data-testid="copy-command"]');
    const clipboard = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboard).toBe('npx skills add hummingbot/skills --skill executors');
  });
});
```

## Implementation Phases

### Phase 1: Static Site
- [ ] Initialize Next.js 15 with App Router
- [ ] Set up Tailwind v4 with HBUI theme
- [ ] Build Header component
- [ ] Build Hero component with ASCII art
- [ ] Build InstallCommand component
- [ ] Build AgentIcons component
- [ ] Build SkillsLeaderboard component
- [ ] Build SkillRow component
- [ ] Create homepage layout
- [ ] Add search functionality
- [ ] Add tab filtering (All Time/Trending/Hot)

### Phase 2: Skill Pages
- [ ] Build Breadcrumb component
- [ ] Build SkillContent component (markdown renderer)
- [ ] Build StatsSidebar component
- [ ] Create dynamic skill page route
- [ ] Fetch and render SKILL.md content
- [ ] Link skills from leaderboard to detail pages

### Phase 3: Analytics & Polish
- [ ] Set up Vercel Analytics
- [ ] Implement install tracking API
- [ ] Add real install counts
- [ ] Responsive design testing
- [ ] Add Playwright E2E tests
- [ ] Deploy to Vercel
- [ ] Connect skills.hummingbot.org domain

### Phase 4: Dynamic Content
- [ ] Fetch skill metadata from GitHub API
- [ ] Auto-sync SKILL.md content
- [ ] Add "last updated" timestamps
- [ ] Cache invalidation strategy
