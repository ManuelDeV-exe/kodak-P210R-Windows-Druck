"""Offline-Tests; kein Drucker erforderlich."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Photo, prepare_image, SIZE
from driver.print_photo import image_packet, packetize


class ImageTests(unittest.TestCase):
    def test_image_processing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'internes_testbild.jpg'
            Image.new('RGB', (120, 70), '#5588aa').save(p)
            photo = Photo(p)
            for fit in ('Füllen (Beschnitt)', 'Ganzes Bild (weißer Rand)'):
                photo.fit = fit
                photo.rotate = 90
                photo.brightness = 1.2
                photo.contrast = 1.1
                photo.saturation = .8
                image = prepare_image(photo)
                self.assertEqual(image.size, SIZE)
                self.assertEqual(image.mode, 'RGB')
                out = Path(d) / 'result.jpg'
                image.save(out, 'JPEG')
                data = out.read_bytes()
                self.assertTrue(data.startswith(b'\xff\xd8'))
                self.assertTrue(data.endswith(b'\xff\xd9'))

    def test_last_block_size(self):
        data = b'abc' * 11000
        packets = packetize(data)
        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0][:8], b'\x09\x00\x00\x00\x00\x00\x80\x00')
        self.assertEqual(packets[1][:8], b'\x09\x00\x00\x00' + (len(data)-32768).to_bytes(4,'big'))
        self.assertEqual(packets[1][8:], data[32768:])


if __name__ == '__main__':
    unittest.main()