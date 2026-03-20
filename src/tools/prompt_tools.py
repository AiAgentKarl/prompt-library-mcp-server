"""Prompt-Library-Tools — Prompts und Configs teilen, finden und bewerten."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DB_PATH = Path.home() / ".prompt-library" / "prompts.db"


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            prompt_text TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '[]',
            author TEXT DEFAULT '',
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    # Seed mit Beispiel-Prompts
    count = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    if count == 0:
        _seed_prompts(conn)
    return conn


def _seed_prompts(conn):
    """Bibliothek mit bewährten Prompts vorbeladen."""
    prompts = [
        {
            "id": "code-review",
            "title": "Thorough Code Review",
            "description": "Systematic code review covering security, performance, maintainability and correctness",
            "prompt_text": "Review this code systematically. Check for: 1) Security vulnerabilities (injection, auth issues, data exposure) 2) Performance issues (N+1 queries, unnecessary loops, memory leaks) 3) Maintainability (naming, structure, DRY violations) 4) Correctness (edge cases, error handling, race conditions). For each issue found, explain the problem and suggest a fix.",
            "category": "development",
            "tags": '["code-review", "security", "performance", "best-practices"]',
        },
        {
            "id": "api-docs-generator",
            "title": "API Documentation Generator",
            "description": "Generate comprehensive API documentation from code",
            "prompt_text": "Analyze this API code and generate comprehensive documentation including: 1) Endpoint overview table (method, path, description) 2) For each endpoint: parameters, request/response examples, error codes 3) Authentication requirements 4) Rate limits if applicable. Format as clean Markdown.",
            "category": "development",
            "tags": '["api", "documentation", "markdown"]',
        },
        {
            "id": "data-analysis",
            "title": "Data Analysis Framework",
            "description": "Structured approach to analyzing any dataset",
            "prompt_text": "Analyze this data following these steps: 1) Data overview: shape, types, missing values 2) Descriptive statistics: central tendency, distribution, outliers 3) Key patterns: trends, correlations, anomalies 4) Actionable insights: what does this data tell us? 5) Recommendations: what actions should be taken based on findings?",
            "category": "data-science",
            "tags": '["data-analysis", "statistics", "insights"]',
        },
        {
            "id": "bug-investigation",
            "title": "Systematic Bug Investigation",
            "description": "Methodical approach to finding and fixing bugs",
            "prompt_text": "Investigate this bug systematically: 1) Reproduce: What exact steps trigger the bug? 2) Isolate: What's the minimal code that reproduces it? 3) Root cause: WHY does it happen (not just what)? 4) Fix: What's the correct fix (not just a workaround)? 5) Prevention: How do we prevent similar bugs? Add a test case.",
            "category": "development",
            "tags": '["debugging", "testing", "investigation"]',
        },
        {
            "id": "market-research",
            "title": "Market Research Template",
            "description": "Comprehensive market research for a product or service",
            "prompt_text": "Conduct market research on this topic: 1) Market size and growth rate 2) Key players and market share 3) Target audience and segments 4) Competitive advantages/disadvantages 5) Trends and disruptions 6) Opportunities and threats 7) Recommended go-to-market strategy",
            "category": "business",
            "tags": '["market-research", "strategy", "competitive-analysis"]',
        },
        {
            "id": "security-audit",
            "title": "Security Audit Checklist",
            "description": "Comprehensive security review for web applications",
            "prompt_text": "Perform a security audit: 1) Authentication: password policies, MFA, session management 2) Authorization: RBAC, privilege escalation risks 3) Input validation: XSS, SQL injection, CSRF 4) Data protection: encryption at rest/transit, PII handling 5) API security: rate limiting, input validation, auth 6) Dependencies: known vulnerabilities, outdated packages 7) Infrastructure: HTTPS, headers, CORS. Rate each area as Low/Medium/High risk.",
            "category": "security",
            "tags": '["security", "audit", "web", "vulnerabilities"]',
        },
    ]

    now = datetime.utcnow().isoformat()
    for p in prompts:
        p["author"] = "MCP Community"
        p["created_at"] = now
        conn.execute("""
            INSERT OR IGNORE INTO prompts
            (id, title, description, prompt_text, category, tags, author, created_at)
            VALUES (:id, :title, :description, :prompt_text, :category, :tags, :author, :created_at)
        """, p)
    conn.commit()


def register_prompt_tools(mcp: FastMCP):

    @mcp.tool()
    async def search_prompts(query: str, category: str = "") -> dict:
        """Search the prompt library by keyword or category.

        Find tested, community-rated prompts for any task.

        Args:
            query: Search term (e.g. "code review", "security", "data")
            category: Filter by category (optional: development, business, data-science, security)
        """
        conn = _get_db()
        q = f"%{query.lower()}%"

        if category:
            rows = conn.execute("""
                SELECT id, title, description, category, upvotes, downvotes, usage_count
                FROM prompts
                WHERE (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)
                  AND LOWER(category) LIKE ?
                ORDER BY upvotes DESC LIMIT 20
            """, (q, q, q, f"%{category.lower()}%")).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, title, description, category, upvotes, downvotes, usage_count
                FROM prompts
                WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?
                ORDER BY upvotes DESC LIMIT 20
            """, (q, q, q)).fetchall()

        results = [dict(r) for r in rows]
        return {"query": query, "results_count": len(results), "prompts": results}

    @mcp.tool()
    async def get_prompt(prompt_id: str) -> dict:
        """Get a specific prompt by ID, ready to use.

        Returns the full prompt text and metadata.

        Args:
            prompt_id: Prompt ID (from search_prompts)
        """
        conn = _get_db()
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        if not row:
            return {"error": f"Prompt '{prompt_id}' not found"}

        # Nutzungszähler erhöhen
        conn.execute("UPDATE prompts SET usage_count = usage_count + 1 WHERE id = ?", (prompt_id,))
        conn.commit()

        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "prompt_text": row["prompt_text"],
            "category": row["category"],
            "tags": json.loads(row["tags"]),
            "author": row["author"],
            "upvotes": row["upvotes"],
            "usage_count": row["usage_count"] + 1,
        }

    @mcp.tool()
    async def share_prompt(
        prompt_id: str, title: str, prompt_text: str,
        description: str = "", category: str = "general",
        tags: str = "[]", author: str = "",
    ) -> dict:
        """Share a prompt with the community.

        Add a tested prompt or config to the library for others to use.

        Args:
            prompt_id: Unique ID (e.g. "my-code-review")
            title: Display title
            prompt_text: The full prompt text
            description: What this prompt does (1-2 sentences)
            category: Category (development, business, data-science, security, general)
            tags: JSON array of tags (e.g. '["python", "testing"]')
            author: Your name
        """
        conn = _get_db()
        existing = conn.execute("SELECT id FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        if existing:
            return {"error": f"Prompt '{prompt_id}' already exists"}

        conn.execute("""
            INSERT INTO prompts (id, title, description, prompt_text, category, tags, author, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (prompt_id, title, description, prompt_text, category, tags, author,
              datetime.utcnow().isoformat()))
        conn.commit()

        return {"status": "shared", "prompt_id": prompt_id, "message": f"'{title}' added to the library."}

    @mcp.tool()
    async def rate_prompt(prompt_id: str, upvote: bool = True) -> dict:
        """Rate a prompt — upvote if it worked well, downvote if not.

        Helps the community find the best prompts.

        Args:
            prompt_id: Prompt ID to rate
            upvote: True = thumbs up, False = thumbs down
        """
        conn = _get_db()
        row = conn.execute("SELECT id, title FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        if not row:
            return {"error": f"Prompt '{prompt_id}' not found"}

        if upvote:
            conn.execute("UPDATE prompts SET upvotes = upvotes + 1 WHERE id = ?", (prompt_id,))
        else:
            conn.execute("UPDATE prompts SET downvotes = downvotes + 1 WHERE id = ?", (prompt_id,))
        conn.commit()

        return {"status": "rated", "prompt": row["title"], "vote": "upvote" if upvote else "downvote"}

    @mcp.tool()
    async def list_popular_prompts(limit: int = 10) -> dict:
        """List the most popular prompts by usage and votes.

        Args:
            limit: Max results (default: 10)
        """
        conn = _get_db()
        rows = conn.execute("""
            SELECT id, title, description, category, upvotes, downvotes, usage_count
            FROM prompts ORDER BY (upvotes - downvotes + usage_count) DESC LIMIT ?
        """, (limit,)).fetchall()

        return {"prompts": [dict(r) for r in rows]}
