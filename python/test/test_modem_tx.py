import pytest

from radiolab.phy.tx import ModemTx


@pytest.fixture()
def modem():
    _modem = ModemTx()


# @pytest.mark.parametrize()
# def test_modulate_payload():
