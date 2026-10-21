"""Container regressions live with the host bootstrap in tests/test_bootstrap.py."""
from fungen_operator.bootstrap import MODELS

def test_four_published_laguna_choices():
    assert len(MODELS) == 4
    assert MODELS['laguna-xs-2.1:q4_K_M'] == 20
