import unittest
import sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from calibration import SIZE, calibration_pattern, calculate_offsets, apply_calibration, DEFAULT
from app import PRINT_PHASES

class CalibrationTests(unittest.TestCase):
    def test_square_centered(self):
        im=calibration_pattern()
        self.assertEqual(im.size,SIZE)
        self.assertEqual(im.getpixel((130,322)),(0,0,0))
        self.assertEqual(im.getpixel((510,702)),(0,0,0))
        self.assertEqual(im.getpixel((10,10)),(255,255,255))
    def test_equal_margins_no_shift(self):
        c=calculate_offsets(11,11,20,20)
        self.assertEqual((c['x_px'],c['y_px']),(0,0))
    def test_asymmetric_margins(self):
        c=calculate_offsets(8,12,20,14,54,86)
        self.assertGreater(c['x_px'],0)
        self.assertLess(c['y_px'],0)
    def test_measurement_validation(self):
        with self.assertRaises(ValueError):calculate_offsets(-1,10,15,15)
        with self.assertRaises(ValueError):calculate_offsets(30,30,20,20)
    def test_shift_fills_white_without_wrap(self):
        im=Image.new('RGB',(10,10),'black')
        o=apply_calibration(im,{'x_px':2,'y_px':-3})
        self.assertEqual(o.getpixel((0,0)),(255,255,255))
        self.assertEqual(o.getpixel((5,0)),(0,0,0))
        self.assertEqual(o.getpixel((3,9)),(255,255,255))
    def test_correct_phase_assignment(self):
        self.assertEqual([PRINT_PHASES[p][0] for p in ('FF','05','06','00','01','02','03')],
                         ['Druckstart','Vorbereitung','Gelb','Magenta','Cyan','Schutzschicht','Abgeschlossen'])

if __name__=='__main__':unittest.main()