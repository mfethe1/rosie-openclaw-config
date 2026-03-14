#!/usr/bin/env python3
"""
dependency_analyzer.py — SI Infrastructure Dependency Analyzer

Scans the self_improvement/scripts/ directory (and optionally the broader
workspace) to map:
  1. Python import dependencies (stdlib vs third-party vs local)
  2. Cross-script call references (which scripts invoke which)
  3. Shared resource dependencies (files, DBs, APIs, env vars)
  4. Missing or broken dependencies (importable? binary available?)
  5. Circular dependency detection
  6. Staleness scoring (last modified, dead code candidates)

Outputs:
  - Markdown report (default)
  - JSON graph (--json)
  - Dot/Graphviz (--dot)
  - Store to agent-memory.db (--store)

Usage:
  python3 dependency_analyzer.py                          # full SI scan, markdown
  python3 dependency_analyzer.py --json                   # JSON output
  python3 dependency_analyzer.py --dot                    # Graphviz dot
  python3 dependency_analyzer.py --scope workspace        # scan entire workspace
  python3 dependency_analyzer.py --check                  # verify all deps importable
  python3 dependency_analyzer.py --store                  # store summary in memory DB
"""

import ast
import argparse
import datetime
import importlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
SI_DIR = WORKSPACE / "self_improvement"
SCRIPTS_DIR = SI_DIR / "scripts"
MEMORY_DB = Path.home() / ".openclaw" / "agent-memory.db"

# Standard library modules (Python 3.9+)
STDLIB_MODULES = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
    'cgi', 'cmd', 'codecs', 'collections', 'configparser', 'contextlib',
    'copy', 'csv', 'ctypes', 'dataclasses', 'datetime', 'decimal',
    'difflib', 'dis', 'email', 'enum', 'errno', 'fnmatch', 'fractions',
    'ftplib', 'functools', 'gc', 'getpass', 'glob', 'gzip', 'hashlib',
    'heapq', 'hmac', 'html', 'http', 'imaplib', 'importlib', 'inspect',
    'io', 'itertools', 'json', 'keyword', 'linecache', 'locale',
    'logging', 'lzma', 'math', 'mimetypes', 'multiprocessing', 'operator',
    'os', 'pathlib', 'pickle', 'platform', 'plistlib', 'pprint',
    'profile', 'pstats', 'queue', 're', 'readline', 'reprlib', 'sched',
    'secrets', 'select', 'shelve', 'shlex', 'shutil', 'signal', 'site',
    'smtplib', 'socket', 'sqlite3', 'ssl', 'statistics', 'string',
    'struct', 'subprocess', 'sys', 'syslog', 'tarfile', 'tempfile',
    'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token',
    'tokenize', 'traceback', 'tracemalloc', 'turtle', 'types', 'typing',
    'unicodedata', 'unittest', 'urllib', 'uuid', 'venv', 'warnings',
    'wave', 'weakref', 'webbrowser', 'xml', 'xmlrpc', 'zipfile', 'zipimport',
    'zlib', '_thread', '__future__', 'builtins', 'posixpath', 'ntpath',
    'genericpath', 'stat', 'posix', 'nt', 'random',
}


@dataclass
class ScriptInfo:
    """Metadata about a single script."""
    path: str
    name: str
    size_bytes: int = 0
    lines: int = 0
    last_modified: str = ""
    days_since_modified: float = 0.0
    imports_stdlib: List[str] = field(default_factory=list)
    imports_third_party: List[str] = field(default_factory=list)
    imports_local: List[str] = field(default_factory=list)
    calls_scripts: List[str] = field(default_factory=list)
    shared_resources: List[str] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    has_main: bool = False
    has_argparse: bool = False
    docstring: str = ""
    broken_imports: List[str] = field(default_factory=list)
    staleness: str = "active"  # active / stale / dead


@dataclass
class DependencyGraph:
    """Full dependency analysis result."""
    scripts: Dict[str, ScriptInfo] = field(default_factory=dict)
    cross_refs: List[Tuple[str, str]] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    missing_deps: List[str] = field(default_factory=list)
    shared_files: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    shared_apis: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    shared_envvars: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    scan_time: str = ""
    total_scripts: int = 0
    total_lines: int = 0


def extract_imports(source: str) -> Tuple[List[str], List[str], List[str]]:
    """Parse imports from Python source, categorize as stdlib/third-party/local."""
    stdlib, third_party, local = [], [], []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return stdlib, third_party, local

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split('.')[0]
                _categorize_import(mod, stdlib, third_party, local)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split('.')[0]
                _categorize_import(mod, stdlib, third_party, local)

    return sorted(set(stdlib)), sorted(set(third_party)), sorted(set(local))


def _categorize_import(mod: str, stdlib: list, third_party: list, local: list):
    """Categorize a module name."""
    if mod in STDLIB_MODULES or mod.startswith('_'):
        stdlib.append(mod)
    elif mod in ('schwab', 'sentence_transformers', 'sqlite_vec', 'requests',
                 'flask', 'fastapi', 'uvicorn', 'pydantic', 'numpy', 'pandas',
                 'anthropic', 'openai', 'tiktoken', 'fastembed'):
        third_party.append(mod)
    else:
        # Could be local or third-party — check if it's a local file
        local_path = SCRIPTS_DIR / f"{mod}.py"
        if local_path.exists():
            local.append(mod)
        else:
            third_party.append(mod)


def extract_cross_refs(name: str, source: str, all_script_names: Set[str]) -> List[str]:
    """Find references to other scripts in this source."""
    refs = []
    for other in all_script_names:
        if other == name:
            continue
        # Look for the script name in strings, subprocess calls, etc.
        if other in source:
            refs.append(other)
    return sorted(set(refs))


def extract_shared_resources(source: str) -> Tuple[List[str], List[str], List[str]]:
    """Extract shared files, API endpoints, and env vars referenced."""
    files = []
    apis = []
    envvars = []

    # Shared coordination files
    file_patterns = [
        (r'shared-state\.json', 'shared-state.json'),
        (r'CHANGELOG\.md', 'CHANGELOG.md'),
        (r'TODO\.md', 'TODO.md'),
        (r'MEMORY\.md', 'MEMORY.md'),
        (r'LOOPS\.md', 'LOOPS.md'),
        (r'agent-memory\.db', 'agent-memory.db'),
        (r'eval-log\.md', 'eval-log.md'),
        (r'fail-reflections\.jsonl', 'fail-reflections.jsonl'),
        (r'self-reflect-log\.md', 'self-reflect-log.md'),
        (r'awesome_memory_tracker_state\.json', 'awesome_memory_tracker_state.json'),
        (r'issues\.md', 'issues.md'),
    ]
    for pattern, label in file_patterns:
        if re.search(pattern, source):
            files.append(label)

    # API endpoints
    api_patterns = [
        (r'localhost:12345', 'memU (localhost:12345)'),
        (r'localhost:12345', 'memu-service (localhost:12345)'),
        (r'api\.anthropic\.com', 'Anthropic API'),
        (r'api\.openai\.com', 'OpenAI API'),
        (r'github\.com', 'GitHub'),
        (r'raw\.githubusercontent\.com', 'GitHub Raw'),
    ]
    for pattern, label in api_patterns:
        if re.search(pattern, source):
            apis.append(label)

    # Environment variables
    env_matches = re.findall(r'os\.environ(?:\.get)?\(\s*["\'](\w+)', source)
    env_matches += re.findall(r'os\.getenv\(\s*["\'](\w+)', source)
    env_matches += re.findall(r'\$\{?(\w+)\}?', source)
    # Filter noise
    envvars = sorted(set(e for e in env_matches if len(e) > 2 and e.isupper()))

    return sorted(set(files)), sorted(set(apis)), envvars


def detect_cycles(cross_refs: List[Tuple[str, str]]) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    graph = defaultdict(set)
    for src, dst in cross_refs:
        graph[src].add(dst)

    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def check_import_availability(imports: List[str]) -> List[str]:
    """Check if third-party imports are actually available."""
    broken = []
    for mod in imports:
        try:
            importlib.import_module(mod)
        except ImportError:
            broken.append(mod)
        except (ImportError, RuntimeError, OSError, SystemError):
            pass  # Module exists but has runtime issues
    return broken


def score_staleness(days: float) -> str:
    """Score how stale a script is based on last modification."""
    if days <= 3:
        return "active"
    elif days <= 14:
        return "recent"
    elif days <= 30:
        return "stale"
    else:
        return "dead"


def analyze_scripts(scope: str = "si", check: bool = False) -> DependencyGraph:
    """Main analysis entry point."""
    graph = DependencyGraph()
    graph.scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M EST")

    # Determine scan directory
    if scope == "workspace":
        scan_dirs = [SCRIPTS_DIR, WORKSPACE / "memu_server"]
    else:
        scan_dirs = [SCRIPTS_DIR]

    # Collect all Python files
    py_files = []
    for d in scan_dirs:
        if d.exists():
            py_files.extend(sorted(d.glob("*.py")))

    all_names = {f.stem for f in py_files}
    now = datetime.datetime.now()

    for py_file in py_files:
        name = py_file.stem
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        stat = py_file.stat()
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        days_old = (now - mtime).total_seconds() / 86400

        stdlib, third_party, local = extract_imports(source)
        cross_refs = extract_cross_refs(name, source, all_names)
        shared_files, apis, envvars = extract_shared_resources(source)

        broken = []
        if check:
            broken = check_import_availability(third_party)

        info = ScriptInfo(
            path=str(py_file.relative_to(WORKSPACE)),
            name=name,
            size_bytes=stat.st_size,
            lines=source.count('\n') + 1,
            last_modified=mtime.strftime("%Y-%m-%d %H:%M"),
            days_since_modified=round(days_old, 1),
            imports_stdlib=stdlib,
            imports_third_party=third_party,
            imports_local=local,
            calls_scripts=cross_refs,
            shared_resources=shared_files,
            env_vars=envvars,
            api_endpoints=apis,
            has_main='if __name__' in source,
            has_argparse='argparse' in source,
            docstring=(ast.get_docstring(ast.parse(source)) or "")[:200],
            broken_imports=broken,
            staleness=score_staleness(days_old),
        )

        graph.scripts[name] = info
        graph.total_scripts += 1
        graph.total_lines += info.lines

        # Build cross-ref edges
        for ref in cross_refs:
            graph.cross_refs.append((name, ref))

        # Aggregate shared resources
        for f in shared_files:
            graph.shared_files[f].append(name)
        for a in apis:
            graph.shared_apis[a].append(name)
        for e in envvars:
            graph.shared_envvars[e].append(name)

    # Detect cycles
    graph.cycles = detect_cycles(graph.cross_refs)

    # Collect all broken deps
    for info in graph.scripts.values():
        graph.missing_deps.extend(f"{info.name}→{b}" for b in info.broken_imports)

    return graph


def render_markdown(graph: DependencyGraph) -> str:
    """Render analysis as Markdown report."""
    lines = [
        f"# Dependency Analysis Report",
        f"**Generated:** {graph.scan_time}",
        f"**Scripts scanned:** {graph.total_scripts}",
        f"**Total lines:** {graph.total_lines:,}",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Staleness distribution
    staleness_counts = defaultdict(int)
    for info in graph.scripts.values():
        staleness_counts[info.staleness] += 1
    lines.append("### Staleness")
    for status in ['active', 'recent', 'stale', 'dead']:
        count = staleness_counts.get(status, 0)
        icon = {'active': '🟢', 'recent': '🟡', 'stale': '🟠', 'dead': '🔴'}.get(status, '⚪')
        lines.append(f"- {icon} **{status}**: {count} scripts")
    lines.append("")

    # Third-party dependencies (unified)
    all_third_party = set()
    for info in graph.scripts.values():
        all_third_party.update(info.imports_third_party)
    if all_third_party:
        lines.append("### Third-Party Dependencies")
        for dep in sorted(all_third_party):
            users = [n for n, i in graph.scripts.items() if dep in i.imports_third_party]
            lines.append(f"- `{dep}` — used by: {', '.join(users)}")
        lines.append("")

    # Broken imports
    if graph.missing_deps:
        lines.append("### ⚠️ Broken Imports")
        for dep in graph.missing_deps:
            lines.append(f"- {dep}")
        lines.append("")

    # Circular dependencies
    if graph.cycles:
        lines.append("### 🔄 Circular Dependencies")
        for cycle in graph.cycles:
            lines.append(f"- {' → '.join(cycle)}")
        lines.append("")
    else:
        lines.append("### Circular Dependencies: None detected ✅")
        lines.append("")

    # Shared resources
    lines.append("## Shared Resources")
    lines.append("")

    if graph.shared_files:
        lines.append("### Shared Files")
        for f, users in sorted(graph.shared_files.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{f}** ({len(users)} scripts): {', '.join(sorted(users))}")
        lines.append("")

    if graph.shared_apis:
        lines.append("### External APIs")
        for api, users in sorted(graph.shared_apis.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{api}** ({len(users)} scripts): {', '.join(sorted(users))}")
        lines.append("")

    if graph.shared_envvars:
        lines.append("### Environment Variables")
        relevant_envvars = {k: v for k, v in graph.shared_envvars.items()
                          if len(v) > 1 or k in ('ANTHROPIC_API_KEY', 'GOG_KEYRING_PASSWORD',
                                                   'MEMU_KEY', 'MEMU_URL')}
        for var, users in sorted(relevant_envvars.items(), key=lambda x: -len(x[1])):
            lines.append(f"- `{var}` ({len(users)} scripts): {', '.join(sorted(users))}")
        lines.append("")

    # Cross-reference graph
    lines.append("## Cross-Script References")
    lines.append("")
    if graph.cross_refs:
        # Group by source
        by_source = defaultdict(list)
        for src, dst in graph.cross_refs:
            by_source[src].append(dst)
        for src in sorted(by_source):
            refs = sorted(by_source[src])
            lines.append(f"- **{src}** → {', '.join(refs)}")
    else:
        lines.append("No cross-references detected.")
    lines.append("")

    # Per-script detail
    lines.append("## Script Details")
    lines.append("")
    for name in sorted(graph.scripts):
        info = graph.scripts[name]
        icon = {'active': '🟢', 'recent': '🟡', 'stale': '🟠', 'dead': '🔴'}.get(info.staleness, '⚪')
        lines.append(f"### {icon} {name}")
        lines.append(f"- **Path:** `{info.path}`")
        lines.append(f"- **Lines:** {info.lines:,} | **Size:** {info.size_bytes:,}B | **Modified:** {info.last_modified} ({info.days_since_modified}d ago)")
        if info.docstring:
            lines.append(f"- **Purpose:** {info.docstring[:150]}")
        features = []
        if info.has_main:
            features.append("CLI-runnable")
        if info.has_argparse:
            features.append("argparse")
        if features:
            lines.append(f"- **Features:** {', '.join(features)}")
        if info.imports_third_party:
            lines.append(f"- **Third-party:** {', '.join(info.imports_third_party)}")
        if info.shared_resources:
            lines.append(f"- **Shared files:** {', '.join(info.shared_resources)}")
        if info.api_endpoints:
            lines.append(f"- **APIs:** {', '.join(info.api_endpoints)}")
        if info.broken_imports:
            lines.append(f"- **⚠️ Broken:** {', '.join(info.broken_imports)}")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")

    # Stale scripts
    stale = [n for n, i in graph.scripts.items() if i.staleness in ('stale', 'dead')]
    if stale:
        lines.append(f"1. **Review stale scripts** ({len(stale)}): {', '.join(sorted(stale))}")

    # High fan-in shared resources
    hot_files = [f for f, u in graph.shared_files.items() if len(u) >= 5]
    if hot_files:
        lines.append(f"2. **High-contention files** (≥5 writers): {', '.join(hot_files)} — consider adding atomic write/lock patterns")

    # Missing CLI support
    no_main = [n for n, i in graph.scripts.items() if not i.has_main and i.lines > 50]
    if no_main:
        lines.append(f"3. **No `__main__` guard** ({len(no_main)} scripts ≥50 lines): {', '.join(sorted(no_main))}")

    lines.append("")
    return "\n".join(lines)


def render_json(graph: DependencyGraph) -> str:
    """Render as JSON."""
    data = {
        "scan_time": graph.scan_time,
        "total_scripts": graph.total_scripts,
        "total_lines": graph.total_lines,
        "scripts": {k: asdict(v) for k, v in graph.scripts.items()},
        "cross_refs": graph.cross_refs,
        "cycles": graph.cycles,
        "missing_deps": graph.missing_deps,
        "shared_files": dict(graph.shared_files),
        "shared_apis": dict(graph.shared_apis),
    }
    return json.dumps(data, indent=2)


def render_dot(graph: DependencyGraph) -> str:
    """Render as Graphviz DOT."""
    lines = ['digraph dependencies {', '  rankdir=LR;', '  node [shape=box, fontsize=10];', '']

    # Color nodes by staleness
    colors = {'active': '#90EE90', 'recent': '#FFFACD', 'stale': '#FFD700', 'dead': '#FF6347'}
    for name, info in graph.scripts.items():
        color = colors.get(info.staleness, '#FFFFFF')
        lines.append(f'  "{name}" [style=filled, fillcolor="{color}"];')

    lines.append('')

    # Edges
    for src, dst in graph.cross_refs:
        lines.append(f'  "{src}" -> "{dst}";')

    lines.append('}')
    return '\n'.join(lines)


def store_to_memory(graph: DependencyGraph):
    """Store analysis summary in agent-memory.db."""
    if not MEMORY_DB.exists():
        print(f"[WARN] Memory DB not found: {MEMORY_DB}")
        return

    summary = (
        f"Dependency analysis: {graph.total_scripts} scripts, {graph.total_lines} lines. "
        f"Cross-refs: {len(graph.cross_refs)}. Cycles: {len(graph.cycles)}. "
        f"Broken: {len(graph.missing_deps)}. "
        f"Shared files: {', '.join(sorted(graph.shared_files.keys())[:5])}."
    )

    now = datetime.datetime.now().isoformat()
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.execute(
            """INSERT INTO agent_memories
               (agent, cycle, topic, body, source_file, tags, created_at, memory_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "winnie",
                f"dependency-analysis-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}",
                "dependency-analysis",
                summary,
                "self_improvement/scripts/dependency_analyzer.py",
                "dependency,analysis,infrastructure,winnie",
                now,
                "factual",
            ),
        )
        conn.commit()
        conn.close()
        print(f"[OK] Stored analysis summary in agent-memory.db")
    except (sqlite3.Error, OSError) as e:
        print(f"[WARN] Failed to store in memory DB: {e}")


def main():
    parser = argparse.ArgumentParser(description="Dependency analyzer for SI scripts")
    parser.add_argument("--scope", choices=["si", "workspace"], default="si",
                       help="Scan scope: si (scripts/ only) or workspace (+ memu_server)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dot", action="store_true", help="Graphviz DOT output")
    parser.add_argument("--check", action="store_true",
                       help="Verify third-party imports are available")
    parser.add_argument("--store", action="store_true",
                       help="Store summary in agent-memory.db")
    args = parser.parse_args()

    graph = analyze_scripts(scope=args.scope, check=args.check)

    if args.json:
        print(render_json(graph))
    elif args.dot:
        print(render_dot(graph))
    else:
        print(render_markdown(graph))

    if args.store:
        store_to_memory(graph)


if __name__ == "__main__":
    main()
