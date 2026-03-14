# PM Framework Live Test — BuildBid H8
**Granular 3D Lot Models — Persistence Layer**

| Field | Value |
|-------|-------|
| Test ID | `live-test-buildbid-h8-2026-03-02` |
| Date | 2026-03-02 |
| Timestamp | 2026-03-02 21:45 |
| Personas run | pm, red, blue, qa, tech_lead, ux_designer, cpo |
| API provider | openrouter |
| Model | `anthropic/claude-haiku-4-5` |
| Total output | 36,063 chars |
| Errors | 0 |
| Mode | 🟢 LIVE |

---

## Feature Context

## Feature: H8 — Granular 3D Lot Models (Persistence Layer)

**Summary:** BuildBid currently generates 3D lot model visualizations for construction site estimates
but loses all model data on session end. H8 adds full persistence: database storage, versioning,
and retrieval for granular 3D lot model data.

**Scope:**
- PostgreSQL schema for lot_models table (JSONB for geometry, versioning, tenant isolation)
- FastAPI endpoints: POST /lots, GET /lots/{id}, PUT /lots/{id}, GET /lots/{project_id}
- Soft-delete and version history (keep last 10 versions per lot)
- Signed URL generation for large geometry blobs (>5MB fallback to S3)
- Frontend: auto-save on model mutation (debounced 2s), load on session restore
- Multi-tenant: row-level security via PostgreSQL RLS

**Known constraints:**
- Multi-user collaboration on same lot not yet supported (deferred to H9)
- Mobile-responsive UI is a dependency (partial, H7 in parallel)
- Material pricing not yet live (separate stream)
- 3 pilot customers expect this in the next sprint

**Success criteria:**
- Lot model persists across browser refreshes and login sessions
- Load time <2s for lots with <10,000 geometry nodes
- Zero data loss on concurrent save attempts (last-write-wins for now)
- RLS verified: Tenant A cannot access Tenant B's lots


---

## Project Manager

# BuildBid H8 Feature Review & Sprint Plan
## Granular 3D Lot Models (Persistence Layer)

---

## EXECUTIVE SUMMARY

**Status:** ✅ **APPROVED WITH MODIFICATIONS**

**Recommendation:** Proceed with sprint planning. Feature is well-scoped but requires:
1. **Immediate clarification** on concurrent write conflict resolution (last-write-wins is risky)
2. **Dependency sequencing** with H7 (mobile UI) and H9 (collaboration)
3. **Risk mitigation** for S3 fallback and RLS testing before pilot rollout

**Pilot Readiness:** 70% — feasible in 1 sprint with focused scope, but recommend staged rollout (1 pilot → 3 pilots).

---

## FEATURE ANALYSIS

### Strengths
| Aspect | Assessment |
|--------|-----------|
| **Scope Clarity** | Well-defined: schema, endpoints, versioning, multi-tenancy |
| **Success Metrics** | Quantifiable (load time, data loss, RLS verification) |
| **Constraint Awareness** | Explicitly defers collaboration (H9), acknowledges mobile dependency |
| **Business Value** | Solves critical pain point (data loss); unblocks 3 pilot customers |

### Concerns & Gaps

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| **C1** | Last-write-wins conflict resolution is unsafe for concurrent edits | **HIGH** | Data loss risk; pilot customers may have simultaneous users |
| **C2** | No mention of geometry validation (invalid JSON, oversized blobs) | **MEDIUM** | Could corrupt database or cause API crashes |
| **C3** | Version history limit (10 versions) lacks business justification | **MEDIUM** | May be insufficient for audit/compliance; storage cost unclear |
| **C4** | S3 fallback strategy undefined (when triggered? cost? latency?) | **MEDIUM** | Could impact load time SLA; no cost model |
| **C5** | RLS testing scope not detailed (who tests? what scenarios?) | **MEDIUM** | Multi-tenant security is non-negotiable; needs explicit test plan |
| **C6** | Auto-save debounce (2s) may cause UX friction on slow networks | **LOW** | Acceptable but should be configurable/monitored |

---

## SPRINT PLAN

### Sprint Duration
**2 weeks (10 working days)** — Aggressive but achievable with focused team.

### Team Composition (Recommended)
- **Backend Lead** (1 FTE): Schema, RLS, versioning logic
- **Backend Dev** (1 FTE): FastAPI endpoints, S3 integration
- **Frontend Dev** (1 FTE): Auto-save, session restore, error handling
- **QA/Security** (0.5 FTE): RLS testing, concurrent write testing, load testing
- **PM** (0.25 FTE): Pilot coordination, dependency management

---

## USER STORIES

### Story 1: Database Schema & Multi-Tenant Foundation
**ID:** H8-US-001  
**Title:** Create PostgreSQL schema for lot model persistence with RLS

```markdown
### As a
Backend engineer

### I want to
Define the lot_models table with JSONB geometry storage, versioning, 
and row-level security policies

### So that
Lot data persists securely across sessions and is isolated by tenant

### Acceptance Criteria
- [ ] lot_models table created with columns:
  - id (UUID, PK)
  - project_id (UUID, FK → projects)
  - tenant_id (UUID, FK → tenants, indexed)
  - geometry (JSONB, not null)
  - metadata (JSONB: created_by, created_at, updated_at, node_count)
  - version (INT, default 1)
  - is_deleted (BOOLEAN, default false, soft-delete)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
  - s3_url (VARCHAR, nullable, for large blobs >5MB)

- [ ] Indexes created:
  - (tenant_id, project_id) for query performance
  - (tenant_id, is_deleted) for soft-delete queries

- [ ] PostgreSQL RLS enabled:
  - Policy: Users can only SELECT/UPDATE/DELETE rows where tenant_id = current_tenant_id
  - Policy: INSERT requires tenant_id = current_tenant_id
  - Verified with test queries from two separate tenants

- [ ] Versioning table (lot_model_versions):
  - id (UUID, PK)
  - lot_model_id (FK)
  - version_number (INT)
  - geometry (JSONB)
  - changed_by (UUID)
  - changed_at (TIMESTAMP)
  - Retention: Keep last 10 versions; older versions soft-deleted

- [ ] Migration script is idempotent and reversible
- [ ] Schema documented in README with ER diagram

### Definition of Done
- Code reviewed by 2 backend engineers
- RLS policies tested with pytest fixtures (2 tenants, 3 users)
- Migration runs successfully on staging DB
- No performance regression on existing queries (explain plan reviewed)

### Effort Estimate
**M (Medium)** — 3-4 days
- Schema design: 0.5 days
- RLS policy implementation: 1 day
- Versioning table & logic: 1 day
- Testing & documentation: 1-1.5 days

### Dependencies
- PostgreSQL 12+ (assumed available)
- Alembic migration tool (assumed configured)

### Risks
- RLS policy misconfiguration → data leakage (mitigate: peer review + automated tests)
- Version history bloat → storage costs (mitigate: monitor with metrics)
```

---

### Story 2: Core CRUD Endpoints
**ID:** H8-US-002  
**Title:** Implement FastAPI endpoints for lot model persistence

```markdown
### As a
Frontend developer

### I want to
Call REST endpoints to create, retrieve, update, and list lot models

### So that
3D lot data can be saved and restored without manual database queries

### Acceptance Criteria
- [ ] POST /api/v1/lots

---

## Red Team Critic

# RED TEAM CRITIQUE: BuildBid H8 Sprint Plan
## Granular 3D Lot Models (Persistence Layer)

---

## EXECUTIVE FAILURE SUMMARY

This sprint plan is **dangerously incomplete**. The PM has identified some concerns but then **approved it anyway** with a false 70% confidence rating. The plan will fail pilot rollout. Specific failures below.

---

## CRITICAL FAILURES (P0 — BLOCKING)

### P0-1: Last-Write-Wins is a Data Loss Timebomb
**Severity:** P0 | **Likelihood:** HIGH | **Impact:** CATASTROPHIC

**The Problem:**
- Plan acknowledges "last-write-wins for now" as temporary.
- No implementation plan exists for when/how to fix this.
- Pilot customers are 3 construction firms. Construction sites have **multiple stakeholders editing simultaneously**: site managers, estimators, engineers, inspectors.
- Two users open lot model. User A modifies geometry (adds 50 nodes). User B modifies metadata (changes material type). User B saves at 14:32:01. User A saves at 14:32:02. **User B's entire edit is lost.**

**Why This Breaks:**
- No conflict detection mechanism in the plan.
- No version comparison logic.
- No client-side optimistic locking or server-side concurrency tokens.
- The `updated_at` timestamp alone is insufficient; you need **version numbers or ETags**.
- Construction estimates have **legal/contractual weight**. Data loss = liability.

**What's Missing:**
- Concurrent write test suite (none mentioned).
- Conflict resolution strategy (deferred to H9 is unacceptable; H8 should at least prevent silent loss).
- Client-side version tracking (frontend story doesn't mention sending/validating version on PUT).
- Retry logic with exponential backoff (frontend auto-save will retry blindly).

**Failure Mode:**
Pilot customer A reports: *"We lost $2M estimate revision when two team members edited simultaneously. Your product corrupted our data."* Pilot fails. Reputation damage.

**Mitigation (Required Before Sprint):**
- Implement **optimistic locking** with version number in PUT request:
  ```sql
  UPDATE lot_models 
  SET geometry = $1, version = version + 1, updated_at = NOW()
  WHERE id = $2 AND version = $3 AND tenant_id = $4
  RETURNING *;
  ```
- If `UPDATE` returns 0 rows → conflict. Return 409 Conflict with latest version.
- Frontend must fetch latest version and re-apply user's changes or prompt user.
- Add test: "Two concurrent PUTs, second should fail or merge."

---

### P0-2: RLS Testing is a Checkbox, Not a Plan
**Severity:** P0 | **Likelihood:** MEDIUM | **Impact:** CRITICAL (data breach)

**The Problem:**
- Success criterion: "*RLS verified: Tenant A cannot access Tenant B's lots*"
- Plan allocates 0.5 FTE QA for RLS testing.
- No test scenarios defined. No test data setup. No automation.
- RLS bugs are **silent**: a misconfigured policy doesn't throw errors; it just silently allows/denies.

**Why This Breaks:**
- RLS policies in PostgreSQL are **notoriously easy to bypass**:
  - Forgot to enable RLS on the versions table? Tenant A can query `lot_model_versions` directly.
  - Set `USING` but not `WITH CHECK`? Users can INSERT rows with arbitrary `tenant_id`.
  - Didn't set `row_security = on` at table creation? RLS is disabled by default on existing tables.
  - Superuser connections bypass RLS entirely (is the app running as superuser? Not mentioned).
- No mention of **role-based access control**. Are all users in the same DB role? If yes, RLS alone won't work.
- Frontend sends `tenant_id` in JWT. Is it validated server-side? Not mentioned.

**What's Missing:**
- Explicit RLS test matrix:
  ```
  - Tenant A user tries SELECT on Tenant B lot → DENY
  - Tenant A user tries UPDATE on Tenant B lot → DENY
  - Tenant A user tries INSERT with Tenant B tenant_id → DENY
  - Tenant A user tries DELETE on Tenant B lot → DENY
  - Superuser/admin bypass scenarios documented
  - Cross-tenant query via JOIN (e.g., SELECT * FROM lot_models lm 
    JOIN projects p ON lm.project_id = p.id WHERE p.tenant_id != current_tenant_id) → DENY
  ```
- Automated test suite (pytest with separate DB connections per tenant).
- Security review by external party (not mentioned).
- Staging environment RLS test before pilot.

**Failure Mode:**
Pilot customer B's data is visible to Pilot customer A via a subtle RLS misconfiguration. Discovered during UAT. Regulatory violation (if construction contracts are PII-adjacent). Pilot fails. Legal liability.

**Mitigation (Required Before Sprint):**
- Write RLS test plan NOW (before sprint starts). Include all scenarios above.
- Add to Definition of Done: "All RLS tests pass in staging. Security review completed."
- Assign security-focused engineer to review RLS code (not the person who wrote it).
- Document RLS assumptions in code comments.

---

### P0-3: S3 Fallback Strategy is Undefined (and Will Fail)
**Severity:** P0 | **Likelihood:** HIGH | **Impact:** HIGH (performance + cost)

**The Problem:**
- Plan: "Signed URL generation for large geometry blobs (>5MB fallback to S3)"
- No details:
  - When exactly does a blob become "large"? 5MB is arbitrary.
  - How does the client know to use S3 vs. PostgreSQL?
  - Who generates signed URLs? Frontend or backend?
  - What's the TTL on signed URLs? (If too short, users get 403. If too long, security risk.)
  - What happens if S3 upload fails but DB insert succeeds? Orphaned DB record.
  - What happens if DB insert fails but S3 upload succeeds? Orphaned S3 object (cost leak).

---

## Blue Team Defender

# BLUE TEAM MITIGATIONS: BuildBid H8 Sprint Plan

## Mapping Red Team P0 Findings to Concrete Mitigations

---

## **P0-1: Last-Write-Wins Data Loss Timebomb**

### Mitigation 1.1: Implement Optimistic Locking with Version Numbers
**Acceptance Criteria:**
- [ ] `lot_models` table includes `version INT NOT NULL DEFAULT 1` column
- [ ] PUT endpoint signature requires `version` in request body:
  ```json
  {
    "geometry": {...},
    "metadata": {...},
    "version": 5
  }
  ```
- [ ] Database UPDATE uses version check:
  ```sql
  UPDATE lot_models 
  SET geometry = $1, metadata = $2, version = version + 1, updated_at = NOW()
  WHERE id = $3 AND tenant_id = $4 AND version = $5
  RETURNING version, updated_at;
  ```
- [ ] Endpoint returns **409 Conflict** (not 200) if version mismatch:
  ```json
  {
    "error": "version_conflict",
    "current_version": 6,
    "message": "Your version (5) is stale. Fetch latest and retry."
  }
  ```
- [ ] HTTP status code is exactly `409`, not `400` or `422`
- [ ] Response includes `current_version` and `updated_at` for client reconciliation

**Code Pattern (FastAPI):**
```python
from fastapi import HTTPException, status

@app.put("/api/v1/lots/{lot_id}")
async def update_lot(
    lot_id: UUID,
    update: LotUpdateRequest,  # includes version field
    tenant_id: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        update(LotModel)
        .where(
            (LotModel.id == lot_id) &
            (LotModel.tenant_id == tenant_id) &
            (LotModel.version == update.version)
        )
        .values(
            geometry=update.geometry,
            metadata=update.metadata,
            version=LotModel.version + 1,
            updated_at=func.now()
        )
        .returning(LotModel)
    )
    row = result.scalars().first()
    
    if not row:
        # Fetch current version for client
        current = await db.execute(
            select(LotModel).where(
                (LotModel.id == lot_id) & (LotModel.tenant_id == tenant_id)
            )
        )
        current_lot = current.scalars().first()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "version_conflict",
                "current_version": current_lot.version if current_lot else None,
                "updated_at": current_lot.updated_at.isoformat() if current_lot else None
            }
        )
    return row
```

**Test Requirements:**
- [ ] Unit test: Single PUT succeeds, version increments
- [ ] Unit test: PUT with stale version returns 409 with current_version
- [ ] Integration test: Two concurrent PUTs, second receives 409
- [ ] Integration test: Client retries after 409, succeeds with new version
- [ ] Load test: 100 concurrent PUTs to same lot, exactly 1 succeeds per version increment

**Effort:** 2 days (backend), 1 day (frontend retry logic)

---

### Mitigation 1.2: Add Client-Side Version Tracking and Retry Logic
**Acceptance Criteria:**
- [ ] Frontend stores `currentVersion` in component state alongside `geometry`
- [ ] Auto-save function includes version in PUT request
- [ ] On 409 response, frontend:
  - [ ] Fetches latest lot data (GET /lots/{id})
  - [ ] Displays conflict resolution UI: "Your changes conflict with updates from [user] at [time]. Merge or discard?"
  - [ ] Does NOT silently overwrite
- [ ] Exponential backoff retry: 100ms, 200ms, 400ms, max 3 retries
- [ ] After 3 retries, show user error: "Could not save. Please refresh and try again."
- [ ] No retry on 409 (version conflict requires user action, not retry)

**Code Pattern (React):**
```typescript
const [geometry, setGeometry] = useState(initialGeometry);
const [currentVersion, setCurrentVersion] = useState(initialVersion);
const [conflictState, setConflictState] = useState(null);

const autoSave = useCallback(
  debounce(async (newGeometry) => {
    try {
      const response = await fetch(`/api/v1/lots/${lotId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          geometry: newGeometry,
          metadata: currentMetadata,
          version: currentVersion
        })
      });

      if (response.status === 409) {
        const conflict = await response.json();
        setConflictState({
          serverVersion: conflict.current_version,
          serverUpdatedAt: conflict.updated_at,
          userChanges: newGeometry
        });
        // Fetch latest to show user
        const latest = await fetch(`/api/v1/lots/${lotId}`).then(r => r.json());
        setConflictState(prev => ({ ...prev, serverGeometry: latest.geometry }));
        return;
      }

      if (response.ok) {
        const saved = await response.json();
        setCurrentVersion(saved.version);
        setConflictState(null);
      }
    } catch (err) {
      // Retry logic handled by fetch wrapper with exponential backoff
      retryWithBackoff(() => autoSave(newGeometry), 3);
    }
  }, 2000),
  [lotI

---

## QA Reviewer

# QA Test Strategy: BuildBid H8 — Granular 3D Lot Models (Persistence Layer)

---

## EXECUTIVE SUMMARY

**Completeness Score: 72/100**

**Rationale:**
- ✅ Strong coverage of core persistence, RLS, and concurrent write scenarios
- ✅ Comprehensive edge cases for geometry validation and versioning
- ⚠️ Mobile/responsive testing deferred to H7 dependency (acceptable)
- ⚠️ Performance testing framework defined but load thresholds need refinement
- ❌ S3 fallback testing incomplete (no chaos engineering for blob failures)
- ❌ Multi-user collaboration conflict resolution testing minimal (deferred to H9, but H8 version conflict logic needs deeper coverage)

**Risk Level:** MEDIUM-HIGH
- Version conflict resolution is critical path; inadequate testing = data loss for pilots
- RLS misconfiguration is non-negotiable security risk
- S3 integration is untested failure mode

**Recommendation:** Proceed with sprint; add 2-3 days for S3 chaos testing and version conflict load testing before pilot rollout.

---

## 1. UNIT TESTS

### 1.1 Database Layer (PostgreSQL + SQLAlchemy ORM)

#### Test Suite: `test_lot_model_schema.py`

```python
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from datetime import datetime, timedelta

class TestLotModelSchema:
    """Test lot_models table structure, constraints, and indexes."""

    @pytest.fixture
    def tenant_id(self):
        return uuid4()

    @pytest.fixture
    def project_id(self):
        return uuid4()

    @pytest.fixture
    def valid_geometry(self):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0, 0, 0]
                    },
                    "properties": {"node_id": 1}
                }
            ]
        }

    # ===== SCHEMA VALIDATION TESTS =====

    def test_lot_model_insert_valid_record(self, db_session, tenant_id, project_id, valid_geometry):
        """Verify basic INSERT with all required fields."""
        lot = LotModel(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            geometry=valid_geometry,
            metadata={"created_by": str(uuid4()), "node_count": 1},
            version=1,
            is_deleted=False
        )
        db_session.add(lot)
        db_session.commit()
        
        result = db_session.execute(
            select(LotModel).where(LotModel.id == lot.id)
        ).scalar_one()
        
        assert result.version == 1
        assert result.is_deleted is False
        assert result.geometry == valid_geometry

    def test_lot_model_missing_tenant_id_fails(self, db_session, project_id, valid_geometry):
        """Verify NOT NULL constraint on tenant_id."""
        lot = LotModel(
            id=uuid4(),
            tenant_id=None,  # INVALID
            project_id=project_id,
            geometry=valid_geometry,
            metadata={}
        )
        db_session.add(lot)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_lot_model_missing_geometry_fails(self, db_session, tenant_id, project_id):
        """Verify NOT NULL constraint on geometry."""
        lot = LotModel(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            geometry=None,  # INVALID
            metadata={}
        )
        db_session.add(lot)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_lot_model_version_defaults_to_one(self, db_session, tenant_id, project_id, valid_geometry):
        """Verify version column defaults to 1."""
        lot = LotModel(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            geometry=valid_geometry,
            metadata={}
            # version NOT specified
        )
        db_session.add(lot)
        db_session.commit()
        
        assert lot.version == 1

    def test_lot_model_is_deleted_defaults_to_false(self, db_session, tenant_id, project_id, valid_geometry):
        """Verify is_deleted column defaults to False."""
        lot = LotModel(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            geometry=valid_geometry,
            metadata={}
        )
        db_session.add(lot)
        db_session.commit()
        
        assert lot.is_deleted is False

    def test_lot_model_timestamps_auto_set(self, db_session, tenant_id, project_id, valid_geometry):
        """Verify created_at and updated_at are auto-populated."""
        before = datetime.utcnow()
        lot = LotModel(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            geometry=valid_geometry,
            metadata={}
        )
        db_session.add(lot)
        db_session.commit()
        after = datetime.utcnow()
        
        assert before <= lot.created_at <= after
        assert before <= lot.updated_at <= after

    # ===== INDEX PERFORMANCE TESTS =====

    def test_index_tenant_id_project_id_exists(self, db_session):
        """Verify (tenant_id, project_id) composite index exists."""
        inspector = inspect(db_

---

## Technical Lead [construction]

# Technical Architecture Review: H8 — Granular 3D Lot Models

## CRITICAL BLOCKING DECISIONS

### 🚨 **DECISION 1: Concurrent Write Conflict Resolution**
**Status:** BLOCKS SPRINT START  
**Severity:** CRITICAL

**Current Plan:** Last-write-wins (LWW)  
**Problem:**
- Pilot customers likely have simultaneous users editing same lot (e.g., site manager + estimator)
- LWW silently discards edits → data loss → pilot failure
- No conflict detection or user notification

**Recommended Solutions (Choose One):**

| Approach | Pros | Cons | Recommendation |
|----------|------|------|-----------------|
| **Optimistic Locking (Version Field)** | Detects conflicts; user can merge/retry | Requires frontend retry logic | ✅ **RECOMMENDED** |
| **Operational Transform (OT)** | True collaborative editing | Complex; 2-week effort minimum | ❌ Defer to H9 |
| **CRDT (Conflict-free Replicated Data Type)** | Automatic conflict resolution | Requires new persistence layer | ❌ Out of scope |
| **Pessimistic Locking (Row Lock)** | Prevents conflicts entirely | Blocks concurrent reads; poor UX | ❌ Unacceptable |

**DECISION:** Implement **Optimistic Locking** for H8:
```sql
-- Add to lot_models table
ALTER TABLE lot_models ADD COLUMN version_number INT NOT NULL DEFAULT 1;
ALTER TABLE lot_models ADD COLUMN updated_by UUID NOT NULL;

-- Update endpoint requires version match
UPDATE lot_models 
SET geometry = $1, version_number = version_number + 1, updated_at = NOW()
WHERE id = $2 AND version_number = $3 AND tenant_id = current_tenant_id
RETURNING *;
-- Returns 0 rows if version mismatch → 409 Conflict to frontend
```

**Frontend Behavior:**
- On 409 Conflict: Fetch latest version, show merge dialog, allow user to re-apply changes
- Log conflict events for pilot feedback

**Sprint Impact:** +1 day (frontend merge UI + endpoint logic)

---

### 🚨 **DECISION 2: Geometry Validation & Size Limits**
**Status:** BLOCKS SCHEMA FINALIZATION  
**Severity:** HIGH

**Current Plan:** None mentioned  
**Problem:**
- Invalid JSONB geometry crashes queries or corrupts data
- Unbounded geometry blobs exhaust PostgreSQL memory
- No clear S3 fallback trigger

**DECISION:** Implement Multi-Layer Validation:

```python
# FastAPI schema (pydantic)
from pydantic import BaseModel, validator
import json

class GeometryPayload(BaseModel):
    geometry: dict  # JSONB
    node_count: int
    
    @validator('geometry')
    def validate_geometry(cls, v):
        # 1. Ensure valid GeoJSON or Three.js format
        if not isinstance(v, dict):
            raise ValueError("geometry must be object")
        
        # 2. Check required fields (format-specific)
        if 'vertices' not in v and 'features' not in v:
            raise ValueError("geometry missing vertices or features")
        
        # 3. Size check
        size_bytes = len(json.dumps(v).encode('utf-8'))
        if size_bytes > 5_000_000:  # 5MB threshold
            raise ValueError(f"geometry too large: {size_bytes} bytes")
        
        return v
    
    @validator('node_count')
    def validate_node_count(cls, v):
        if v < 0 or v > 100_000:  # Reasonable bounds
            raise ValueError("node_count out of range [0, 100000]")
        return v

# Database constraint (PostgreSQL)
ALTER TABLE lot_models 
ADD CONSTRAINT geometry_size_check 
CHECK (octet_length(geometry::text) <= 5000000);

ALTER TABLE lot_models 
ADD CONSTRAINT node_count_check 
CHECK (metadata->>'node_count'::int BETWEEN 0 AND 100000);
```

**S3 Fallback Logic:**
```python
# In endpoint handler
if size_bytes > 5_000_000:
    # Store in S3, reference via signed URL
    s3_key = f"lot-models/{tenant_id}/{lot_id}/geometry-v{version}.json"
    s3_client.put_object(
        Bucket='buildbid-models',
        Key=s3_key,
        Body=json.dumps(geometry),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )
    
    # Store signed URL in DB (valid 24h)
    signed_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'buildbid-models', 'Key': s3_key},
        ExpiresIn=86400
    )
    
    db_record = {
        'geometry': None,  # NULL in DB
        's3_url': signed_url,
        'geometry_size_bytes': size_bytes,
        'stored_at': 'S3'
    }
else:
    db_record = {
        'geometry': geometry,  # JSONB in DB
        's3_url': None,
        'geometry_size_bytes': size_bytes,
        'stored_at': 'PostgreSQL'
    }
```

**Schema Update:**
```sql
ALTER TABLE lot_models ADD COLUMN geometry_size_bytes INT;
ALTER TABLE lot_models ADD COLUMN stored_at VARCHAR(20) DEFAULT 'PostgreSQL';
  -- Enum: 'PostgreSQL' | 'S3'

CREATE INDEX idx_stored_at ON lot_models(stored_at) 
WHERE stored_at = 'S3';  -- Monitor S3 usage
```

**Sprint Impact:** +0.5 days (validation logic + S3 integration)

---

### 🚨 **DECISION 3: Version History Retention Policy**
**

---

## UX/UI Designer

# UX/UI Design Review: H8 Lot Model Persistence
## Mobile-First Construction Site Context

---

## CRITICAL UX/FLOW GAPS

### 🔴 **G1: No Offline-First Strategy (HIGH PRIORITY)**

**Issue:** Construction sites have unreliable connectivity. Auto-save with 2s debounce assumes stable network.

**Current Flow Gap:**
```
User edits model on-site (poor signal)
  → Auto-save triggers after 2s
  → Network fails silently
  → User sees no error
  → Refreshes page → data lost
```

**Recommended Solution:**

| Component | Design |
|-----------|--------|
| **Local Storage** | Cache geometry mutations in IndexedDB (not localStorage—too small for 3D data) |
| **Sync Queue** | Queue failed saves; retry on reconnect with exponential backoff |
| **Visual Indicator** | Persistent status badge: "Saving..." → "✓ Saved" / "⚠️ Offline—will sync" / "❌ Sync failed" |
| **Conflict Resolution** | On reconnect, if server version differs: show "Your changes" vs. "Latest version" diff UI (prep for H9 collaboration) |

**Acceptance Criteria:**
- [ ] IndexedDB schema for pending mutations (lot_id, geometry_delta, timestamp)
- [ ] Sync status visible in top-right corner (mobile-friendly, non-intrusive)
- [ ] Retry logic: 1s, 3s, 10s, 30s, then hourly
- [ ] User can manually trigger "Sync now" button
- [ ] Test: Disable network → edit → reconnect → verify data persists

---

### 🔴 **G2: No Error Handling UX (HIGH PRIORITY)**

**Issue:** Auto-save failures (validation errors, S3 timeout, RLS violation) have no user feedback.

**Scenarios Missing:**
```
1. Geometry validation fails (invalid JSON, >100k nodes)
   → Silent failure? Retry loop? User unaware.

2. S3 fallback triggered (blob >5MB)
   → No indication to user; could add 5-10s latency
   → User thinks app is frozen

3. RLS violation (shouldn't happen, but...)
   → 403 error with no context
   → User confused why their lot disappeared
```

**Recommended UX Pattern:**

```
┌─────────────────────────────────────────┐
│ ⚠️ Model too complex (12,500 nodes)     │
│                                         │
│ This lot model exceeds recommended      │
│ complexity. Performance may degrade.    │
│                                         │
│ [Simplify] [Save Anyway] [Learn more]   │
└─────────────────────────────────────────┘

(Toast notification, dismissible, 6s timeout)
```

**Acceptance Criteria:**
- [ ] Geometry validation errors → user-friendly toast (not console errors)
- [ ] S3 fallback → "Large file uploading..." progress indicator
- [ ] RLS errors → "Permission denied" with support contact
- [ ] All errors logged to Sentry with user context (lot_id, tenant_id, action)
- [ ] Test: Trigger each error scenario; verify UX response

---

### 🟡 **G3: Session Restore Flow Unclear (MEDIUM PRIORITY)**

**Issue:** "Load on session restore" is vague. What happens in these scenarios?

**Missing Flows:**

| Scenario | Current Design | Gap |
|----------|---|---|
| User closes tab → reopens BuildBid | Auto-load last lot? | No—which lot? How to choose? |
| User logs out → logs back in | Restore to same lot? | Risky if lot was deleted or reassigned |
| User has 2 tabs open, edits in Tab A | Tab B stale? | No cross-tab sync mentioned |
| User on mobile, switches to desktop | Sync state? | Unclear |

**Recommended Flow:**

```
User logs in
  ↓
Check IndexedDB for "last_active_lot_id"
  ↓
  ├─ If found & user has access:
  │   └─ Load lot + show "Resume editing?" banner
  │       ├─ [Resume] → restore to editor, highlight unsaved changes
  │       └─ [New Lot] → start fresh
  │
  └─ If not found or access revoked:
      └─ Show project list (normal flow)

(Persist last_active_lot_id on every lot load)
```

**Acceptance Criteria:**
- [ ] Last active lot stored in IndexedDB (not localStorage)
- [ ] On login, check access permissions before auto-loading
- [ ] "Resume editing?" banner with clear [Resume] / [New Lot] buttons
- [ ] Cross-tab sync: If user opens lot in Tab B, Tab A gets notified (use BroadcastChannel API)
- [ ] Test: Multi-tab scenario; verify no data conflicts

---

## MOBILE/TABLET-SPECIFIC UX ISSUES

### 🔴 **M1: 3D Model Interaction on Touch (HIGH PRIORITY)**

**Issue:** 3D model manipulation (rotate, pan, zoom) is difficult on touch without proper gestures.

**Current State:** Unclear if H7 (mobile-responsive UI) addresses this.

**Recommended Gestures:**

| Gesture | Action | Feedback |
|---------|--------|----------|
| **1-finger drag** | Pan camera | Smooth; show crosshair |
| **2-finger pinch** | Zoom | Smooth; show zoom level % |
| **2-finger rotate** | Rotate model | Smooth; show rotation angle |
| **Long-press** | Context menu (edit, delete, properties) | Haptic feedback + menu |
| **Double-tap** | Focus/reset view | Smooth animation |

**Acceptance Criteria:**
- [ ] Touch gestures implemented (use Hammer.js or Three.js built-in)
- [ ] No accidental pan/zoom when scrolling page
- [ ] Haptic feedback on long-press (if device supports)
- [ ]

---

## Chief Product Officer

# CPO FINAL DECISION: BuildBid H8 — Granular 3D Lot Models (Persistence Layer)

---

## 🎯 **GO/NO-GO VERDICT: CONDITIONAL GO**

**Decision:** Proceed to sprint with **mandatory pre-launch gates**. Feature is strategically critical for pilot retention but has **3 unresolved technical/UX risks** that must be closed before any customer exposure.

**Rationale:**
- ✅ Core persistence architecture is sound (PostgreSQL + RLS + versioning)
- ✅ Pilot demand is real and urgent (3 customers, next sprint)
- ✅ Blue Team mitigations are concrete and implementable
- ❌ **Concurrent write handling is incomplete** — LWW will cause pilot data loss
- ❌ **Offline-first UX is missing** — construction sites will fail silently
- ❌ **S3 fallback chaos testing absent** — blob failures will break estimates

**Risk Tolerance:** We can absorb 1-2 week sprint delay to close these gaps. We **cannot** absorb pilot failure and customer churn.

---

## 📊 **TOP 3 BUSINESS BETS**

### Bet 1: Persistence = Pilot Retention (Highest ROI)
**Thesis:** Losing 3D models on session end is the #1 blocker for pilot adoption. Solving this unlocks revenue conversation with 3 customers.

**Success Metric:** Pilot customers report "model data survives browser refresh" as working feature in week 1 of sprint.

**Contingency:** If concurrent write conflicts emerge during pilot, fall back to read-only mode for multi-user scenarios (defer H9 collaboration).

---

### Bet 2: Offline-First = Construction Site Viability (Medium ROI)
**Thesis:** BuildBid's TAM is field-based estimators with spotty connectivity. Without offline support, we're building for office users only.

**Success Metric:** Auto-save queue persists locally; users see "syncing..." indicator; zero silent data loss in QA testing.

**Contingency:** Ship with "online-only" warning in v1; add offline queue in H8.1 post-pilot.

---

### Bet 3: RLS + Versioning = Enterprise Trust (Long-term ROI)
**Thesis:** Multi-tenant data isolation and audit trails are table-stakes for construction firms. Getting this right now prevents costly refactors later.

**Success Metric:** RLS penetration testing passes (Tenant A cannot query Tenant B data); version history audit trail verified in QA.

**Contingency:** If RLS testing fails, ship with application-level filtering + security review gate before production.

---

## 🛡️ **RESOLVED RISK REGISTER**

| Risk ID | Red Team Finding | Mitigation (Blue Team) | Owner | Status | Launch Gate? |
|---------|------------------|------------------------|-------|--------|--------------|
| **P0-1** | Last-Write-Wins data loss | Implement optimistic locking (version column + conflict detection) | Tech Lead | ⚠️ IN PROGRESS | **YES** |
| **P0-2** | Silent save failures on-site | Add offline queue (IndexedDB) + sync status UI | UX/Frontend | ⚠️ DESIGN PHASE | **YES** |
| **P0-3** | S3 blob failures crash estimates | Implement retry logic + fallback to smaller geometry | Tech Lead | ⚠️ BACKLOG | **CONDITIONAL** |
| **P1-1** | RLS bypass vulnerability | Penetration test + row-level policy audit | QA/Security | ⏳ SCHEDULED | **YES** |
| **P1-2** | >10K node geometry timeout | Implement pagination + streaming geometry fetch | Tech Lead | ✅ DESIGNED | NO |
| **P1-3** | Mobile UI incomplete (H7 dependency) | Defer mobile testing to H7 integration; ship desktop-first | PM | ✅ SCOPED | NO |
| **P2-1** | Concurrent user conflict UX | Add "conflict detected" modal + manual merge UI | UX | ⚠️ DESIGN PHASE | **CONDITIONAL** |

---

## 📈 **SUCCESS METRICS (Launch Criteria)**

### Tier 1: Must-Have (Blocking)
- [ ] **Persistence:** Lot model survives 5 consecutive browser refreshes + logout/login cycle
- [ ] **Conflict Detection:** Optimistic locking rejects concurrent writes; user sees error message (not silent loss)
- [ ] **Offline Queue:** Auto-save queue persists locally; syncs when connectivity restored; zero data loss in QA
- [ ] **RLS Security:** Penetration test confirms Tenant A cannot access Tenant B's lots via any API endpoint
- [ ] **Load Time:** <2s for lots with <10K geometry nodes (measured in production-like environment)

### Tier 2: Should-Have (Pilot Success)
- [ ] **Version History:** Last 10 versions retrievable; soft-delete recoverable within 30 days
- [ ] **Sync Status UI:** User sees "saving...", "saved", "sync failed" states in real-time
- [ ] **Audit Trail:** All mutations logged with timestamp, user ID, version delta
- [ ] **S3 Fallback:** Geometry >5MB stored in S3; retrieval via signed URL works for 3 pilot customers

### Tier 3: Nice-to-Have (Post-Pilot)
- [ ] Mobile-responsive UI (deferred to H7)
- [ ] Multi-user real-time collaboration (deferred to H9)
- [ ] Conflict merge UI (deferred to H9)

---

## 🚀 **LAUNCH CRITERIA (Go/No-Go Gates)**

### **Gate 1: Concurrent Write Safety (Week 1 of Sprint)**
**Requirement:** Optimistic locking + conflict detection implemented and passing QA.

**Acceptance:** 
- Simulate 2 users editing same lot simultaneously
- Verify second write is rejected with HTTP 409 (Conflict)
- Verify user sees "Your changes conflict with another user's edits" message
- Verify no data is silently lost

**Owner:** Tech Lead + QA

---

## Summary

- **Personas run:** 7
- **Successful:** 7
- **Failed:** 0
- **Total output:** 36,063 characters
