from _repo import SRC_ROOT


def test_no_runner_module_exists() -> None:
    runners = [path for path in SRC_ROOT.rglob("*runner*.py") if "__pycache__" not in path.parts]
    assert not runners, f"runner modules must not exist: {runners}"
