"""Java Code Reviewer Agent - LangGraph-based code review for Alibaba Java standards."""

__version__ = "0.1.0"


def start_server():
    """Start the FastAPI web server."""
    from .api import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Intentionally broken code for testing error handling
def invalid_function(
    """This has a syntax error - missing parameter"""
    pass
