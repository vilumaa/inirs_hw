import json
import pathlib

import pytest


@pytest.fixture(name="test_file")
def _test_file():
    "Gives access to files in test_data"

    def _open(fname, mode="r", encoding=None, errors=None):
        path = pathlib.Path(__file__).parent.joinpath("test_data", fname)
        return path.open(mode, encoding=encoding, errors=errors)

    return _open


@pytest.fixture(name="json_test_file")
def _json_test_file(test_file):
    def _open(fname, mode="r", encoding=None, errors=None):
        with test_file(fname, mode=mode, encoding=encoding, errors=errors) as json_file:
            return json.load(json_file)

    return _open
