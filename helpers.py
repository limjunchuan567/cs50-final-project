from functools import wraps

from flask import redirect, session


def login_required(f):
    """Redirect to /login if nobody is logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated
