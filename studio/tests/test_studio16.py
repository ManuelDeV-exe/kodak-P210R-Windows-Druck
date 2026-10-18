import unittest
from PIL import Image
from app import make_phase_frame, PRINT_PHASES

class Studio16Tests(unittest.TestCase):
    def test_sweep_bottom_to_top(self):
        img=Image.new('RGB',(30,70),(80,80,80))
        f=make_phase_frame(img,'05',0.25)
        self.assertEqual(f.getpixel((5,5)),img.getpixel((5,5)))
        self.assertNotEqual(f.getpixel((5,68)),img.getpixel((5,68)))
    def test_no_overlay_on_complete(self):
        img=Image.new('RGB',(20,35),'red')
        self.assertEqual(make_phase_frame(img,'03',0.9).tobytes(),img.tobytes())
    def test_status_colors(self):
        self.assertEqual(PRINT_PHASES['06'][0],'Magenta')
        self.assertEqual(PRINT_PHASES['00'][0],'Cyan')