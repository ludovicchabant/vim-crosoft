import io
import sys


def runscript(scriptfunc, *args):
    """ Executes a given function with the given args. This is because
        the convention is that all python scripts here should have a `main`
        function that takes a custom list of args to override the default
        behaviour of using `sys.args`.
    """
    prevout = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    try:
        scriptfunc(args)
    finally:
        sys.stdout = prevout
    return captured.getvalue()

