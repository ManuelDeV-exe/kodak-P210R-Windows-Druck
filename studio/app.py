"""KODAK P210R Studio — local Tkinter frontend using unmodified v2.3 driver."""
import json
import copy
import datetime
import webbrowser
import math
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageEnhance, ImageOps, ImageTk, ImageDraw, ImageFont, ImageFilter

BASE = Path(__file__).resolve().parent
DRIVER = BASE / 'driver' / 'print_photo.py'
OUTPUT = BASE / 'output'
OUTPUT.mkdir(exist_ok=True)
SIZE = (640, 1024)  # verified photo dimensions from original capture
FORMATS = [('Bilder', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'), ('Alle Dateien', '*.*')]

@dataclass
class Photo:
    path: Path
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    copies: int = 1
    rotate: int = 0
    fit: str = 'Füllen (Beschnitt)'
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    layout: str = 'Foto mit weißem Rand'
    caption: str = ''
    border: int = 22
    print_rotate: bool = False
    name: str = ''
    enabled: bool = True
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    font_name: str = 'Standard'
    date_from_exif: bool = False
    exposure: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    warmth: float = 0.0
    sharpness: float = 0.0
    def __post_init__(self):
        self.name = self.path.name


LAYOUTS = ('Ohne Rahmen', 'Foto mit weißem Rand', 'Polaroid 1:1,2', 'Polaroid 1:1,4', 'Polaroid 1:1,6')
INK = '#233044'
BG = '#eef2f7'
ACCENT = '#4765e9'
PROJECT_VERSION = 1
FONT_CHOICES = ('Standard', 'Segoe UI', 'Arial', 'Georgia', 'Times New Roman', 'Consolas')
FONT_FILES = {
    'Standard': ('segoepr.ttf', 'segoesc.ttf', 'segoeui.ttf'),
    'Segoe UI': ('segoeui.ttf',), 'Arial': ('arial.ttf',),
    'Georgia': ('georgia.ttf',), 'Times New Roman': ('times.ttf',),
    'Consolas': ('consola.ttf',),
}

def exif_date(path):
    """Prefer original capture date, fallback to date digitized; no filesystem timestamp."""
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            # Pillow may store DateTimeOriginal under Exif IFD (34665).
            detail = exif.get_ifd(0x8769) if hasattr(exif, 'get_ifd') else {}
            raw = detail.get(36867) or detail.get(36868) or exif.get(306)
        if raw:
            return datetime.datetime.strptime(str(raw), '%Y:%m:%d %H:%M:%S').strftime('%d.%m.%Y')
    except (OSError, ValueError, TypeError, OverflowError):
        pass
    return None

def caption_for(item):
    if item.date_from_exif:
        return exif_date(item.path) or item.caption.strip()
    return item.caption.strip()

def choose_font(name, size):
    for filename in FONT_FILES.get(name, FONT_FILES['Standard']):
        for location in (f'C:/Windows/Fonts/{filename}', filename):
            try:return ImageFont.truetype(location, size)
            except OSError:pass
    try:return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:return ImageFont.load_default()

def apply_zoom_pan(im, target_size, fit_mode, zoom, pan_x, pan_y):
    """Crop around normalized center; drag positive x shows content shifted right."""
    rw, rh = target_size
    if fit_mode != 'Füllen (Beschnitt)' and zoom <= 1.0001 and not (pan_x or pan_y):
        return ImageOps.contain(im, target_size, method=Image.Resampling.LANCZOS)
    # Always fill target and then zoom using a crop of the *source*.
    w,h = im.size
    base_scale = max(rw / w, rh / h)
    # Allow dragging at zoom=1, even for photos that perfectly match target aspect.
    # A non-zero pan grants a small virtual overscan to create movable content.
    z = max(1.0, min(8.0, float(zoom)))
    if z == 1.0 and (pan_x or pan_y): z = 1.08
    crop_w = min(w, rw / (base_scale*z))
    crop_h = min(h, rh / (base_scale*z))
    # pan coordinates in [-1,1], where +1 slides image right (shows left edge).
    left = (w-crop_w) * (1.0 - max(-1,min(1,pan_x))) / 2
    top = (h-crop_h) * (1.0 - max(-1,min(1,pan_y))) / 2
    cropped=im.crop((int(round(left)),int(round(top)),int(round(left+crop_w)),int(round(top+crop_h))))
    return cropped.resize((rw,rh),Image.Resampling.LANCZOS)

def apply_advanced(im, item):
    """Lightroom-inspired approximate local adjustments; no proprietary Adobe processing."""
    exposure = max(-2.0,min(2.0,float(item.exposure)))
    if exposure: im = ImageEnhance.Brightness(im).enhance(2.0 ** exposure)
    hi=max(-1.0,min(1.0,float(item.highlights)))
    sh=max(-1.0,min(1.0,float(item.shadows)))
    if hi or sh:
        # grayscale masks with smooth transitions; exposure-like selective lift/recovery
        lum=im.convert('L')
        lm=lum.point(lambda v: int((v/255.0)**2*255))
        sm=lum.point(lambda v: int(((255-v)/255.0)**2*255))
        if hi:
            target=ImageEnhance.Brightness(im).enhance(max(0.15,1+0.8*hi))
            im=Image.composite(target, im, lm)
        if sh:
            target=ImageEnhance.Brightness(im).enhance(max(0.15,1+0.9*sh))
            im=Image.composite(target, im, sm)
    warmth=max(-1.0,min(1.0,float(item.warmth)))
    if warmth:
        r,g,b=im.split()
        r=r.point(lambda v: min(255,max(0,round(v*(1+0.17*warmth)))))
        b=b.point(lambda v: min(255,max(0,round(v*(1-0.17*warmth)))))
        im=Image.merge('RGB',(r,g,b))
    sharp=max(0.0,min(2.0,float(item.sharpness)))
    if sharp: im=ImageEnhance.Sharpness(im).enhance(1+1.5*sharp)
    return im

def make_icon():
    """Original vector-like camera pictogram, no bundled photographs or binaries."""
    im=Image.new('RGBA',(64,64),(0,0,0,0))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((3,8,61,56),radius=13,fill='#4765e9')
    d.rounded_rectangle((10,15,54,49),radius=7,outline='#ffffff',width=3)
    d.ellipse((23,21,43,41),outline='#ffffff',width=4)
    d.rounded_rectangle((14,3,32,14),radius=3,fill='#8c9dff')
    return im

def project_payload(items, project_path, port='COM5'):
    base=Path(project_path).resolve().parent
    data=[]
    for it in items:
        d={key:getattr(it,key) for key in ('uid','copies','rotate','fit','brightness','contrast','saturation','layout','caption','border','print_rotate','enabled','zoom','pan_x','pan_y','font_name','date_from_exif','exposure','highlights','shadows','warmth','sharpness')}
        try:d['path']=str(it.path.resolve().relative_to(base))
        except ValueError:d['path']=str(it.path.resolve())
        data.append(d)
    return {'format':'kodak-p210r-studio-project','version':PROJECT_VERSION,'port':port,'items':data}

def load_project_items(payload, project_path):
    if payload.get('format')!='kodak-p210r-studio-project' or payload.get('version')!=PROJECT_VERSION:
        raise ValueError('Unbekanntes Projektformat oder Version')
    base=Path(project_path).resolve().parent
    items=[];missing=[]
    fields=set(Photo.__dataclass_fields__)-{'path','name'}
    for entry in payload.get('items',[]):
        raw=Path(entry['path']); path=raw if raw.is_absolute() else base/raw
        path=path.resolve()
        if not path.is_file():
            missing.append(str(path));continue
        kwargs={k:v for k,v in entry.items() if k in fields}
        kwargs.pop('name',None)
        kwargs['uid']=uuid.uuid4().hex[:10]
        items.append(Photo(path,**kwargs))
    return items,missing



def prepare_image(item, for_print=False):
    """Render upright preview; rotate Polaroids for physical print output."""
    with Image.open(item.path) as src:
        im = ImageOps.exif_transpose(src).convert('RGB')
    if item.rotate:
        im = im.rotate(-item.rotate, expand=True, resample=Image.Resampling.BICUBIC)
    for factor, cls in ((item.brightness, ImageEnhance.Brightness),
                        (item.contrast, ImageEnhance.Contrast),
                        (item.saturation, ImageEnhance.Color)):
        if factor != 1:
            im = cls(im).enhance(factor)
    im = apply_advanced(im, item)

    canvas = Image.new('RGB', SIZE, 'white')
    edge = max(0, min(110, int(item.border)))
    if item.layout == 'Ohne Rahmen':
        rect = (0, 0, SIZE[0], SIZE[1])
    elif item.layout == 'Foto mit weißem Rand':
        rect = (edge, edge, SIZE[0] - edge, SIZE[1] - edge)
    else:
        # Polaroid frame: caption stays below the image, no text over photograph.
        top = max(18, edge)
        bottom_space = {'Polaroid 1:1,2': 190, 'Polaroid 1:1,4': 255, 'Polaroid 1:1,6': 320}.get(item.layout, 255)
        # The requested aspect ratio refers to photo inset, not the fixed paper.
        # 1:1.2 or 1:1.4 means inset height = inset width * ratio.
        ratio = {'Polaroid 1:1,2': 1.2, 'Polaroid 1:1,4': 1.4, 'Polaroid 1:1,6': 1.6}.get(item.layout, 1.4)
        available_w = SIZE[0] - 2 * top
        available_h = SIZE[1] - top - bottom_space
        iw = min(available_w, int(available_h / ratio))
        ih = round(iw * ratio)
        x = (SIZE[0] - iw) // 2
        rect = (x, top, x + iw, top + ih)
    rw, rh = rect[2]-rect[0], rect[3]-rect[1]
    if rw < 10 or rh < 10:
        raise ValueError('Rand zu groß')
    final = apply_zoom_pan(im, (rw,rh), item.fit, item.zoom, item.pan_x, item.pan_y)
    x = rect[0] + (rw - final.width)//2
    y = rect[1] + (rh - final.height)//2
    canvas.paste(final, (x, y))
    if item.layout.startswith('Polaroid') and caption_for(item):
        from PIL import ImageFont
        font=choose_font(item.font_name, 33)
        draw=ImageDraw.Draw(canvas)
        label=' '.join(caption_for(item).split())
        max_width=SIZE[0]-50
        while len(label)>1 and draw.textbbox((0,0),label,font=font)[2]>max_width:
            label=label[:-2]+'…'
        textbb=draw.textbbox((0,0),label,font=font)
        tw=textbb[2]-textbb[0]
        bottom_start=rect[3]
        text_y=bottom_start + max(8,(SIZE[1]-bottom_start-(textbb[3]-textbb[1]))//2) - textbb[1]
        draw.text(((SIZE[0]-tw)//2,text_y),label,fill=INK,font=font)
    if for_print and (item.layout.startswith('Polaroid') != bool(item.print_rotate)):
        canvas = canvas.rotate(180)
    elif for_print and item.print_rotate and not item.layout.startswith('Polaroid'):
        canvas = canvas.rotate(180)
    return canvas


class App:
    def __init__(self, root):
        self.root = root
        root.title('KODAK P210R Studio · 1.4')
        self.icon_image = ImageTk.PhotoImage(make_icon())
        root.iconphoto(True, self.icon_image)
        root.geometry('1280x880')
        root.minsize(1030, 740)
        self.items = []
        self.selected = None
        self.ui_messages = queue.Queue()
        self.running = False
        self.cancel_flag = threading.Event()
        self.preview_photo = None
        self.refresh_after = None
        self.drag_start = None
        self.preview_rect = None
        self.project_path = None
        root.configure(bg=BG)
        self.anim_tick=0
        self._build()
        root.after(90, self._poll_ui)
        root.after(110, self._animate)
        root.protocol('WM_DELETE_WINDOW', self._close)

    def _build(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TFrame',background=BG)
        s.configure('TLabel',background=BG,foreground=INK,font=('Segoe UI',10))
        s.configure('TLabelframe',background=BG,foreground=INK)
        s.configure('TLabelframe.Label',background=BG,foreground=INK,font=('Segoe UI',10,'bold'))
        s.configure('TButton',font=('Segoe UI',10),padding=(12,7),background='#ffffff',foreground=INK,borderwidth=0)
        s.map('TButton',background=[('active','#dce4fa')])
        s.configure('Primary.TButton',background=ACCENT,foreground='white',font=('Segoe UI',10,'bold'),padding=(16,9))
        s.map('Primary.TButton',background=[('active','#3450bf'),('disabled','#b0b7c9')])
        s.configure('Treeview',rowheight=34,background='white',fieldbackground='white',foreground=INK,font=('Segoe UI',10),borderwidth=0)
        s.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),background='#dee5f2',foreground=INK)
        s.map('Treeview',background=[('selected','#cad5ff')],foreground=[('selected',INK)])
        outer = ttk.Frame(self.root, padding=17); outer.pack(fill='both', expand=True)
        top = ttk.Frame(outer); top.pack(fill='x', pady=(0,10))
        ttk.Label(top, text='✦ KODAK P210R Studio', font=('Segoe UI',22,'bold')).pack(side='left')
        ttk.Label(top, text='  · Bluetooth-Fotodruck & Stapelverarbeitung', foreground='#666').pack(side='left')
        help_btn=ttk.Menubutton(top,text='Hilfe & Links  ▾')
        help_btn.pack(side='right',padx=(8,0))
        links=tk.Menu(help_btn,tearoff=0)
        links.add_command(label='KODAK – Herstellerseite ↗',command=lambda:webbrowser.open('https://www.kodakphotoprinter.com/'))
        links.add_command(label='GitHub – Quellcode ↗',command=lambda:webbrowser.open('https://github.com/ManuelDeV-exe/kodak'))
        links.add_command(label='GitHub – Anleitung ↗',command=lambda:webbrowser.open('https://github.com/ManuelDeV-exe/kodak#installation-und-erster-druck'))
        links.add_separator()
        links.add_command(label='Über Studio 1.4',command=lambda:messagebox.showinfo('Über P210R Studio','KODAK P210R Studio 1.4\nUnabhängiges Open-Source-Entwicklungsprojekt\nDrucktreiber: stabile Version 2.3'))
        help_btn['menu']=links
        ttk.Button(top, text='Bilder hinzufügen', command=self.add_files).pack(side='right', padx=3)
        ttk.Button(top, text='Projekt öffnen', command=self.open_project).pack(side='right', padx=3)
        ttk.Button(top, text='Projekt speichern', command=self.save_project).pack(side='right', padx=3)
        ttk.Button(top, text='Ordner hinzufügen', command=self.add_folder).pack(side='right', padx=3)
        mid = ttk.PanedWindow(outer, orient='horizontal'); mid.pack(fill='both', expand=True)
        left = ttk.Frame(mid, padding=(0,5,10,5)); mid.add(left, weight=2)
        right = ttk.Frame(mid, padding=(10,5,0,5)); mid.add(right, weight=3)
        ttk.Label(left, text='Druckwarteschlange', font=('Segoe UI',12,'bold')).pack(anchor='w')
        table_frame = ttk.Frame(left); table_frame.pack(fill='both', expand=True, pady=7)
        self.tree = ttk.Treeview(table_frame, columns=('enabled','copies','status'), show='tree headings', selectmode='browse', height=12)
        self.tree.heading('#0', text='Datei'); self.tree.heading('enabled', text='✓');self.tree.column('enabled',width=38,anchor='center',stretch=False); self.tree.heading('copies', text='Kopien'); self.tree.heading('status', text='Status')
        self.tree.column('#0', width=275, stretch=True); self.tree.column('copies', width=65, anchor='center', stretch=False)
        self.tree.column('status', width=125, anchor='w', stretch=False)
        bar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview); self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side='left', fill='both', expand=True); bar.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._select)
        self.tree.bind('<Button-1>', self._tree_click, add='+')
        controls = ttk.Frame(left); controls.pack(fill='x')
        for text,fn in [('↑',lambda:self.move(-1)),('↓',lambda:self.move(1)),('Entfernen',self.remove),('Liste leeren',self.clear)]:
            ttk.Button(controls,text=text,command=fn).pack(side='left',padx=(0,5))
        logbox = ttk.LabelFrame(left,text='Druckprotokoll',padding=5); logbox.pack(fill='both',expand=True,pady=(12,0))
        self.log_widget = tk.Text(logbox,height=9,wrap='word',state='disabled',font=('Consolas',9))
        self.log_widget.pack(fill='both',expand=True)
        ttk.Label(right,text='Bildvorschau & Bearbeitung',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.preview = tk.Canvas(right,bg='#1d2739',highlightthickness=0,height=345)
        self.preview.pack(fill='both',expand=True,pady=8)
        self.preview.bind('<Configure>',lambda _:self._schedule_preview())
        self.preview.bind('<MouseWheel>',self._mouse_zoom)
        self.preview.bind('<Button-4>',lambda e:self._mouse_zoom(e,1))
        self.preview.bind('<Button-5>',lambda e:self._mouse_zoom(e,-1))
        self.preview.bind('<ButtonPress-1>',self._drag_begin)
        self.preview.bind('<B1-Motion>',self._drag_move)
        self.preview.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag_start',None))
        self.tip_label=ttk.Label(right,text='▼  Abreißstreifen: kurze Papierseite · nicht Teil des Druckbilds',foreground='#566783')
        self.tip_label.pack(anchor='w',pady=(0,4))
        ttk.Label(right,text='Mausrad: Zoom  ·  Linke Maustaste ziehen: Bild verschieben',foreground='#566783').pack(anchor='w')
        edit = ttk.LabelFrame(right,text='Bild & Drucklayout',padding=10); edit.pack(fill='x')
        layoutrow=ttk.Frame(edit);layoutrow.pack(fill='x',pady=(0,7))
        ttk.Label(layoutrow,text='Druckstil:').pack(side='left',padx=(0,9))
        self.layout_var=tk.StringVar(value='Foto mit weißem Rand')
        layouts=ttk.Combobox(layoutrow,textvariable=self.layout_var,values=LAYOUTS,state='readonly',width=27)
        layouts.pack(side='left',fill='x',expand=True)
        layouts.bind('<<ComboboxSelected>>',lambda _:self._change('layout',self.layout_var.get()))
        captionrow=ttk.Frame(edit);captionrow.pack(fill='x',pady=(0,7))
        ttk.Label(captionrow,text='Polaroid-Text:').pack(side='left',padx=(0,8))
        self.caption_var=tk.StringVar()
        self.caption_entry=ttk.Entry(captionrow,textvariable=self.caption_var)
        self.caption_entry.pack(side='left',fill='x',expand=True)
        self.caption_var.trace_add('write',lambda *_:self._change('caption',self.caption_var.get()))
        fontrow=ttk.Frame(edit);fontrow.pack(fill='x',pady=(0,7))
        ttk.Label(fontrow,text='Schriftart:').pack(side='left',padx=(0,8))
        self.font_var=tk.StringVar(value='Standard')
        fonts=ttk.Combobox(fontrow,textvariable=self.font_var,values=FONT_CHOICES,state='readonly',width=20)
        fonts.pack(side='left',fill='x',expand=True)
        fonts.bind('<<ComboboxSelected>>',lambda _:self._change('font_name',self.font_var.get()))
        self.exif_var=tk.BooleanVar(value=False)
        ttk.Checkbutton(fontrow,text='EXIF-Datum',variable=self.exif_var,command=lambda:self._change('date_from_exif',self.exif_var.get())).pack(side='left',padx=(10,0))
        borderrow=ttk.Frame(edit);borderrow.pack(fill='x',pady=(0,7))
        ttk.Label(borderrow,text='Weißer Rand:').pack(side='left',padx=(0,8))
        self.border_var=tk.IntVar(value=22)
        ttk.Scale(borderrow,from_=0,to=100,variable=self.border_var,command=lambda v:self._change('border',round(float(v)))).pack(side='left',fill='x',expand=True)
        self.border_text=ttk.Label(borderrow,text='22 px',width=7)
        self.border_text.pack(side='left',padx=6)
        self.orientation_var=tk.BooleanVar(value=False)
        ttk.Checkbutton(edit,text='Druckausrichtung umkehren (Polaroid wird automatisch korrigiert)',variable=self.orientation_var,
                        command=lambda:self._change('print_rotate',self.orientation_var.get())).pack(anchor='w',pady=(0,7))
        row1=ttk.Frame(edit);row1.pack(fill='x',pady=3)
        ttk.Button(row1,text='↻ 90°',command=lambda:self.rotate(90)).pack(side='left')
        ttk.Button(row1,text='↺ 90°',command=lambda:self.rotate(-90)).pack(side='left',padx=5)
        ttk.Label(row1,text='Einpassung:').pack(side='left',padx=(12,5))
        self.fit_var=tk.StringVar(value='Füllen (Beschnitt)')
        fit=ttk.Combobox(row1,textvariable=self.fit_var,values=['Füllen (Beschnitt)','Ganzes Bild (weißer Rand)'],state='readonly',width=27)
        fit.pack(side='left',fill='x',expand=True)
        fit.bind('<<ComboboxSelected>>',lambda _:self._change('fit',self.fit_var.get()))
        row2=ttk.Frame(edit);row2.pack(fill='x',pady=5)
        self.copies_var=tk.IntVar(value=1)
        ttk.Label(row2,text='Kopien:').pack(side='left'); self.copies_spin=ttk.Spinbox(row2,from_=1,to=99,textvariable=self.copies_var,width=5,command=self._set_copies)
        self.copies_spin.pack(side='left',padx=7); self.copies_spin.bind('<FocusOut>',lambda _:self._set_copies());self.copies_spin.bind('<Return>',lambda _:self._set_copies())
        ttk.Button(row2,text='Alle Einstellungen zurücksetzen',command=self.reset_edits).pack(side='right')
        ttk.Button(row2,text='Bild zentrieren',command=self.center_crop).pack(side='right',padx=5)
        ttk.Button(row2,text='Weitere Bearbeitung…',command=self.advanced_editor).pack(side='right',padx=5)
        self.sliders={}
        for label,attr in [('Helligkeit','brightness'),('Kontrast','contrast'),('Sättigung','saturation')]:
            r=ttk.Frame(edit);r.pack(fill='x',pady=3)
            ttk.Label(r,text=label,width=14).pack(side='left')
            v=tk.DoubleVar(value=1)
            scale=ttk.Scale(r,from_=0.5,to=1.5,variable=v,command=lambda val,a=attr:self._change(a,round(float(val),3)))
            scale.pack(side='left',fill='x',expand=True,padx=7)
            valuelabel=ttk.Label(r,text='100 %',width=7);valuelabel.pack(side='left')
            self.sliders[attr]=(v,valuelabel)
        bottom=ttk.LabelFrame(outer,text='Druck',padding=10);bottom.pack(fill='x',pady=(12,0))
        ttk.Label(bottom,text='Bluetooth-COM-Port:').pack(side='left')
        self.port=tk.StringVar(value='COM5');ttk.Entry(bottom,textvariable=self.port,width=9).pack(side='left',padx=(5,12))
        self.poll_var=tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom,text='Druckphasen live anzeigen (Statusabfragen)',variable=self.poll_var).pack(side='left',padx=8)
        self.status=tk.StringVar(value='Bereit · Keine Fotos')
        self.phase=tk.StringVar(value='Druckphase: —')
        ttk.Label(bottom,textvariable=self.status).pack(side='left',padx=10)
        ttk.Label(bottom,textvariable=self.phase,foreground='#345db2').pack(side='left',padx=10)
        self.stop_btn=ttk.Button(bottom,text='Nach aktuellem Foto stoppen',command=self.stop,state='disabled');self.stop_btn.pack(side='right',padx=4)
        self.start_btn=ttk.Button(bottom,text='Stapel drucken',style='Primary.TButton',command=self.start);self.start_btn.pack(side='right',padx=4)
        ttk.Button(bottom,text='Vorschau-JPEG speichern',command=self.export).pack(side='right',padx=4)
        self.progress=ttk.Progressbar(outer,mode='indeterminate',length=180)
        self.progress.pack(fill='x',pady=(9,0))
        self.progress['value']=0
        self._log('Druckroutine: unveränderte V2.3. Änderungen werden nur am vorbereiteten Foto vorgenommen.')

    def _log(self,msg):
        self.log_widget.configure(state='normal'); self.log_widget.insert('end',f'{time.strftime("%H:%M:%S")}  {msg}\n');self.log_widget.see('end');self.log_widget.configure(state='disabled')

    def add_files(self):
        selected=filedialog.askopenfilenames(title='Fotos auswählen',filetypes=FORMATS)
        self._append([Path(x) for x in selected])

    def add_folder(self):
        folder=filedialog.askdirectory(title='Fotoordner auswählen')
        if folder:self._append(sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}),key=lambda p:p.name.lower()))

    def _append(self,paths):
        added=0
        for path in paths:
            try:
                with Image.open(path) as im: im.verify()
                item=Photo(path); self.items.append(item);self.tree.insert('', 'end', iid=item.uid,text=item.name,values=('☑',item.copies,'Wartend'));added+=1
            except Exception as ex:self._log(f'Übersprungen: {path.name}: {ex}')
        if added and self.selected is None:self.tree.selection_set(self.items[0].uid);self._select()
        self.status.set(f'{len(self.items)} Fotos in der Warteschlange')

    def _tree_click(self,event):
        if self.running:return
        row=self.tree.identify_row(event.y)
        if row and self.tree.identify_column(event.x)=='#1':
            item=next((x for x in self.items if x.uid==row),None)
            if item:
                item.enabled=not item.enabled
                self.tree.set(row,'enabled','☑' if item.enabled else '☐')
                self.status.set(f'{sum(x.enabled for x in self.items)} aktive Fotos')
            return 'break'

    def _mouse_zoom(self,event,direction=None):
        if self.running:return
        it=self._current()
        if not it:return
        sign=direction if direction is not None else (1 if event.delta>0 else -1)
        it.zoom=max(1.0,min(8.0,it.zoom*(1.12 if sign>0 else 1/1.12)))
        self._schedule_preview()

    def _drag_begin(self,event):
        self.drag_start=(event.x,event.y)

    def _drag_move(self,event):
        if self.running or not self.drag_start:return
        it=self._current()
        if not it:return
        x,y=self.drag_start;self.drag_start=(event.x,event.y)
        if not self.preview_rect:return
        _,_,w,h=self.preview_rect
        effective_zoom=max(1.08,it.zoom)
        it.pan_x=max(-1,min(1,it.pan_x+2*(event.x-x)/max(1,w)/(1-1/effective_zoom)))
        it.pan_y=max(-1,min(1,it.pan_y+2*(event.y-y)/max(1,h)/(1-1/effective_zoom)))
        self._schedule_preview()

    def _current(self):
        return next((x for x in self.items if x.uid==self.selected),None)

    def _select(self,_=None):
        selection=self.tree.selection()
        if not selection:return
        self.selected=selection[0];item=self._current()
        if item:
            self.fit_var.set(item.fit);self.copies_var.set(item.copies)
            self.layout_var.set(item.layout);self.caption_var.set(item.caption)
            self.font_var.set(item.font_name);self.exif_var.set(item.date_from_exif)
            self.border_var.set(item.border);self.border_text.configure(text=f'{item.border} px')
            self.orientation_var.set(item.print_rotate)
            for attr,(v,lbl) in self.sliders.items():v.set(getattr(item,attr));lbl.configure(text=f'{int(round(getattr(item,attr)*100))} %')
            self._schedule_preview()

    def _change(self,attr,value):
        if self.running:return
        item=self._current()
        if item:setattr(item,attr,value)
        if attr=='border':self.border_text.configure(text=f'{value} px')
        if attr in self.sliders:self.sliders[attr][1].configure(text=f'{int(round(value*100))} %')
        self._schedule_preview()

    def _set_copies(self):
        if self.running:return
        item=self._current()
        if item:
            try:item.copies=max(1,min(99,int(self.copies_var.get())))
            except (ValueError,tk.TclError):item.copies=1
            self.copies_var.set(item.copies);self.tree.set(item.uid,'copies',item.copies)

    def rotate(self,degrees):
        if self.running:return
        item=self._current()
        if item:item.rotate=(item.rotate+degrees)%360;self._schedule_preview()

    def reset_edits(self):
        if self.running:return
        item=self._current()
        if not item:return
        if not messagebox.askyesno('Zurücksetzen', 'Alle Einstellungen des ausgewählten Fotos zurücksetzen (inklusive Kopienzahl, Druckhaken und Expertenkorrekturen)?'):
            return
        defaults=Photo(item.path)
        for name in Photo.__dataclass_fields__:
            if name not in ('path','uid','name'):
                setattr(item,name,getattr(defaults,name))
        self.tree.set(item.uid,'copies',item.copies)
        self.tree.set(item.uid,'enabled','☑' if item.enabled else '☐')
        self._select()

    def center_crop(self):
        if self.running:return
        it=self._current()
        if it:
            it.pan_x=it.pan_y=0.0
            self._schedule_preview()

    def advanced_editor(self):
        if self.running:return
        item=self._current()
        if item is None:
            messagebox.showinfo('Weitere Bearbeitung','Bitte ein Bild auswählen.');return
        dialog=tk.Toplevel(self.root)
        dialog.title('Weitere Bearbeitung · Studio 1.4')
        dialog.geometry('850x690');dialog.minsize(650,540)
        dialog.transient(self.root)
        dialog.configure(bg=BG)
        original=copy.copy(item)
        before=copy.copy(item)
        before.exposure=before.highlights=before.shadows=before.warmth=before.sharpness=0.0
        layout=ttk.Frame(dialog,padding=16);layout.pack(fill='both',expand=True)
        ttk.Label(layout,text='Weitere Bearbeitung',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(layout,text='Licht · Details · Farbtemperatur – Änderungen werden direkt im Foto übernommen.',foreground='#58657a').pack(anchor='w',pady=(2,9))
        sw=tk.Canvas(layout,bg='#202b3d',highlightthickness=0,height=320)
        sw.pack(fill='both',expand=True,pady=(0,10))
        show_before=tk.BooleanVar(value=False)
        cache={'photo':None,'after':None}
        def show(*_):
            try:
                image=prepare_image(before if show_before.get() else item)
                w=max(200,sw.winfo_width()-14);h=max(180,sw.winfo_height()-14)
                image.thumbnail((w,h),Image.Resampling.LANCZOS)
                cache['photo']=ImageTk.PhotoImage(image)
                sw.delete('all');sw.create_image(sw.winfo_width()//2,sw.winfo_height()//2,image=cache['photo'])
            except Exception as exc:
                sw.delete('all');sw.create_text(180,80,text=str(exc),fill='white')
        sw.bind('<Configure>',show)
        ttk.Checkbutton(layout,text='Vorher anzeigen (zum Vergleichen)',variable=show_before,command=show).pack(anchor='w',pady=(0,8))
        fields=[('Belichtung','exposure',-2,2),('Lichter','highlights',-1,1),('Tiefen','shadows',-1,1),('Temperatur','warmth',-1,1),('Schärfe','sharpness',0,2)]
        controls=ttk.Frame(layout);controls.pack(fill='x')
        vars={}
        for index,(label,key,lo,hi) in enumerate(fields):
            line=ttk.Frame(controls);line.pack(fill='x',pady=3)
            ttk.Label(line,text=label,width=15).pack(side='left')
            var=tk.DoubleVar(value=getattr(item,key));vars[key]=var
            value_lbl=ttk.Label(line,text=f'{var.get():+.2f}',width=8)
            def on_slide(value,k=key,lbl=value_lbl):
                setattr(item,k,round(float(value),3));lbl.configure(text=f'{float(value):+.2f}')
                if not show_before.get():show()
                self._schedule_preview()
            ttk.Scale(line,from_=lo,to=hi,variable=var,command=on_slide).pack(side='left',fill='x',expand=True,padx=9)
            value_lbl.pack(side='left')
        actions=ttk.Frame(layout);actions.pack(fill='x',pady=(12,0))
        def defaults():
            for key,var in vars.items():
                var.set(0.0);setattr(item,key,0.0)
            show();self._schedule_preview()
        def cancel():
            for key in vars:setattr(item,key,getattr(original,key))
            self._schedule_preview();dialog.destroy()
        ttk.Button(actions,text='Korrekturen zurücksetzen',command=defaults).pack(side='left')
        ttk.Button(actions,text='Abbrechen',command=cancel).pack(side='right',padx=4)
        ttk.Button(actions,text='Übernehmen',style='Primary.TButton',command=dialog.destroy).pack(side='right',padx=4)
        dialog.protocol('WM_DELETE_WINDOW',cancel)
        dialog.after(80,show)

    def _schedule_preview(self):
        if self.refresh_after:self.root.after_cancel(self.refresh_after)
        self.refresh_after=self.root.after(120,self._render_preview)

    def _render_preview(self):
        self.refresh_after=None
        item=self._current();self.preview.delete('all');self.preview_rect=None
        if not item:
            self.preview.create_text(max(self.preview.winfo_width()//2,100),max(self.preview.winfo_height()//2,100),text='Fotos hinzufügen, um eine Vorschau zu sehen',fill='white');return
        try:
            im=prepare_image(item)
            width=max(100,self.preview.winfo_width()-32);height=max(100,self.preview.winfo_height()-32)
            im.thumbnail((width,height),Image.Resampling.LANCZOS)
            self.preview_photo=ImageTk.PhotoImage(im)
            cx=self.preview.winfo_width()//2;cy=self.preview.winfo_height()//2
            self.preview.create_rectangle(cx-im.width//2-8,cy-im.height//2-8,cx+im.width//2+8,cy+im.height//2+8,fill='#152035',outline='')
            self.preview.create_image(cx,cy,image=self.preview_photo)
            self.preview_rect=(cx-im.width//2,cy-im.height//2,im.width,im.height)
            # Tear-off strip always sits on the short paper edge. For vertical
            # 640x1024 canvas, the output-side marker is therefore below.
            self.preview.create_line(cx-im.width//2,cy+im.height//2+13,cx+im.width//2,cy+im.height//2+13,fill='#f4c271',width=3,dash=(5,4))
        except Exception as ex:self._log(f'Vorschaufehler: {ex}')

    def move(self,direction):
        if self.running:return
        it=self._current()
        if not it:return
        idx=self.items.index(it);new=idx+direction
        if 0<=new<len(self.items):
            self.items[idx],self.items[new]=self.items[new],self.items[idx]
            self.tree.move(it.uid,'',new)

    def remove(self):
        if self.running:return
        it=self._current()
        if it:
            self.items.remove(it);self.tree.delete(it.uid);self.selected=None
            if self.items:self.tree.selection_set(self.items[0].uid);self._select()
            else:self.preview.delete('all')

    def clear(self):
        if self.running:return
        self.items.clear();self.selected=None
        for iid in self.tree.get_children():self.tree.delete(iid)
        self.preview.delete('all')
        self.status.set('Bereit · Keine Fotos')
        self.project_path=None

    def save_project(self):
        if self.running:return
        path=filedialog.asksaveasfilename(title='Projekt speichern',defaultextension='.p210r.json',
            filetypes=[('P210R-Projekt','*.p210r.json'),('JSON','*.json')],initialfile=Path(self.project_path).name if self.project_path else 'mein_projekt.p210r.json')
        if not path:return
        try:
            payload=project_payload(self.items,path,self.port.get().strip())
            tmp=Path(path+'.tmp')
            tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
            tmp.replace(path)
            self.project_path=path
            self._log('Projekt gespeichert: '+path)
        except Exception as ex:messagebox.showerror('Projekt speichern',str(ex))

    def open_project(self):
        if self.running:return
        path=filedialog.askopenfilename(title='Projekt öffnen',filetypes=[('P210R-Projekt','*.p210r.json'),('JSON','*.json')])
        if not path:return
        if self.items and not messagebox.askyesno('Projekt öffnen','Aktuelle Warteschlange ersetzen?'):return
        try:
            payload=json.loads(Path(path).read_text(encoding='utf-8'))
            items,missing=load_project_items(payload,path)
        except Exception as ex:return messagebox.showerror('Projekt öffnen',str(ex))
        self.clear();self.items=items;self.port.set(str(payload.get('port','COM5')))
        for item in items:self.tree.insert('', 'end', iid=item.uid,text=item.name,values=('☑' if item.enabled else '☐',item.copies,'Wartend'))
        if items:self.tree.selection_set(items[0].uid);self._select()
        self.project_path=path
        self.status.set(f'{len(items)} Bilder aus Projekt geladen')
        if missing:messagebox.showwarning('Fehlende Bilddateien',f'{len(missing)} Bilder nicht gefunden und übersprungen:\n'+'\n'.join(missing[:8]))

    def export(self):
        item=self._current()
        if not item:return messagebox.showinfo('Info','Bitte zuerst ein Bild auswählen.')
        path=filedialog.asksaveasfilename(defaultextension='.jpg',filetypes=[('JPEG','*.jpg')],initialfile=item.path.stem+'_p210r.jpg')
        if path:
            try:prepare_image(item,for_print=True).save(path,'JPEG',quality=94,subsampling=0)
            except Exception as ex:messagebox.showerror('Fehler',str(ex))
            else:self._log(f'Bild gespeichert: {path}')

    def start(self):
        if self.running:return
        if not any(x.enabled for x in self.items):return messagebox.showinfo('Keine aktiven Bilder','Bitte mindestens ein Foto in der Warteschlange anhaken.')
        port=self.port.get().strip()
        if not port:return messagebox.showerror('Fehler','Bitte COM-Port eintragen.')
        if not DRIVER.exists():return messagebox.showerror('Fehler','V2.3 Druckroutine fehlt.')
        # Immutable snapshot; edits are disabled while running.
        snapshot=[copy.copy(x) for x in self.items if x.enabled]
        self.running=True;self.cancel_flag.clear()
        self.start_btn.configure(state='disabled');self.stop_btn.configure(state='normal')
        self.status.set('Druck läuft …')
        self.phase.set('Druckphase: Übertragung / Vorbereitung')
        self.progress.start(12)
        threading.Thread(target=self._worker,args=(snapshot,port,self.poll_var.get()),daemon=True).start()

    def stop(self):
        self.cancel_flag.set();self._log('Stop angefordert: aktueller Druck läuft zu Ende.')
        self.status.set('Stop nach aktuellem Foto angefordert')

    def _worker(self,items,port,poll):
        jobid=time.strftime('%Y%m%d_%H%M%S')
        work=OUTPUT/jobid;work.mkdir(parents=True,exist_ok=True)
        jobs=[(item,c) for item in items for c in range(1,item.copies+1)]
        successful=0;failed=0
        for index,(item,copy_num) in enumerate(jobs,1):
            if self.cancel_flag.is_set():break
            self.ui_messages.put(('status',f'Foto {index}/{len(jobs)}: {item.name}'))
            self.ui_messages.put(('tree',(item.uid,'Druck läuft')))
            target=work/f'{index:04d}_{item.uid}.jpg';report=work/f'{index:04d}_{item.uid}.json'
            try:
                prepare_image(item,for_print=True).save(target,'JPEG',quality=94,subsampling=0,optimize=False)
                args=[sys.executable,str(DRIVER),'--send','--port',port,'--image',str(target),'--report',str(report)]
                if poll:args.append('--poll')
                self.ui_messages.put(('log',f'{index}/{len(jobs)} → {item.name}, Kopie {copy_num}/{item.copies}'))
                # The v2.3 script remains an external, unmodified subprocess.
                # Line-buffered driver output makes observed print phases visible in real time.
                # No serial/Bluetooth frame or transfer behavior is modified.
                args.append('--emit-phases')
                output_lines=[]
                with subprocess.Popen(args,cwd=str(BASE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                      text=True,encoding='utf-8',errors='replace',bufsize=1) as process:
                    began=time.monotonic()
                    for line in process.stdout:
                        output_lines.append(line)
                        if line.startswith('P210R_PHASE '):
                            parts=line.strip().split(' ',2)
                            if len(parts)==3:
                                self.ui_messages.put(('phase',parts[2]))
                                self.ui_messages.put(('tree',(item.uid,parts[2])))
                        if time.monotonic()-began>300:
                            process.kill()
                            raise TimeoutError('Druckauftrag nach 300 Sekunden abgebrochen')
                    code=process.wait(timeout=5)
                result_stdout=''.join(output_lines)
                try:data=json.loads(report.read_text(encoding='utf-8'))
                except Exception:data={}
                error=data.get('error')
                if code!=0 or error or data.get('result')=='error':
                    failed+=1;self.ui_messages.put(('tree',(item.uid,'Fehler')))
                    self.ui_messages.put(('log',f'Druckfehler: {error or result_stdout[-800:]}'))
                    self.cancel_flag.set()  # don't continue batch after protocol failure
                else:
                    successful+=1
                    self.ui_messages.put(('tree',(item.uid,'Übertragen')))
                    self.ui_messages.put(('log',f'Übertragung abgeschlossen · Druckbericht: {report.name} · Status: {data.get("result","unbekannt")}'))
                if self.cancel_flag.is_set():break
            except Exception as ex:
                failed+=1;self.cancel_flag.set()
                self.ui_messages.put(('tree',(item.uid,'Fehler')))
                self.ui_messages.put(('log',f'Fehler: {ex}. Stapel wird zur Sicherheit beendet.'))
                break
        self.ui_messages.put(('finished',(successful,failed,self.cancel_flag.is_set(),str(work))))

    def _poll_ui(self):
        try:
            while True:
                action,data=self.ui_messages.get_nowait()
                if action=='log':self._log(data)
                elif action=='status':self.status.set(data)
                elif action=='phase':self.phase.set('Druckphase: '+data)
                elif action=='tree':
                    uid,state=data
                    if self.tree.exists(uid):self.tree.set(uid,'status',state)
                elif action=='finished':
                    success,failed,stopped,path=data
                    self.running=False;self.start_btn.configure(state='normal');self.stop_btn.configure(state='disabled')
                    self.progress.stop();self.progress['value']=0
                    msg=f'{success} Übertragungen abgeschlossen, {failed} Fehler'+(' · Stapel gestoppt' if stopped else '')
                    self.status.set(msg);self._log(msg+' · Protokolle in '+path)
                    if failed:messagebox.showwarning('Druckstapel',msg+'\nDetails im Protokoll.')
        except queue.Empty:pass
        self.root.after(90,self._poll_ui)

    def _animate(self):
        # A subtle animated activity marker, only while a print is active.
        self.anim_tick=(self.anim_tick+1)%4
        if self.running:
            self.tip_label.configure(text='◀  Abreißstreifen links beim Auswurf  '+'·'*self.anim_tick)
        else:
            self.tip_label.configure(text='◀  Abreißstreifen links beim Auswurf · nicht Teil des Druckbilds')
        self.root.after(280,self._animate)

    def _close(self):
        if self.running:
            messagebox.showwarning('Druck läuft','Bitte den aktiven Druckvorgang abwarten. Zum Abbrechen nach dem aktuellen Foto auf „Stoppen“ klicken.')
            return
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()