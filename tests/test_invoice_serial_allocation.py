from services.reception_his_service import _next_serial
import models


class _Col:
    def __init__(self, name):
        self.key = name

    def like(self, _pattern):
        return self


def test_next_serial_uses_max_not_count(monkeypatch):
    class FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *a, **k):
            return self

        def all(self):
            return self._rows

    class FakeDB:
        def query(self, col):
            return FakeQuery([("INV-2026-017-00010",), ("INV-2026-017-00099",), ("INV-2026-017-00050",)])

    out = _next_serial(FakeDB(), models.Invoice, models.Invoice.invoice_number, 17, "INV")
    assert out == "INV-2026-017-00100"
