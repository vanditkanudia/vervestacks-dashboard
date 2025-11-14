const fs = require('fs');
const path = require('path');

// Determine environment
const nodeEnv = (process.env.NODE_ENV || process.env.REACT_APP_ENV || 'development').trim();

// Load root env file: env/env.{environment}
const rootEnvPath = path.resolve(__dirname, '..', 'env', `env.${nodeEnv}`);
if (!fs.existsSync(rootEnvPath)) {
  console.error(`syncEnvToFrontend: Root env file not found: ${rootEnvPath}`);
  process.exit(1);
}

// Lightweight .env parser (no external dependency)
const fileContent = fs.readFileSync(rootEnvPath, 'utf8');
const parsed = {};
for (const rawLine of fileContent.split(/\r?\n/)) {
  const line = rawLine.trim();
  if (!line || line.startsWith('#')) continue;
  const eq = line.indexOf('=');
  if (eq === -1) continue;
  const key = line.slice(0, eq).trim();
  let value = line.slice(eq + 1).trim();
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith('\'') && value.endsWith('\''))) {
    value = value.slice(1, -1);
  }
  parsed[key] = value;
}

// Validate required backend values from root env (no fallbacks)
const requiredKeys = ['BACKEND_PROTOCOL', 'BACKEND_HOST', 'BACKEND_PORT'];
const missing = requiredKeys.filter((k) => !parsed[k] || parsed[k].toString().trim() === '');
if (missing.length) {
  console.error(`syncEnvToFrontend: Missing required keys in ${rootEnvPath}: ${missing.join(', ')}`);
  process.exit(1);
}

// Derive safe frontend vars
const backendProtocol = parsed.BACKEND_PROTOCOL.trim();
const backendHost = parsed.BACKEND_HOST.trim();
const backendPort = parsed.BACKEND_PORT.toString().trim();

if (!/^\d+$/.test(backendPort)) {
  console.error(`syncEnvToFrontend: BACKEND_PORT must be a number, got: ${backendPort}`);
  process.exit(1);
}
const reactAppApiUrl = `${backendProtocol}://${backendHost}:${backendPort}/api`;
const reactAppEnv = nodeEnv;

const lines = [
  `REACT_APP_API_URL=${reactAppApiUrl}`,
  `REACT_APP_ENV=${reactAppEnv}`,
  ''
].join('\n');

// Write to frontend/.env.local
const frontendEnvPath = path.resolve(__dirname, '..', 'frontend', '.env.local');
fs.writeFileSync(frontendEnvPath, lines, { encoding: 'utf8' });

console.log('✅ syncEnvToFrontend: wrote frontend/.env.local with:');
console.log(lines.replace(/\n/g, '\n'));


