import os

# Tests never touch real Firestore or Claude.
os.environ.setdefault("STORE_BACKEND", "memory")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
