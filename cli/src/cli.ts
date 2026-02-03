#!/usr/bin/env node

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));

function getVersion(): string {
  try {
    const pkgPath = join(__dirname, '..', 'package.json');
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    return pkg.version;
  } catch {
    return '1.0.0';
  }
}

const VERSION = getVersion();
const REPO = 'hummingbot/skills';
const SKILLS_API_URL = 'https://skills.hummingbot.org/api/skills';

// ANSI colors
const RESET = '\x1b[0m';
const BOLD = '\x1b[1m';
const DIM = '\x1b[38;5;102m';
const TEXT = '\x1b[38;5;145m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';

const LOGO_LINES = [
  ' _                               _             _   ',
  '| |__  _   _ _ __ ___  _ __ ___ (_)_ __   __ _| |__   ___  ___ ',
  "| '_ \\| | | | '_ ` _ \\| '_ ` _ \\| | '_ \\ / _` | '_ \\ / _ \\/ __|",
  '| | | | |_| | | | | | | | | | | | | | | | (_| | |_) | (_) \\__ \\',
  '|_| |_|\\__,_|_| |_| |_|_| |_| |_|_|_| |_|\\__, |_.__/ \\___/|___/',
  '                                         |___/                 ',
];

const GRAYS = [
  '\x1b[38;5;250m',
  '\x1b[38;5;248m',
  '\x1b[38;5;245m',
  '\x1b[38;5;243m',
  '\x1b[38;5;240m',
  '\x1b[38;5;238m',
];

interface Skill {
  id: string;
  name: string;
  description: string;
  path: string;
  author?: string;
}

interface SkillsResponse {
  skills: Skill[];
}

function showLogo(): void {
  console.log();
  LOGO_LINES.forEach((line, i) => {
    console.log(`${GRAYS[i % GRAYS.length]}${line}${RESET}`);
  });
}

function showBanner(): void {
  showLogo();
  console.log();
  console.log(`${DIM}AI agent skills for algorithmic trading${RESET}`);
  console.log();
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills add${RESET}        ${DIM}Install skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills list${RESET}       ${DIM}List installed skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills find${RESET}       ${DIM}Search for skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills check${RESET}      ${DIM}Check for updates${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills update${RESET}     ${DIM}Update all skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills remove${RESET}     ${DIM}Remove installed skills${RESET}`
  );
  console.log(
    `  ${DIM}$${RESET} ${TEXT}npx hummingbot-skills create${RESET}     ${DIM}Create a new skill${RESET}`
  );
  console.log();
  console.log(`Discover more at ${TEXT}https://skills.hummingbot.org${RESET}`);
  console.log();
}

function showHelp(): void {
  console.log(`
${BOLD}Usage:${RESET} npx hummingbot-skills <command> [options]

${BOLD}Commands:${RESET}
  add [skills...]      Install skills from hummingbot/skills
  list, ls             List installed skills
  find [query]         Search for skills
  check                Check for available updates
  update               Update all skills to latest
  remove [skills...]   Remove installed skills
  create [name]        Create a new skill

${BOLD}Options:${RESET}
  -a, --agent       Specify agents (claude-code, cursor, etc.)
  -y, --yes         Skip confirmation prompts

${BOLD}Examples:${RESET}
  ${DIM}$${RESET} npx hummingbot-skills add
  ${DIM}$${RESET} npx hummingbot-skills add portfolio candles-feed
  ${DIM}$${RESET} npx hummingbot-skills list
  ${DIM}$${RESET} npx hummingbot-skills find trading
  ${DIM}$${RESET} npx hummingbot-skills check
  ${DIM}$${RESET} npx hummingbot-skills update
  ${DIM}$${RESET} npx hummingbot-skills remove
  ${DIM}$${RESET} npx hummingbot-skills create my-skill

${BOLD}Options:${RESET}
  --help, -h        Show this help message
  --version, -v     Show version number

Discover more at ${TEXT}https://skills.hummingbot.org${RESET}
`);
}

async function fetchSkills(): Promise<Skill[]> {
  try {
    const response = await fetch(SKILLS_API_URL);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = (await response.json()) as SkillsResponse;
    return data.skills;
  } catch {
    console.log(`${DIM}Could not fetch skills from API, using fallback...${RESET}`);
    try {
      const ghResponse = await fetch(
        `https://api.github.com/repos/${REPO}/contents/skills`
      );
      if (!ghResponse.ok) throw new Error('GitHub API error');
      const dirs = (await ghResponse.json()) as Array<{ name: string; type: string }>;
      return dirs
        .filter((d) => d.type === 'dir')
        .map((d) => ({
          id: d.name,
          name: d.name,
          description: '',
          path: `skills/${d.name}`,
        }));
    } catch {
      return [];
    }
  }
}

async function runAvailable(): Promise<void> {
  console.log(`${TEXT}Available Hummingbot Skills:${RESET}`);
  console.log();

  const skills = await fetchSkills();

  if (skills.length === 0) {
    console.log(`${DIM}No skills found.${RESET}`);
    return;
  }

  const maxNameLen = Math.max(...skills.map((s) => s.name.length));

  for (const skill of skills) {
    const name = skill.name.padEnd(maxNameLen + 2);
    const author = skill.author ? `${DIM}by ${skill.author}${RESET}` : '';
    console.log(`  ${GREEN}•${RESET} ${TEXT}${name}${RESET}${skill.description ? ` ${DIM}${skill.description}${RESET}` : ''}`);
    if (author) {
      console.log(`    ${author}`);
    }
  }

  console.log();
  console.log(`${DIM}Install with:${RESET} npx hummingbot-skills add`);
  console.log();
}

async function runFind(args: string[]): Promise<void> {
  const query = args.join(' ').toLowerCase();
  const skills = await fetchSkills();

  if (!query) {
    console.log(`${TEXT}All Hummingbot Skills:${RESET}`);
    console.log();
    for (const skill of skills) {
      console.log(`  ${GREEN}•${RESET} ${TEXT}${skill.name}${RESET}`);
      if (skill.description) {
        console.log(`    ${DIM}${skill.description}${RESET}`);
      }
    }
    console.log();
    return;
  }

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(query) ||
      s.description.toLowerCase().includes(query) ||
      s.id.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    console.log(`${DIM}No skills found matching "${query}"${RESET}`);
    console.log();
    console.log(`${DIM}Available skills:${RESET}`);
    for (const skill of skills) {
      console.log(`  ${TEXT}${skill.name}${RESET}`);
    }
    return;
  }

  console.log(`${TEXT}Skills matching "${query}":${RESET}`);
  console.log();
  for (const skill of filtered) {
    console.log(`  ${GREEN}•${RESET} ${TEXT}${skill.name}${RESET}`);
    if (skill.description) {
      console.log(`    ${DIM}${skill.description}${RESET}`);
    }
  }
  console.log();
  console.log(
    `${DIM}Install with:${RESET} npx hummingbot-skills add ${filtered.map((s) => s.id).join(' ')}`
  );
  console.log();
}

interface CommandOptions {
  agents: string[];
  skills: string[];
  yes: boolean;
}

function parseOptions(args: string[]): CommandOptions {
  const options: CommandOptions = {
    agents: [],
    skills: [],
    yes: false,
  };

  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    if (arg === '-y' || arg === '--yes') {
      options.yes = true;
    } else if (arg === '-a' || arg === '--agent') {
      i++;
      while (i < args.length && !args[i].startsWith('-')) {
        options.agents.push(args[i]);
        i++;
      }
      continue;
    } else if (!arg.startsWith('-')) {
      options.skills.push(arg);
    }
    i++;
  }

  return options;
}

function runSkillsCommand(args: string[]): void {
  const result = spawnSync('npx', ['-y', 'skills', ...args], {
    stdio: 'inherit',
  });

  if (result.status !== 0 && result.status !== null) {
    process.exit(result.status);
  }
}

async function runAdd(options: CommandOptions): Promise<void> {
  const installArgs = ['add', REPO];

  if (options.skills.length > 0) {
    installArgs.push('--skill', ...options.skills);
  }

  if (options.agents.length > 0) {
    installArgs.push('--agent', ...options.agents);
  }

  if (options.yes) {
    installArgs.push('-y');
  }

  runSkillsCommand(installArgs);
}

async function runRemove(options: CommandOptions): Promise<void> {
  const removeArgs = ['remove'];

  if (options.skills.length > 0) {
    removeArgs.push(...options.skills);
  }

  if (options.agents.length > 0) {
    removeArgs.push('--agent', ...options.agents);
  }

  if (options.yes) {
    removeArgs.push('-y');
  }

  runSkillsCommand(removeArgs);
}

async function runList(): Promise<void> {
  runSkillsCommand(['list']);
}

async function runCheck(): Promise<void> {
  runSkillsCommand(['check']);
}

async function runUpdate(): Promise<void> {
  runSkillsCommand(['update']);
}

async function runCreate(args: string[]): Promise<void> {
  runSkillsCommand(['init', ...args]);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    showBanner();
    return;
  }

  const command = args[0];
  const restArgs = args.slice(1);

  switch (command) {
    case 'add':
    case 'install':
    case 'i':
      await runAdd(parseOptions(restArgs));
      break;

    case 'remove':
    case 'rm':
    case 'uninstall':
      await runRemove(parseOptions(restArgs));
      break;

    case 'list':
    case 'ls':
      await runList();
      break;

    case 'available':
      showLogo();
      console.log();
      await runAvailable();
      break;

    case 'find':
    case 'search':
      showLogo();
      console.log();
      await runFind(restArgs);
      break;

    case 'check':
      await runCheck();
      break;

    case 'update':
    case 'upgrade':
      await runUpdate();
      break;

    case 'create':
    case 'init':
    case 'new':
      await runCreate(restArgs);
      break;

    case '--help':
    case '-h':
    case 'help':
      showHelp();
      break;

    case '--version':
    case '-v':
    case 'version':
      console.log(VERSION);
      break;

    default:
      console.log(`Unknown command: ${command}`);
      console.log(`Run ${BOLD}npx hummingbot-skills --help${RESET} for usage.`);
      process.exit(1);
  }
}

main();
