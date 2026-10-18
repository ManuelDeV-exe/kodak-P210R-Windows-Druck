import unittest
import tempfile
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from app import Photo, SIZE, LAYOUTS, prepare_image

class LayoutTest(unittest.TestCase):
    def test_all_layouts_and_rotation(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'fixture.jpg'
            Image.new('RGB',(500,750),'#188040').save(p)
            for layout in LAYOUTS:
                item=Photo(p,layout=layout,caption='Test 2026',border=30)
                im=prepare_image(item)
                self.assertEqual(im.size,SIZE)
                if layout!='Ohne Rahmen':
                    self.assertEqual(im.getpixel((0,0)),(255,255,255))
                item.print_rotate=True
                rotated=prepare_image(item,for_print=True)
                expected=im if layout.startswith('Polaroid') else im.rotate(180)
                self.assertEqual(rotated.tobytes(),expected.tobytes())
    def test_white_polaroid_caption_space(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'fixture.jpg'
            Image.new('RGB',(300,500),'#123456').save(p)
            for layout in ('Polaroid 1:1,2','Polaroid 1:1,4','Polaroid 1:1,6'):
                im=prepare_image(Photo(p,layout=layout,caption='Hallo!'))
                self.assertEqual(im.getpixel((5,SIZE[1]-10)),(255,255,255))
                self.assertNotEqual(im.getpixel((SIZE[0]//2,110)),(255,255,255))
                printed=prepare_image(Photo(p,layout=layout,caption='Hallo!'),for_print=True)
                self.assertEqual(printed.getpixel((5,10)),(255,255,255))
                self.assertEqual(printed.tobytes(),im.rotate(180).tobytes())

if __name__=='__main__': unittest.main()