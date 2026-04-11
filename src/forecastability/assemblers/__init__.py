"""Assembler subpackage — payload and summary construction helpers.

Currently a thin package marker. Neither ``types.py`` nor ``reporting.py``
contain assembly logic that warrants extraction: ``types.py`` holds only pure
Pydantic data containers and ``reporting.py`` exposes only standalone
module-level functions.  Assemblers will be added here if/when models grow
non-trivial construction classmethods that need to be separated.
"""
