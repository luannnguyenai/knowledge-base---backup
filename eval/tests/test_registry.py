"""Unit tests for the registry module."""
import pytest

from ragbench.core.registry import (
    ComponentNotFoundError,
    _REGISTRY,
    build,
    list_registered,
    register,
)


class _Dummy:
    def __init__(self, x: int = 0) -> None:
        self.x = x


def test_register_and_build_basic():
    register("_test_kind", "_dummy")(_Dummy)
    obj = build("_test_kind", {"name": "_dummy", "x": 42})
    assert isinstance(obj, _Dummy)
    assert obj.x == 42


def test_build_unknown_name_raises():
    with pytest.raises(ComponentNotFoundError, match="Unknown"):
        build("_test_kind", {"name": "_nonexistent"})


def test_build_missing_name_key_raises():
    with pytest.raises(ComponentNotFoundError, match="missing the 'name' field"):
        build("_test_kind", {})


def test_build_unknown_kind_raises():
    with pytest.raises(ComponentNotFoundError):
        build("_totally_unknown_kind", {"name": "x"})


def test_list_registered():
    register("_test_list", "_a")(_Dummy)
    register("_test_list", "_b")(_Dummy)
    names = list_registered("_test_list")
    assert "_a" in names and "_b" in names
