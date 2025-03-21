from functools import wraps
from flask import session, redirect, url_for, flash, request


def is_authenticated():
    """Controleert of de gebruiker is ingelogd."""
    return session.get('is_authenticated', False)


def login_required(f):
    """Decorator die ervoor zorgt dat alleen ingelogde gebruikers toegang hebben."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('U moet eerst inloggen om toegang te krijgen.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def authenticate(password):
    """Verifieert het wachtwoord."""
    correct_password = '6583'
    if password == correct_password:
        session['is_authenticated'] = True
        return True
    return False


def logout():
    """Logt de gebruiker uit."""
    session.pop('is_authenticated', None)