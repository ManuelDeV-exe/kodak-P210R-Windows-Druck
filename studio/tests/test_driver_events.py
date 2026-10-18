import unittest
from app import parse_driver_event, make_phase_frame
from PIL import Image

class DriverEventTests(unittest.TestCase):
    def test_phases(self):
        self.assertEqual(parse_driver_event('P210R_PHASE 05 Gelb\n'), ('phase','05','Gelb'))
        self.assertEqual(parse_driver_event('P210R_PHASE 03 Abgeschlossen\n'), ('phase','03','Abgeschlossen'))
        self.assertEqual(parse_driver_event('P210R_PHASE 02 Druck läuft (unbekannte Phase)\n')[1], '02')
    def test_transfer_progress(self):
        self.assertEqual(parse_driver_event('P210R_TRANSFER 65536 250768\n'), ('transfer',65536,250768))
        self.assertIsNone(parse_driver_event('P210R_TRANSFER 333 200\n'))
    def test_diagnostic(self):
        self.assertEqual(parse_driver_event('P210R_DIAGNOSTIC Kein_Farbstatus_empfangen\n')[0], 'diagnostic')
    def test_other_output_is_ignored(self):
        self.assertIsNone(parse_driver_event('ACK next request: offset=1234'))
    def test_bottom_to_top_still_works(self):
        src=Image.new('RGB',(60,100),'gray')
        dst=make_phase_frame(src,'06',.3)
        self.assertEqual(dst.getpixel((10,2)),src.getpixel((10,2)))
        self.assertNotEqual(dst.getpixel((10,90)),src.getpixel((10,90)))

if __name__=='__main__':unittest.main()