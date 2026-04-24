"""FastAPI application for Java Code Reviewer web interface."""

import os
import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Java Code Reviewer")


def get_html_path():
    """Get the absolute path to the HTML template."""
    return os.path.join(os.path.dirname(__file__), "templates", "index.html")


class ReviewRequest(BaseModel):
    """Request model for code review."""
    pr_url: str
    mode: str = "audit_only"


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the frontend HTML page."""
    with open(get_html_path(), "r") as f:
        return f.read()


@app.post("/api/review")
async def review_pr(request: ReviewRequest):
    """Run code review and return results."""
    try:
        from .main import run_review

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_review, request.pr_url, request.mode),
            timeout=180.0
        )
        issues = result.get("issues", [])

        return {
            "success": True,
            "pr_title": result.get("pr_title", ""),
            "pr_url": result.get("pr_url", ""),
            "total_issues": len(issues),
            "issues": [
                {
                    "severity": i["severity"].value if hasattr(i["severity"], "value") else i["severity"],
                    "rule_id": i["rule_id"],
                    "file_path": i["file_path"],
                    "line_number": i["line_number"],
                    "message": i["message"],
                    "code_snippet": i["code_snippet"],
                    "suggestion": i.get("suggestion", ""),
                }
                for i in issues
            ],
            "markdown_report": result.get("markdown_report", ""),
            "error": result.get("error"),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Review timed out after 180 seconds")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def start_server():
    """Start the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()