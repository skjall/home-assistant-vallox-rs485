# Vendored from ha-integration-standards 0.3.1. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Shared quality gates for custom Home Assistant integrations.

The checks in this package know nothing about any particular integration.
They find the integration in the repository they are run against, read what it
claims in its own files, and hold it to that. Pulling in a newer version of
this package therefore tightens the rules without touching a line of the
integration's code.
"""

__all__ = ["__version__"]

__version__ = "0.3.1"
