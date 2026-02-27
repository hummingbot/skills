#!/usr/bin/env node
/**
 * Updates install counts for hummingbot skills.
 *
 * Since skills.sh uses client-side rendering, automatic scraping is not possible.
 * This script provides instructions for manual updates.
 *
 * Usage: npm run update-installs
 */

const fs = require('fs');
const path = require('path');

const INSTALLS_FILE = path.join(__dirname, '../src/data/installs.json');
const SKILLS_SH_URL = 'https://skills.sh/?q=hummingbot';

// Our skills in hummingbot/skills repo
const OUR_SKILLS = [
  'hummingbot-deploy',
  'lp-agent',
  'connectors-available',
  'slides-generator',
  'find-arbitrage-opps',
  'hummingbot'
];

function main() {
  console.log('=== Hummingbot Skills Install Counter ===\n');

  // Read current values
  let current = {};
  try {
    current = JSON.parse(fs.readFileSync(INSTALLS_FILE, 'utf-8'));
  } catch {
    console.log('No existing installs.json found, will create new file.\n');
  }

  console.log('Current install counts:');
  for (const skill of OUR_SKILLS) {
    console.log(`  ${skill}: ${current[skill] ?? 0}`);
  }

  console.log('\n--- Manual Update Instructions ---\n');
  console.log(`1. Open: ${SKILLS_SH_URL}`);
  console.log('2. Note the INSTALLS count for each hummingbot/skills skill');
  console.log(`3. Edit: ${INSTALLS_FILE}`);
  console.log('4. Update the counts and save\n');

  console.log('Example installs.json format:');
  console.log(JSON.stringify({
    'hummingbot-deploy': 48,
    'lp-agent': 39,
    'connectors-available': 35,
    'slides-generator': 24,
    'find-arbitrage-opps': 0,
    'hummingbot': 0
  }, null, 2));

  console.log('\n');

  // If running with --set, allow setting values from command line
  const args = process.argv.slice(2);
  if (args.includes('--set')) {
    const setIndex = args.indexOf('--set');
    const pairs = args.slice(setIndex + 1);

    if (pairs.length === 0) {
      console.log('Usage: npm run update-installs -- --set skill1=count1 skill2=count2');
      console.log('Example: npm run update-installs -- --set hummingbot-deploy=50 lp-agent=40');
      return;
    }

    for (const pair of pairs) {
      const [skill, count] = pair.split('=');
      if (OUR_SKILLS.includes(skill) && !isNaN(parseInt(count))) {
        current[skill] = parseInt(count);
        console.log(`Set ${skill} = ${count}`);
      } else if (!OUR_SKILLS.includes(skill)) {
        console.log(`Skipping unknown skill: ${skill}`);
      }
    }

    // Ensure all skills have values
    for (const skill of OUR_SKILLS) {
      if (!(skill in current)) {
        current[skill] = 0;
      }
    }

    fs.writeFileSync(INSTALLS_FILE, JSON.stringify(current, null, 2) + '\n');
    console.log(`\nUpdated ${INSTALLS_FILE}`);
  }
}

main();
