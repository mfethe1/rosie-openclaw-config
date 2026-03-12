# memU-Proof Gate Protocol

## 1. Requirement
Every task completion MUST be accompanied by proof of memU usage.

## 2. Definition of Proof
- A `memU` record ID for the task's outcome, context, or learned patterns.
- A summary of what was written to `memU`.

## 3. Mandatory Steps
- On task start: Read relevant context from `memU` via API/MCP tool.
- During execution: Store key decisions, tool results, and novel findings to `memU`. Ensure all written memories include a `relationships` array to establish Graph-Lite entity/relationship tags. This array is REQUIRED for valid memU entries.
- On task completion: Write the final state and any reusable insights to `memU`.

## 4. Deprecation Notice
Local `memory/` files are deprecated for writing. Read them only for historical context.
All new memories MUST be stored in `memU`.
