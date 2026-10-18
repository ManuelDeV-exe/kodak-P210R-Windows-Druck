import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'driver'))
from print_photo import decode_phase, PHASE_NAMES

class StatusTests(unittest.TestCase):
    def test_known_codes(self):
        for code, name in [(255,'Vorbereitung'),(5,'Gelb'),(6,'Magenta'),(0,'Cyan'),(1,'Schutzschicht'),(2,'Druck läuft (unbekannte Phase)'),(3,'Abgeschlossen')]:
            msg=bytes.fromhex('04030101000000080000000000000000')[:-1] + bytes([code])
            self.assertEqual(decode_phase(msg), {'code':f'{code:02X}','name':name})
    def test_invalid_frames(self):
        self.assertIsNone(decode_phase(b'\x04\x06'+b'\x00'*6))
        self.assertIsNone(decode_phase(b'\x00'*16))
if __name__=='__main__': unittest.main()