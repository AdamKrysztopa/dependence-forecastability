"""Typed frozen Pydantic result models for LLM agent tool returns.

All public models in this subpackage are frozen (``ConfigDict(frozen=True)``)
and carry only JSON-serialisable Python types.  They replace the previous
``dict[str, Any]`` returns at every ``@agent.tool`` boundary.
"""
