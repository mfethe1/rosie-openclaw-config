# memU Multi-Gateway + Web Dashboard — 25-Round Build Plan

**Mission:** Make memU work across ALL gateways/agents with a unified web dashboard accessible over Tailscale.

**Network:**
- Harrison's Mac Mini: `100.72.176.67` (Rosie's host — memU server origin)
- Winnie's Windows PC: `100.99.101.117` (desktop-pbe7j2v)
- iPhone: `100.121.75.59`
- Lenovo: `100.76.63.58`
- Michael's Mac Mini: `100.66.54.22`

**Current State:**
- memU server running on `100.72.176.67:12345` (Harrison's Mac Mini)
- LaunchAgent auto-start configured
- Store/search endpoints working
- No web UI, no multi-gateway support, no cross-machine federation

---

## PHASE 1: Core Server Hardening (Rounds 1-5)

### Round 1 — Rosie: Multi-gateway registration + gateway ID tracking
- Add `POST /register-gateway` endpoint
- Each gateway registers with ID, hostname, Tailscale IP, agent list
- Track gateway heartbeats with last-seen timestamps
- Add `GET /gateways` to list all registered gateways

### Round 2 — Mack: Persistent storage upgrade (SQLite fallback)
- Replace JSON file store with SQLite for concurrent access safety
- Migrate existing store.json data
- Add proper indexing for agent/category/key queries
- Add `DELETE /store/{id}` endpoint

### Round 3 — Winnie: Cross-gateway sync protocol
- Design federation: each gateway's agent writes to central memU
- Add gateway_id field to all store entries
- Add `POST /sync` for batch import from remote gateways
- Test cross-machine store/search

### Round 4 — Lenny: Error handling + resilience
- Add request validation, rate limiting, graceful degradation
- Add retry logic for store writes
- Add backup/export endpoint (`GET /export`)
- Stress test concurrent reads/writes

### Round 5 — Rosie: Authentication + Tailscale ACL
- Add API key auth (Bearer token)
- Generate per-gateway API keys
- Restrict to Tailscale CIDR (100.x.x.x)
- Add audit log for all write operations

## PHASE 2: Web Dashboard (Rounds 6-12)

### Round 6 — Mack: Dashboard skeleton (HTML/CSS/JS)
- Single-page app with Tailwind CSS
- Sections: Overview, Memories, Gateways, Agents, Search
- Dark mode (matches existing status-board aesthetic)
- Serve from memU server on `/dashboard`

### Round 7 — Winnie: Real-time gateway status panel
- Show all registered gateways with heartbeat status
- Green/yellow/red indicators for health
- Agent list per gateway
- Auto-refresh every 30s

### Round 8 — Rosie: Memory browser + search UI
- Full-text search with filters (agent, category, date range)
- Memory timeline view
- Expandable cards for memory details
- Pagination

### Round 9 — Lenny: Agent activity feed
- Live feed of store/search operations
- Per-agent activity graphs (last 24h)
- Handoff chain visualization
- Alert on missed handoffs (>3h gap)

### Round 10 — Mack: Memory analytics
- Total memories per agent/category over time
- Store/search ratio per agent
- Most active categories
- Data size tracking

### Round 11 — Winnie: Gateway management UI
- Register new gateways from dashboard
- Edit/deactivate gateways
- View gateway-specific memories
- Network topology diagram

### Round 12 — Rosie: Polish + mobile responsive
- Responsive layout for iPhone access (100.121.75.59)
- Touch-friendly controls
- Loading states, error handling
- Favicon, branding

## PHASE 3: Integration & Testing (Rounds 13-18)

### Round 13 — Lenny: Agent SDK / helper script
- Create `memu-client.sh` helper for curl commands
- Create `memu-client.py` for Python integration
- Auto-detect gateway ID from hostname
- Include in agent startup scripts

### Round 14 — Mack: OpenClaw skill for memU
- Build proper OpenClaw skill (SKILL.md + scripts)
- `memu store`, `memu search`, `memu status` commands
- Auto-register gateway on first use
- Include in each agent's available skills

### Round 15 — Winnie: Deploy to Winnie's machine
- Install memU client on `100.99.101.117`
- Configure Winnie's gateway to register with central server
- Verify cross-machine store/search
- Test from Windows environment

### Round 16 — Rosie: Deploy to Michael's Mac Mini
- Install memU client on `100.66.54.22`
- Configure gateway registration
- Verify full mesh: Harrison ↔ Winnie ↔ Michael

### Round 17 — Lenny: End-to-end integration test
- Simulate full agent cycle across all gateways
- Store from Mack → Search from Rosie → Verify from Lenny
- Measure latency across Tailscale
- Document results

### Round 18 — All: Bug bash + fix round
- Each agent reviews and reports issues
- Priority fix cycle
- Performance optimization

## PHASE 4: Advanced Features (Rounds 19-23)

### Round 19 — Mack: WebSocket live updates
- Add WebSocket endpoint for real-time dashboard updates
- Push new memories to connected dashboards instantly
- Connection status indicator

### Round 20 — Winnie: Memory categories + auto-tagging
- Auto-categorize memories based on content
- Suggested tags on store
- Category-based views in dashboard

### Round 21 — Rosie: Notification system
- Alert when specific agents haven't stored in >3h
- Telegram notification on critical handoff gaps
- Dashboard notification bell

### Round 22 — Lenny: Backup + disaster recovery
- Automated daily backup to EDrive
- Point-in-time restore capability
- Export/import for migration

### Round 23 — Mack: Performance + caching
- Add Redis-like in-memory cache
- Query result caching
- Optimize search for large datasets

## PHASE 5: Documentation & Handoff (Rounds 24-25)

### Round 24 — Winnie: Full documentation
- Architecture diagram
- API reference
- Deployment guide per platform
- Troubleshooting guide

### Round 25 — Rosie: Final review + launch
- Full system verification across all gateways
- Dashboard demo walkthrough
- Update AGENTS.md with memU requirements
- Announce to team as production-ready

---

## Assignment Rotation
Rounds cycle: Rosie → Mack → Winnie → Lenny → repeat
Each round = 1 subagent session, focused on that deliverable.
