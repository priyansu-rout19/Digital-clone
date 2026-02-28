# Database Schema (Component 03)

SQLAlchemy 2.0 ORM models + Alembic migrations for PostgreSQL 17. Defines all persistent tables for clones, documents, user reviews, audit logs, and Sacred Archive provenance graph.

## Files

| File | Purpose |
|---|---|
| `schema.py` | 14 SQLAlchemy models + 3 Pydantic JSONB schemas |
| `migrations/env.py` | Alembic config — loads `DATABASE_URL` from environment |
| `migrations/versions/0001_initial_schema.py` | 6 core tables (all clients) |
| `migrations/versions/0002_provenance_graph.py` | 8 provenance tables (Sacred Archive only) |

## Tables At A Glance

**Migration 0001 (6 core tables):**
`users`, `clones`, `documents`, `review_queue`, `audit_log`, `query_analytics`

**Migration 0002 (8 provenance tables):**
`teaching_sources`, `teachings`, `topics`, `scriptures`, `teaching_topics`, `teaching_scriptures`, `teaching_relations`, `teaching_reviewer_links`

## How to Run

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Verify (no database needed):**
```bash
# Test imports
python -c "from core.db.schema import Clone, ReviewQueue, Document, Teaching"

# Generate SQL without connecting to DB
DATABASE_URL="postgresql://user:pass@localhost/dbname" alembic upgrade --sql head
```

**Apply to real database:**
```bash
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/digitalclone"
alembic upgrade head
```

## Key Decisions (Why We Chose This)

**No Apache AGE for provenance graph**
- Original spec recommended Apache AGE (a PostgreSQL graph extension)
- Apache AGE core team was eliminated in October 2024
- Solution: Pure PostgreSQL tables (`teaching_relations` self-referential) + recursive CTEs for graph traversal
- **Same power, zero external dependencies**

**BIGSERIAL PKs for `audit_log` and `query_analytics`**
- Guarantees ordering: row 1001 always created after row 1000
- UUIDs are random — no ordering guarantee
- Critical for immutable audit trails and efficient time-series append

**`core/db/schema.py` instead of `core/models/database.py`**
- Spec said to put models in `core/models/`
- We separated: `core/models/` = config (CloneProfile), `core/db/` = runtime persistence
- Better architecture: keeps concerns isolated

## What Gets Unblocked

- `review_queue_writer` node → can insert into `review_queue` table
- `provenance_graph_query` node → can run recursive CTEs on `teaching_relations`
- Component 02 (RAG pipeline) → can write ingestion results to `documents` table

## Documentation

See [schema.py](schema.py) docstrings for model details. Recursive CTE pattern documented in `TeachingRelation` class.
