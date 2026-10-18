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
    name: str = ''
    def __post_init__(self):
        self.name = self.path.name


def prepare_image(item):
    with Image.open(item.path) as src:
        im = ImageOps.exif_transpose(src).convert('RGB')
    if item.rotate:
        im = im.rotate(-item.rotate, expand=True, resample=Image.Resampling.BICUBIC)
    if item.fit == 'Füllen (Beschnitt)':
        im = ImageOps.fit(im, SIZE, method=Image.Resampling.LANCZOS, centering=(.5, .5))
    else:
        im.thumbnail(SIZE, Image.Resampling.LANCZOS)
        bg = Image.new('RGB', SIZE, 'white')
        bg.paste(im, ((SIZE[0]-im.width)//2, (SIZE[1]-im.height)//2))
        im = bg
    for factor, cls in ((item.brightness, ImageEnhance.Brightness), (item.contrast, ImageEnhance.Contrast), (item.saturation, ImageEnhance.Color)):
        if factor != 1:
            im = cls(im).enhance(factor)
    return im


class App:
    def __init__(self, root):
        self.root = root
        root.title('KODAK P210R Studio · 1.0')
        root.geometry('1210x780')
        root.minsize(950, 620)
        self.items = []
        self.selected = None
        self.ui_messages = queue.Queue()
        self.running = False
        self.cancel_flag = threading.Event()
        self.preview_photo = None
        self.refresh_after = None
        self._build()
        root.after(90, self._poll_ui)
        root.protocol('WM_DELETE_WINDOW', self._close)

    def _build(self):
        s = ttk.Style()
        if 'vista' in s.theme_names(): s.theme_use('vista')
        outer = ttk.Frame(self.root, padding=13); outer.pack(fill='both', expand=True)
        top = ttk.Frame(outer); top.pack(fill='x', pady=(0,10))
        ttk.Label(top, text='KODAK P210R Studio', font=('Segoe UI',19,'bold')).pack(side='left')
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
        self.preview = tk.Canvas(right,bg='#25272b',highlightthickness=0,height=365)
        self.preview.pack(fill='both',expand=True,pady=8)
        self.preview.bind('<Configure>',lambda _:self._schedule_preview())
        edit = ttk.LabelFrame(right,text='Ausgewähltes Foto',padding=10); edit.pack(fill='x')
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
        self.start_btn=ttk.Button(bottom,text='Stapel drucken',command=self.start);self.start_btn.pack(side='right',padx=4)
        ttk.Button(bottom,text='Vorschau-JPEG speichern',command=self.export).pack(side='right',padx=4)
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
            for attr,(v,lbl) in self.sliders.items():v.set(getattr(item,attr));lbl.configure(text=f'{int(round(getattr(item,attr)*100))} %')
            self._schedule_preview()

    def _change(self,attr,value):
        if self.running:return
        item=self._current()
        if item:setattr(item,attr,value)
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
            self.preview.create_image(self.preview.winfo_width()//2,self.preview.winfo_height()//2,image=self.preview_photo)
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
        snapshot=[Photo(x.path,uid=x.uid,copies=x.copies,rotate=x.rotate,fit=x.fit,brightness=x.brightness,contrast=x.contrast,saturation=x.saturation) for x in self.items]
        self.running=True;self.cancel_flag.clear()
        self.start_btn.configure(state='disabled');self.stop_btn.configure(state='normal')
        self.status.set('Druck läuft …')
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
                    msg=f'{success} Übertragungen abgeschlossen, {failed} Fehler'+(' · Stapel gestoppt' if stopped else '')
                    self.status.set(msg);self._log(msg+' · Protokolle in '+path)
                    if failed:messagebox.showwarning('Druckstapel',msg+'\nDetails im Protokoll.')
        except queue.Empty:pass
        self.root.after(90,self._poll_ui)

    def _close(self):
        if self.running:
            messagebox.showwarning('Druck läuft','Bitte den aktiven Druckvorgang abwarten. Zum Abbrechen nach dem aktuellen Foto auf „Stoppen“ klicken.')
            return
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()