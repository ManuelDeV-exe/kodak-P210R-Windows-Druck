import unittest
from PIL import Image
from app import make_phase_frame, PRINT_PHASES

class PhaseVisualTests(unittest.TestCase):
    def test_sweep_only_affects_finished_region(self):
        sample=Image.new('RGB',(32,48),(100,100,100))
        frame=make_phase_frame(sample,'06',0.5)
        self.assertEqual(frame.getpixel((10,3)),sample.getpixel((10,3)))
        self.assertNotEqual(frame.getpixel((10,45)),sample.getpixel((10,45)))
    def test_completion_has_no_color_overlay(self):
        image=Image.new('RGB',(32,48),(120,60,30))
        self.assertEqual(make_phase_frame(image,'03',0.75).tobytes(),image.tobytes())
    def test_known_phase_names(self):
        self.assertEqual(PRINT_PHASES['06'][0],'Gelb')
        self.assertEqual(PRINT_PHASES['00'][0],'Magenta')
if __name__=='__main__': unittest.main()