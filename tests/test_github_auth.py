# tests/test_github_auth.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_github_auth_uses_token_class():
    from github import Auth
    import os
    token = os.getenv("GITHUB_TOKEN", "fake-token")
    auth = Auth.Token(token)
    assert auth is not None

def test_no_deprecation_warning_community_monitor(recwarn):
    import warnings
    # Import the module and check no DeprecationWarning about login_or_token
    from src.tools import community_monitor
    dep_warnings = [w for w in recwarn.list
                    if issubclass(w.category, DeprecationWarning)
                    and "login_or_token" in str(w.message)]
    assert len(dep_warnings) == 0, f"Deprecation warning found: {dep_warnings}"

def test_no_deprecation_warning_publisher(recwarn):
    from src.tools import publisher
    dep_warnings = [w for w in recwarn.list
                    if issubclass(w.category, DeprecationWarning)
                    and "login_or_token" in str(w.message)]
    assert len(dep_warnings) == 0, f"Deprecation warning found: {dep_warnings}"
