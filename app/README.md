# Hummingbot Skills Webapp

Next.js webapp for browsing and discovering Hummingbot skills.

**Live site:** [skills.hummingbot.org](https://skills.hummingbot.org)

## Features

- Browse all available Hummingbot skills
- View skill details and documentation
- Dark/light mode support
- API endpoint for skills CLI integration

## Development

```bash
cd app
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Tech Stack

- [Next.js 16](https://nextjs.org/) with App Router
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/) components
- [next-themes](https://github.com/pacocoursey/next-themes) for dark mode

## API Endpoints

### GET /api/skills

Returns all skills with metadata. Used by the skills CLI.

```json
{
  "repo": {
    "owner": "hummingbot",
    "name": "skills",
    "url": "https://github.com/hummingbot/skills"
  },
  "skills": [
    {
      "id": "hummingbot-deploy",
      "name": "hummingbot-deploy",
      "description": "Deploy Hummingbot trading infrastructure...",
      "path": "skills/hummingbot-deploy",
      "author": "hummingbot"
    }
  ]
}
```

## Deployment

The webapp is deployed on Vercel.

### Automatic Deploys

Connected to GitHub via Vercel integration:
- Push to `main` → deploys to production
- Open PR → creates preview deployment

### Manual Deploy

```bash
cd app
vercel --prod
```

### Environment Variables

None required. The app reads skill data from local `skills/` directory at build time.

## Project Structure

```
app/
├── src/
│   ├── app/              # Next.js App Router pages
│   │   ├── page.tsx      # Home page (skill list)
│   │   ├── skill/[id]/   # Skill detail pages
│   │   └── api/skills/   # API endpoint
│   ├── components/       # React components
│   │   └── ui/           # shadcn/ui components
│   └── lib/
│       ├── skills.ts     # Skill data fetching
│       └── types.ts      # TypeScript types
├── public/               # Static assets
├── tailwind.config.ts
└── package.json
```

## Links

- [Main Repository](https://github.com/hummingbot/skills)
- [Vercel Dashboard](https://vercel.com/hummingbot/skills)
