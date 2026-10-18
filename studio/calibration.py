"""Printer-coordinate calibration. No external images or hidden print-data modifications."""
import json
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw

SIZE=(640,1024)
DEFAULT={'x_px':0,'y_px':0,'x_mm':0.0,'y_mm':0.0,'paper_width_mm':54.0,'paper_height_mm':86.0}

def settings_path():
    root=Path(os.getenv('APPDATA') or (Path.home()/'.config'))/'P210RStudio'
    return root/'calibration.json'

def load_calibration():
    try:
        p=settings_path()
        data=json.loads(p.read_text(encoding='utf-8'))
        config=DEFAULT.copy()
        for k in DEFAULT:
            if k in data: config[k]=type(DEFAULT[k])(data[k])
        if abs(config['x_px'])>SIZE[0]//3 or abs(config['y_px'])>SIZE[1]//3:raise ValueError('offset too large')
        return config
    except (OSError, ValueError, TypeError, OverflowError, KeyError):
        return DEFAULT.copy()

def save_calibration(settings):
    if not isinstance(settings,dict):raise ValueError('settings must be a dict')
    config=DEFAULT.copy()
    config.update({k:settings[k] for k in DEFAULT if k in settings})
    folder=settings_path().parent
    folder.mkdir(parents=True,exist_ok=True)
    file=settings_path()
    temp=file.with_suffix('.tmp')
    temp.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(file)

def calibration_pattern():
    """Black centered reference square at a fixed pixel location; printer coordinates."""
    im=Image.new('RGB',SIZE,'white')
    d=ImageDraw.Draw(im)
    # Square 380x380, centered in the paper data (not intended as a full bleed).
    cx,cy=SIZE[0]//2,SIZE[1]//2
    half=190
    rect=(cx-half,cy-half,cx+half,cy+half)
    d.rectangle(rect,outline='black',width=5)
    d.line((cx-17,cy,cx+17,cy),fill='black',width=2)
    d.line((cx,cy-17,cx,cy+17),fill='black',width=2)
    return im

def calculate_offsets(left_mm,right_mm,top_mm,bottom_mm,paper_width_mm=54.0,paper_height_mm=86.0):
    """Calculate required movement in the *physical printer image* coordinates.

    Left edge needs +X if left margin is smaller than right margin.
    Top edge needs +Y if top margin is smaller than bottom margin.
    """
    vals=[left_mm,right_mm,top_mm,bottom_mm,paper_width_mm,paper_height_mm]
    if any(not math.isfinite(v) for v in vals):raise ValueError('Alle Messwerte müssen endliche Zahlen sein.')
    if min(vals)<0 or paper_width_mm<=0 or paper_height_mm<=0:
        raise ValueError('Abstände müssen positiv sein; Papiermaße größer als 0.')
    if left_mm+right_mm>=paper_width_mm or top_mm+bottom_mm>=paper_height_mm:
        raise ValueError('Randabstände sind zusammen größer als das Papier.')
    # Squared test printed approximately 380 pixels; paper dims should match the trimmed paper.
    x_mm=(right_mm-left_mm)/2.0
    y_mm=(bottom_mm-top_mm)/2.0
    x_px=round(x_mm*SIZE[0]/paper_width_mm)
    y_px=round(y_mm*SIZE[1]/paper_height_mm)
    if abs(x_px)>SIZE[0]//3 or abs(y_px)>SIZE[1]//3:
        raise ValueError('Ergebnis zu groß. Messungen oder Papiermaße prüfen.')
    return {'x_px':int(x_px),'y_px':int(y_px),'x_mm':round(x_mm,3),'y_mm':round(y_mm,3),
            'paper_width_mm':float(paper_width_mm),'paper_height_mm':float(paper_height_mm)}

def apply_calibration(image,settings):
    """Shift whole JPEG inside white canvas. Applied AFTER physical print orientation."""
    x,y=int(settings.get('x_px',0)),int(settings.get('y_px',0))
    if not x and not y:return image.copy()
    canvas=Image.new('RGB',image.size,'white')
    canvas.paste(image,(x,y))
    return canvas