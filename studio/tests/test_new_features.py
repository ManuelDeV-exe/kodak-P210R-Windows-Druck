import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app import Photo, apply_zoom_pan, project_payload, load_project_items, caption_for, exif_date, make_icon

class Studio12Tests(unittest.TestCase):
    def test_project_roundtrip_and_checked_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); image=base/'sample.png'; Image.new('RGB',(40,60),'red').save(image)
            project=base/'batch.p210r.json'
            source=Photo(image, enabled=False, zoom=2.5, pan_x=.25, font_name='Georgia', caption='Hallo',copies=3)
            payload=project_payload([source],project,'COM7')
            project.write_text(json.dumps(payload),encoding='utf-8')
            restored,missing=load_project_items(json.loads(project.read_text()),project)
            self.assertEqual(missing,[])
            self.assertEqual(len(restored),1)
            self.assertFalse(restored[0].enabled)
            self.assertEqual(restored[0].zoom,2.5)
            self.assertEqual(restored[0].font_name,'Georgia')
            self.assertEqual(restored[0].copies,3)
            self.assertEqual(payload['items'][0]['path'],'sample.png')

    def test_missing_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/'x.p210r.json'
            restored,missing=load_project_items({'format':'kodak-p210r-studio-project','version':1,'items':[{'path':'missing.jpg'}]},project)
            self.assertEqual(restored,[])
            self.assertEqual(len(missing),1)

    def test_zoom_and_pan(self):
        im=Image.new('RGB',(200,100),'red')
        im.paste(Image.new('RGB',(100,100),'blue'),(100,0))
        left=apply_zoom_pan(im,(100,100),'Füllen (Beschnitt)',2,-1,0)
        right=apply_zoom_pan(im,(100,100),'Füllen (Beschnitt)',2,1,0)
        self.assertNotEqual(left.getpixel((50,50)),right.getpixel((50,50)))
        self.assertEqual(left.size,(100,100))

    def test_exif_and_icon(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'photo.jpg'; im=Image.new('RGB',(64,90),'white')
            exif=Image.Exif();exif[306]='2026:10:17 19:24:01';im.save(path,exif=exif)
            self.assertEqual(exif_date(path),'17.10.2026')
            self.assertEqual(caption_for(Photo(path,date_from_exif=True)),'17.10.2026')
            self.assertEqual(make_icon().size,(64,64))

if __name__=='__main__':unittest.main()