from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from decimal import Decimal
from scripts.check_pauses import scan, compare, plate_stream

ROOT=Path(__file__).resolve().parent
GOOD=(ROOT/"examples/good.gcode").read_bytes()

class PauseChecks(unittest.TestCase):
    def audit(self, data, expected):
        events,unknown,layers=scan(BytesIO(data))
        return compare(events,unknown,layers,expected,"z_mm")

    def test_motion_wait_is_not_a_pause(self):
        r=self.audit(GOOD.replace(b"M400 U1",b"M400"),[Decimal("1")])
        self.assertEqual(r["status"],"inconclusive")
        self.assertEqual(len(r["unverified"]),1)
        self.assertFalse(r["matched"])

    def test_conditional_and_duplicate(self):
        r=self.audit(GOOD.replace(b"M400 U1",b"M622 J1\nM400 U1\nM623"),[Decimal("1")])
        self.assertEqual(r["status"],"inconclusive")
        r=self.audit(GOOD.replace(b"M400 U1",b"M400 U1\nM400 U1"),[Decimal("1.0")])
        self.assertEqual(len(r["unexpected"]),1)

    def test_complete_layers(self):
        with self.assertRaises(ValueError):
            self.audit(GOOD.split(b"; EXECUTABLE_BLOCK_END")[0],[])
        with self.assertRaises(ValueError):
            self.audit(GOOD.replace(b"by layer",b"by object"),[])
        r=self.audit(GOOD,[Decimal("1.2")])
        self.assertEqual(Decimal(r["unexpected_minus_expected"]),Decimal("-0.2"))

    def test_end_routine_does_not_match_last_layer(self):
        data=(ROOT/"examples/missing.gcode").read_bytes()
        data=data.replace(b"; EXECUTABLE_BLOCK_END",b"; MACHINE_END_GCODE_START\nM400 U1\n; EXECUTABLE_BLOCK_END")
        r=self.audit(data,[Decimal("3")])
        self.assertEqual(r["status"],"inconclusive")
        self.assertFalse(r["matched"])

    def test_selected_archive_member(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"plates.3mf"
            with ZipFile(path,"w") as z:
                z.writestr("Metadata/plate_1.gcode",(ROOT/"examples/missing.gcode").read_bytes())
                z.writestr("Metadata/plate_2.gcode",GOOD)
            with plate_stream(path,2) as stream:
                self.assertEqual(scan(stream)[0][0]["layer"],5)
            with self.assertRaises(ValueError), plate_stream(path,3):
                pass
