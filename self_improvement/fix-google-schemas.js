
const fs = require('fs');
const path = require('path');

const DIST_DIR = '/opt/homebrew/lib/node_modules/openclaw/dist';
const FILES_TO_PATCH = [
  'pi-embedded-n26FO9Pa.js',
  'pi-embedded-CNutRYOy.js',
  'reply-B1AnbNl6.js',
  'subagent-registry-kdTa9uwX.js',
  'plugin-sdk/reply-BhWxw1_E.js'
];

function patchFile(filename) {
  const filePath = path.join(DIST_DIR, filename);
  if (!fs.existsSync(filePath)) {
    console.log(`Skipping ${filename} (not found)`);
    return;
  }

  console.log(`Patching ${filename}...`);
  let content = fs.readFileSync(filePath, 'utf8');
  let originalContent = content;

  // FIX 1: Convert Type.Union([Type.String(), Type.Array(Type.String())]) to Type.Array(Type.String())
  // This fixes the 'image' tool schema error
  // Regex: image: Type.Union([Type.String(), Type.Array(Type.String())])
  // We need to match the specific pattern used in the minified code
  
  // Pattern 1: image: Type.Union([Type.String(), Type.Array(Type.String())]) - with optional spaces
  content = content.replace(/image:\s*Type\.Union\(\[Type\.String\(\),\s*Type\.Array\(Type\.String\(\)\)\]\)/g, 'image: Type.Array(Type.String())');

  // FIX 2: Convert Type.Optional(Type.Number(...)) to Type.Optional(Type.String())
  // This fixes tools like 'sessions_list', 'browser', etc. which use number constraints (minimum: 1)
  // that are rejected by Google/Anthropic schema validation.
  
  // Pattern 2: Type.Optional(Type.Number()) -> Type.Optional(Type.String())
  content = content.replace(/Type\.Optional\(Type\.Number\(\)\)/g, 'Type.Optional(Type.String())');
  
  // Pattern 3: Type.Optional(Type.Number({ ... })) -> Type.Optional(Type.String())
  // Matches simple object config inside Number(), assuming no nested braces for now (minified code is usually flat)
  content = content.replace(/Type\.Optional\(Type\.Number\({[^}]*}\)\)/g, 'Type.Optional(Type.String())');

  // Verify changes
  if (content !== originalContent) {
    fs.writeFileSync(filePath, content);
    console.log(`✅ Patched ${filename}`);
  } else {
    console.log(`No changes needed for ${filename} (already patched or pattern not found)`);
  }
}

console.log('Starting Google Antigravity Schema Fix...');
FILES_TO_PATCH.forEach(patchFile);
console.log('Patching complete. PLEASE RESTART GATEWAY PROCESS (kill PID if necessary).');
