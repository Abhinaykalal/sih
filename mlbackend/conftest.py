"""
pytest configuration — sets environment variables BEFORE any application
module is imported, so that Settings() singletons pick them up correctly.
"""
import os

# Disable JWT enforcement during tests so API chat endpoints return 200
os.environ.setdefault("ENFORCE_JWT_AUTH", "false")
