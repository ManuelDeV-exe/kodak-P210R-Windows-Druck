"""KODAK P210R Studio — local Tkinter frontend using unmodified v2.3 driver."""
import json
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
from PIL import Image, ImageEnhance, ImageOps, ImageTk, ImageDraw

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
    def __post_init__(self):
        self.name = self.path.name


LAYOUTS = ('Ohne Rahmen', 'Foto mit weißem Rand', 'Polaroid 1:1,2', 'Polaroid 1:1,4')
INK = '#233044'
BG = '#eef2f7'
ACCENT = '#4765e9'


def prepare_image(item):
    """Compose the finished 640x1024 JPEG; preserve proven v2.3 wire protocol."""
    with Image.open(item.path) as src:
        im = ImageOps.exif_transpose(src).convert('RGB')
    if item.rotate:
        im = im.rotate(-item.rotate, expand=True, resample=Image.Resampling.BICUBIC)
    for factor, cls in ((item.brightness, ImageEnhance.Brightness),
                        (item.contrast, ImageEnhance.Contrast),
                        (item.saturation, ImageEnhance.Color)):
        if factor != 1:
            im = cls(im).enhance(factor)

    canvas = Image.new('RGB', SIZE, 'white')
    edge = max(0, min(110, int(item.border)))
    if item.layout == 'Ohne Rahmen':
        rect = (0, 0, SIZE[0], SIZE[1])
    elif item.layout == 'Foto mit weißem Rand':
        rect = (edge, edge, SIZE[0] - edge, SIZE[1] - edge)
    else:
        # Polaroid frame: caption stays below the image, no text over photograph.
        top = max(18, edge)
        bottom_space = 190 if item.layout == 'Polaroid 1:1,2' else 255
        # The requested aspect ratio refers to photo inset, not the fixed paper.
        # 1:1.2 or 1:1.4 means inset height = inset width * ratio.
        ratio = 1.2 if item.layout == 'Polaroid 1:1,2' else 1.4
        available_w = SIZE[0] - 2 * top
        available_h = SIZE[1] - top - bottom_space
        iw = min(available_w, int(available_h / ratio))
        ih = round(iw * ratio)
        x = (SIZE[0] - iw) // 2
        rect = (x, top, x + iw, top + ih)
    rw, rh = rect[2]-rect[0], rect[3]-rect[1]
    if rw < 10 or rh < 10:
        raise ValueError('Rand zu groß')
    if item.fit == 'Füllen (Beschnitt)':
        final = ImageOps.fit(im, (rw, rh), method=Image.Resampling.LANCZOS)
    else:
        final = ImageOps.contain(im, (rw, rh), method=Image.Resampling.LANCZOS)
    x = rect[0] + (rw - final.width)//2
    y = rect[1] + (rh - final.height)//2
    canvas.paste(final, (x, y))
    if item.layout.startswith('Polaroid') and item.caption.strip():
        from PIL import ImageFont
        font = None
        for fontname in ('C:/Windows/Fonts/segoepr.ttf','C:/Windows/Fonts/segoesc.ttf',
                         'C:/Windows/Fonts/segoeui.ttf','DejaVuSans.ttf'):
            try:
                font=ImageFont.truetype(fontname, 33)
                break
            except OSError:
                pass
        if font is None:
            font=ImageFont.load_default()
        draw=ImageDraw.Draw(canvas)
        label=' '.join(item.caption.strip().split())
        max_width=SIZE[0]-50
        while len(label)>1 and draw.textbbox((0,0),label,font=font)[2]>max_width:
            label=label[:-2]+'…'
        textbb=draw.textbbox((0,0),label,font=font)
        tw=textbb[2]-textbb[0]
        bottom_start=rect[3]
        text_y=bottom_start + max(8,(SIZE[1]-bottom_start-(textbb[3]-textbb[1]))//2) - textbb[1]
        draw.text(((SIZE[0]-tw)//2,text_y),label,fill=INK,font=font)
    if item.print_rotate:
        canvas=canvas.rotate(180)
    return canvas


class App:
    def __init__(self, root):
        self.root = root
        root.title('KODAK P210R Studio · 1.1')
        root.geometry('1280x880')
        root.minsize(1030, 740)
        self.items = []
        self.selected = None
        self.ui_messages = queue.Queue()
        self.running = False
        self.cancel_flag = threading.Event()
        self.preview_photo = None
        self.refresh_after = None
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
        ttk.Button(top, text='Bilder hinzufügen', command=self.add_files).pack(side='right', padx=3)
        ttk.Button(top, text='Ordner hinzufügen', command=self.add_folder).pack(side='right', padx=3)
        mid = ttk.PanedWindow(outer, orient='horizontal'); mid.pack(fill='both', expand=True)
        left = ttk.Frame(mid, padding=(0,5,10,5)); mid.add(left, weight=2)
        right = ttk.Frame(mid, padding=(10,5,0,5)); mid.add(right, weight=3)
        ttk.Label(left, text='Druckwarteschlange', font=('Segoe UI',12,'bold')).pack(anchor='w')
        table_frame = ttk.Frame(left); table_frame.pack(fill='both', expand=True, pady=7)
        self.tree = ttk.Treeview(table_frame, columns=('copies','status'), show='tree headings', selectmode='browse', height=12)
        self.tree.heading('#0', text='Datei'); self.tree.heading('copies', text='Kopien'); self.tree.heading('status', text='Status')
        self.tree.column('#0', width=275, stretch=True); self.tree.column('copies', width=65, anchor='center', stretch=False)
        self.tree.column('status', width=125, anchor='w', stretch=False)
        bar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview); self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side='left', fill='both', expand=True); bar.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._select)
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
        self.tip_label=ttk.Label(right,text='◀  Abreißstreifen links beim Auswurf · nicht Teil des Druckbilds',foreground='#566783')
        self.tip_label.pack(anchor='w',pady=(0,4))
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
        borderrow=ttk.Frame(edit);borderrow.pack(fill='x',pady=(0,7))
        ttk.Label(borderrow,text='Weißer Rand:').pack(side='left',padx=(0,8))
        self.border_var=tk.IntVar(value=22)
        ttk.Scale(borderrow,from_=0,to=100,variable=self.border_var,command=lambda v:self._change('border',round(float(v)))).pack(side='left',fill='x',expand=True)
        self.border_text=ttk.Label(borderrow,text='22 px',width=7)
        self.border_text.pack(side='left',padx=6)
        self.orientation_var=tk.BooleanVar(value=False)
        ttk.Checkbutton(edit,text='Druckbild um 180° drehen (Abreißstreifen links)',variable=self.orientation_var,
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
        ttk.Button(row2,text='Bearbeitung zurücksetzen',command=self.reset_edits).pack(side='right')
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
        self.poll_var=tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom,text='Statusabfragen (optional)',variable=self.poll_var).pack(side='left',padx=8)
        self.status=tk.StringVar(value='Bereit · Keine Fotos')
        ttk.Label(bottom,textvariable=self.status).pack(side='left',padx=10)
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
                item=Photo(path); self.items.append(item);self.tree.insert('', 'end', iid=item.uid,text=item.name,values=(item.copies,'Wartend'));added+=1
            except Exception as ex:self._log(f'Übersprungen: {path.name}: {ex}')
        if added and self.selected is None:self.tree.selection_set(self.items[0].uid);self._select()
        self.status.set(f'{len(self.items)} Fotos in der Warteschlange')

    def _current(self):
        return next((x for x in self.items if x.uid==self.selected),None)

    def _select(self,_=None):
        selection=self.tree.selection()
        if not selection:return
        self.selected=selection[0];item=self._current()
        if item:
            self.fit_var.set(item.fit);self.copies_var.set(item.copies)
            self.layout_var.set(item.layout);self.caption_var.set(item.caption)
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
        if item:
            item.rotate=0;item.fit='Füllen (Beschnitt)';item.brightness=item.contrast=item.saturation=1
            item.layout='Foto mit weißem Rand';item.caption='';item.border=22;item.print_rotate=False
            self._select()

    def _schedule_preview(self):
        if self.refresh_after:self.root.after_cancel(self.refresh_after)
        self.refresh_after=self.root.after(120,self._render_preview)

    def _render_preview(self):
        self.refresh_after=None
        item=self._current();self.preview.delete('all')
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
            self.preview.create_line(cx-im.width//2-17,cy-im.height//2,cx-im.width//2-17,cy+im.height//2,fill='#f4c271',width=3,dash=(5,4))
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

    def export(self):
        item=self._current()
        if not item:return messagebox.showinfo('Info','Bitte zuerst ein Bild auswählen.')
        path=filedialog.asksaveasfilename(defaultextension='.jpg',filetypes=[('JPEG','*.jpg')],initialfile=item.path.stem+'_p210r.jpg')
        if path:
            try:prepare_image(item).save(path,'JPEG',quality=94,subsampling=0)
            except Exception as ex:messagebox.showerror('Fehler',str(ex))
            else:self._log(f'Bild gespeichert: {path}')

    def start(self):
        if self.running:return
        if not self.items:return messagebox.showinfo('Keine Bilder','Füge zuerst Fotos hinzu.')
        port=self.port.get().strip()
        if not port:return messagebox.showerror('Fehler','Bitte COM-Port eintragen.')
        if not DRIVER.exists():return messagebox.showerror('Fehler','V2.3 Druckroutine fehlt.')
        # Immutable snapshot; edits are disabled while running.
        snapshot=[Photo(x.path,uid=x.uid,copies=x.copies,rotate=x.rotate,fit=x.fit,brightness=x.brightness,contrast=x.contrast,saturation=x.saturation,layout=x.layout,caption=x.caption,border=x.border,print_rotate=x.print_rotate) for x in self.items]
        self.running=True;self.cancel_flag.clear()
        self.start_btn.configure(state='disabled');self.stop_btn.configure(state='normal')
        self.status.set('Druck läuft …')
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
                prepare_image(item).save(target,'JPEG',quality=94,subsampling=0,optimize=False)
                args=[sys.executable,str(DRIVER),'--send','--port',port,'--image',str(target),'--report',str(report)]
                if poll:args.append('--poll')
                self.ui_messages.put(('log',f'{index}/{len(jobs)} → {item.name}, Kopie {copy_num}/{item.copies}'))
                # The v2.3 script remains an external, unmodified subprocess.
                result=subprocess.run(args,cwd=str(BASE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=300)
                try:data=json.loads(report.read_text(encoding='utf-8'))
                except Exception:data={}
                error=data.get('error')
                if result.returncode!=0 or error or data.get('result')=='error':
                    failed+=1;self.ui_messages.put(('tree',(item.uid,'Fehler')))
                    self.ui_messages.put(('log',f'Druckfehler: {error or result.stdout[-800:]}'))
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