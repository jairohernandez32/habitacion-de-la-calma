# -*- coding: utf-8 -*-
"""
RECONEXIÓN – Habitación de la Calma (v8.2)
Con corrección COMPLETA de base de datos para seguimientos
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, re, time, subprocess, webbrowser
from datetime import datetime
import sqlite3
import math

import serial
import serial.tools.list_ports
import random
import platform
from pathlib import Path
from shutil import which

# PIL es opcional
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

# ---------------------- Texto de consentimiento si no hay DOCX ----------------------
CONSENT_FALLBACK = """
CONSENTIMIENTO INFORMADO – RECONEXIÓN: HABITACIÓN DE LA CALMA  

Este documento busca garantizar que el paciente y/o acudiente comprende los objetivos, beneficios, 
riesgos y derechos relacionados con la participación en el programa digital "RECONEXIÓN – Habitación de la Calma",
orientado a apoyo terapéutico en síntomas de ansiedad y/o depresión. Este programa no sustituye la atención médica  
profesional; actúa como complemento.    

1. Datos del usuario    
- Nombre completo: ________________________________    
- Documento de identificación: ____________________    
- Fecha de nacimiento: ____________________________    
- Edad: __________    
- Teléfono de contacto: ___________________________    
- Correo electrónico: _____________________________   
- Acudiente (si menor de edad):  
  • Nombre: ____________________  • Documento: ____________________  • Parentesco: ____________________    

2. Objetivo del programa    
Apoyar la regulación emocional a través de estrategias como: música terapéutica, respiración guiada, exposición a luz  
circadiana controlada, higiene del sueño y educación en hábitos saludables.  

3. Beneficios esperados  
- Disminución de la ansiedad y/o mejoría del estado de ánimo.  
- Mejora en la calidad del sueño y sensación de calma.   
- Desarrollo de herramientas de autorregulación.

4. Riesgos y molestias posibles   
- Molestias por sonidos/luz (cefalea, fotofobia, mareo).  
- Incomodidad transitoria al realizar ejercicios de respiración/relajación.
Si aparece cualquier síntoma adverso, se recomienda detener la sesión y consultar a un profesional de la salud.  

5. Confidencialidad y manejo de datos  
Los datos se almacenan localmente con fines terapéuticos y de seguimiento. No se comparten con terceros sin autorización.
El usuario puede solicitar la eliminación de sus registros cuando lo considere.  

6. Voluntariedad    
La participación es voluntaria. El usuario puede retirarse en cualquier momento sin penalización. 

7. Consentimiento    
Declaro que he leído y comprendido la información anterior y que doy mi consentimiento para participar.    
Firma del participante: _______________________    Fecha: ____________    
Firma del acudiente (si aplica): _______________   Parentesco: ________  
"""

def encontrar_puerto_arduino():
    """Encuentra y retorna el puerto COM donde está conectado un Arduino."""
    puertos = serial.tools.list_ports.comports()
        
    for puerto in puertos:
        if 'Arduino' in puerto.description:
            return puerto.device
        if '2341' in puerto.hwid or '2A03' in puerto.hwid:
            return puerto.device
        
    return None

def load_consent_text(base_path: str) -> str:
    path = os.path.join(base_path, "CONSENTIMIENTO INFORMADO.docx")
    if not os.path.exists(path):
        return CONSENT_FALLBACK
    try:
        import docx
        d = docx.Document(path)
        parts = [p.text.strip() for p in d.paragraphs if p.text.strip()]
        return "\n\n".join(parts) or CONSENT_FALLBACK
    except Exception:
        return CONSENT_FALLBACK

# Ejecutar la función e imprimir el resultado
puerto_arduino = encontrar_puerto_arduino()
if puerto_arduino:
    arduino = serial.Serial(puerto_arduino, 9600, timeout=1)
else:
    arduino = None
    print("No se encontró Arduino")

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RECONEXIÓN –HABITACIÓN DE LA CALMA")
        self.root.geometry("1200x800")
        self.root.minsize(1100, 750)
        self.color_terapia = None

        # Paleta de colores
        self.COL_BG = "#F7FAF7"
        self.COL_CARD = "#FFFFFF"
        self.COL_CARD2 = "#F1F5F9"
        self.COL_TEXT = "#111827"
        self.COL_MUTED = "#4B5563"
        self.COL_ACCENT = "#0EA5A0"
        self.COL_ACCENT2 = "#60A5FA"
        self.COL_BTN = "#0EA5A0"
        self.COL_BTN_TX = "#ffffff"
        self.COL_BTN_H = "#0b8d87"
        self.COL_INPUT = "#FFFFFF"
        self.COL_INPUT_TX = "#111827"
        self.COL_INPUT_B = "#94A3B8"
        self.COL_HEADER = "#E8FFF6"
        self.COL_BORDER = "#D1FAE5"
        self.COL_SHADOW = "#E5E7EB"
        self.root.configure(bg=self.COL_BG)

        # Estilo ttk
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except:
            pass

        # Rutas e imágenes
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.logo_tk = None
        self.relax_base, self.relax_tk = None, None
        self._load_images()

        # Estado de evaluación/sesión
        self.current = 0
        self.answers = {}
        self.plan_text = ""
        self.plan_playlists = []
        self.session_minutes = 15
        self.demographics = {}
        self.profile_infer = []
        self.modules_selected = []

        # Datos maestros
        self._setup_questions()
        self._setup_playlists()
        self._setup_rules()
        
        # Base de datos para seguimientos - INICIALIZAR PRIMERO
        self._setup_database()

        self._home()

    def _get_nombre_limpio(self, paciente_raw):
        """Extrae solo el nombre del paciente del formato 'nombre - genero - edad años'"""
        if " - " in paciente_raw:
            return paciente_raw.split(" - ")[0].strip()
        return paciente_raw.strip()

    # -------------------- Utilidades de UI --------------------
    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=self.COL_BG)

    def _lang_alert(self):
        messagebox.showinfo("Idiomas", "Por ahora solo Español.")

    def _card(self, parent, relx, rely, rw, rh):
        shadow = tk.Frame(parent, bg=self.COL_SHADOW)
        shadow.place(relx=relx+0.005, rely=rely+0.005, anchor="center", relwidth=rw, relheight=rh)
        card = tk.Frame(parent, bg=self.COL_CARD,
                        highlightbackground=self.COL_BORDER, highlightthickness=1)
        card.place(relx=relx, rely=rely, anchor="center", relwidth=rw, relheight=rh)
        return card

    def _button(self, parent, text, command, primary=True, state="normal"):
        bg = self.COL_BTN if primary else self.COL_CARD2
        fg = self.COL_BTN_TX if primary else self.COL_TEXT
        hov = self.COL_BTN_H if primary else self.COL_ACCENT2
        btn = tk.Button(
            parent, text=text, command=command, font=("Segoe UI", 11, "bold"),
            bg=bg, fg=fg, activeforeground=fg, relief="flat", bd=0, padx=20, pady=12,
            cursor="hand2", state=state
        )
        btn.bind("<Enter>", lambda e: btn.configure(
            bg=hov if (primary and state == "normal") else (self.COL_ACCENT2 if state == "normal" else bg)))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    def _topbar(self, title="RECONEXIÓN – HABITACIÓN DE LA CALMA"):
        top = tk.Frame(self.root, bg=self.COL_BG, height=64)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        tk.Label(top, text=title, font=("Segoe UI", 18, "bold"),
                 bg=self.COL_BG, fg=self.COL_TEXT).pack(side="left", padx=18, pady=10)
        right = tk.Frame(top, bg=self.COL_BG)
        right.pack(side="right", padx=12)
        tk.Button(right, text="🌐 Español", font=("Segoe UI", 10, "bold"),
                  bg="#E5E7EB", fg=self.COL_TEXT, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._lang_alert).grid(row=0, column=0, padx=6)

    def _section(self, parent, title):
        wrap = tk.Frame(parent, bg=self.COL_CARD,
                        highlightbackground=self.COL_BORDER, highlightthickness=1)
        wrap.pack(fill="x", padx=26, pady=10)
        head = tk.Frame(wrap, bg=self.COL_HEADER,
                        highlightbackground=self.COL_BORDER, highlightthickness=1)
        head.pack(fill="x")
        tk.Label(head, text=title, font=("Segoe UI", 12, "bold"),
                 bg=self.COL_HEADER, fg=self.COL_TEXT).pack(anchor="w", padx=10, pady=6)
        body = tk.Frame(wrap, bg=self.COL_CARD)
        body.pack(fill="x", padx=12, pady=10)
        return body

    # -------------------- Carga de imágenes --------------------
    def _load_images(self):
        icon_loaded = False
        if Image is not None:
            possible_icons = ["logo.jpeg", "logo.jpg", "logo.png", "icon.jpeg", "icon.jpg", "icon.png"]
            for icon_name in possible_icons:
                icon_path = os.path.join(self.base_path, icon_name)
                if os.path.exists(icon_path):
                    try:
                        icon_image = Image.open(icon_path)
                        icon_photo = ImageTk.PhotoImage(icon_image)
                        self.root.iconphoto(False, icon_photo)
                        print(f"Icono de ventana cargado: {icon_path}")
                        icon_loaded = True
                        break
                    except Exception as e:
                        print(f"Error cargando icono {icon_path}: {e}")
        
        if not icon_loaded:
            print("No se pudo cargar el icono de ventana")

        if Image is None:
            return
        for stem in ("logo",):
            for ext in ("png", "jpg", "jpeg"):
                for base in (self.base_path, os.path.join(self.base_path, "assets")):
                    p = os.path.join(base, f"{stem}.{ext}")
                    if os.path.exists(p):
                        try:
                            img = Image.open(p).convert("RGBA").resize((128, 128))
                            self.logo_tk = ImageTk.PhotoImage(img)
                            raise StopIteration
                        except Exception:
                            pass
        for stem in ("relajante", "relax", "nature"):
            for ext in ("png", "jpg", "jpeg"):
                p = os.path.join(self.base_path, f"{stem}.{ext}")
                if os.path.exists(p):
                    try:
                        base = Image.open(p).convert("RGBA")
                        w, h = base.size
                        scale = 560 / max(w, h)
                        base = base.resize((int(w*scale), int(h*scale)))
                        self.relax_base = base
                        self.relax_tk = ImageTk.PhotoImage(base)
                        break
                    except Exception:
                        pass

    # ------------------------------- Pantalla de inicio -------------------------------
    def _home(self):
        self._clear()
        self._topbar()
        card = self._card(self.root, 0.5, 0.53, 0.78, 0.76)
        if self.logo_tk:
            tk.Label(card, image=self.logo_tk, bg=self.COL_CARD).pack(pady=(18, 10))
        tk.Label(card, text="HABITACIÓN", font=("Segoe UI", 32, "bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).pack()
        tk.Label(card, text="Terapia de la Calma", font=("Segoe UI", 18, "italic"),
                 bg=self.COL_CARD, fg=self.COL_ACCENT).pack()
        tk.Frame(card, bg=self.COL_ACCENT2, height=2).pack(fill="x", padx=60, pady=16)
        intro = ("Eres el proyecto más importante en el que puedes trabajar. ")
        tk.Label(card, text=intro, font=("Segoe UI", 13), bg=self.COL_CARD,
                 fg=self.COL_MUTED, justify="center", wraplength=900).pack(pady=6, padx=14)
        self._button(card, "✨ Iniciar Programa", self._programa).pack(pady=16)

    # ---------------------- Selección de programa ----------------------
    def _programa(self):
        self._clear()
        self._topbar("Programa Terapéutico")
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.78)
        tk.Label(card, text="Programa Terapéutico",
                 font=("Segoe UI", 26, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(26, 14))
        btns = tk.Frame(card, bg=self.COL_CARD); btns.pack(pady=6)
        
        # Fila 1: Terapias
        self._button(btns, "🕒  Terapia Inicial", self._consent, primary=True).grid(row=0, column=0, padx=18, pady=10)
        self._button(btns, "📊  Terapia de Seguimiento", self._seguimiento_terapia, primary=True).grid(row=0, column=1, padx=18, pady=10)

        # Fila 2: Base de datos
        self._button(btns, "🗃️  Base de Datos", self._visor_base_datos, primary=True).grid(row=1, column=0, columnspan=2, padx=18, pady=10)

        tk.Label(card, text="Selecciona una opción para continuar",
                 font=("Segoe UI", 12), bg=self.COL_CARD, fg=self.COL_MUTED).pack(pady=18)
        self._button(card, "← Volver", self._home, primary=False).pack(pady=(4, 18))

    # ------------------------------- Base de datos para seguimientos -------------------------------
    def _setup_database(self):
        """Crea la base de datos y tabla para seguimientos si no existen"""
        # Asegurar que la base de datos se cree en el directorio actual
        db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
        print(f"Base de datos ubicada en: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabla para terapia inicial
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS terapia_inicial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paciente_id TEXT,
                paciente_nombre TEXT,
                genero TEXT,
                edad INTEGER,
                tipo_documento TEXT,
                perfil_sugerido TEXT,
                modulos_recomendados TEXT,
                playlists TEXT,
                duracion_sesion TEXT,
                sensacion_post_sesion TEXT,
                mas_valioso TEXT,
                recursos_implementados TEXT,
                comentarios_finales TEXT
            )
        ''')
        
        # Tabla para terapia de seguimiento - CORREGIDA COMPLETAMENTE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seguimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paciente_id TEXT,
                paciente_nombre TEXT,
                estado_3dias TEXT,
                sueño_semana TEXT,
                alimentacion_semana TEXT,
                sobre_pensamiento TEXT,
                emociones_frecuentes TEXT,
                sensacion_post_sesion TEXT,
                mas_valioso TEXT,
                recursos_implementados TEXT,
                playlists_utilizadas TEXT,
                recomendaciones_terapia TEXT
            )
        ''')
        
        # VERIFICAR Y AGREGAR COLUMNAS FALTANTES SI ES NECESARIO
        try:
            cursor.execute("PRAGMA table_info(seguimientos)")
            columnas = cursor.fetchall()
            columnas_nombres = [col[1] for col in columnas]
            
            # Verificar y agregar columnas faltantes
            if 'playlists_utilizadas' not in columnas_nombres:
                print("Agregando columna faltante: playlists_utilizadas")
                cursor.execute('ALTER TABLE seguimientos ADD COLUMN playlists_utilizadas TEXT')
            
            if 'recomendaciones_terapia' not in columnas_nombres:
                print("Agregando columna faltante: recomendaciones_terapia")
                cursor.execute('ALTER TABLE seguimientos ADD COLUMN recomendaciones_terapia TEXT')
                
        except Exception as e:
            print(f"Error verificando estructura de tabla: {e}")
        
        conn.commit()
        conn.close()
        print("Base de datos inicializada y verificada correctamente")

    # ------------------------------- Visor de Base de Datos MEJORADO -------------------------------
    def _visor_base_datos(self):
        """Muestra los seguimientos guardados en la base de datos con buscador"""
        try:
            db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
            print(f"Accediendo a base de datos en: {db_path}")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtener datos de ambas tablas
            cursor.execute('''
                SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                       genero as info_extra, perfil_sugerido as estado
                FROM terapia_inicial 
                UNION ALL
                SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                       estado_3dias as info_extra, emociones_frecuentes as estado
                FROM seguimientos
                ORDER BY fecha DESC
            ''')
            registros = cursor.fetchall()
            
            conn.close()
            
            # Procesar registros para mostrar nombres limpios
            registros_procesados = []
            for registro in registros:
                tipo, id_reg, fecha, paciente_id, paciente_nombre, info_extra, estado = registro
                # Limpiar el nombre del paciente
                nombre_limpio = self._get_nombre_limpio(paciente_nombre)
                registros_procesados.append((tipo, id_reg, fecha, paciente_id, nombre_limpio, info_extra, estado))
            
            # Crear ventana para mostrar los datos
            ventana = tk.Toplevel(self.root)
            ventana.title("Base de Datos - Todas las Terapias")
            ventana.geometry("1200x700")
            ventana.configure(bg=self.COL_BG)
            
            tk.Label(ventana, text="📊 Base de Datos - Registros de Terapias", 
                     font=("Segoe UI", 16, "bold"), bg=self.COL_BG, fg=self.COL_TEXT).pack(pady=10)
            
            # Frame de búsqueda
            search_frame = tk.Frame(ventana, bg=self.COL_BG)
            search_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(search_frame, text="Buscar:", font=("Segoe UI", 10, "bold"),
                     bg=self.COL_BG, fg=self.COL_TEXT).pack(side="left", padx=5)
            
            search_var = tk.StringVar()
            search_entry = tk.Entry(search_frame, textvariable=search_var, width=30,
                                   font=("Segoe UI", 10), relief="solid", bd=1)
            search_entry.pack(side="left", padx=5)
            
            search_type = tk.StringVar(value="paciente_id")
            tk.Radiobutton(search_frame, text="Por ID", variable=search_type, value="paciente_id",
                          bg=self.COL_BG, fg=self.COL_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=5)
            tk.Radiobutton(search_frame, text="Por Nombre", variable=search_type, value="paciente_nombre",
                          bg=self.COL_BG, fg=self.COL_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=5)
            
            tipo_consulta = tk.StringVar(value="todos")
            tk.Label(search_frame, text="Tipo:", font=("Segoe UI", 10, "bold"),
                     bg=self.COL_BG, fg=self.COL_TEXT).pack(side="left", padx=(20,5))
            tk.Radiobutton(search_frame, text="Todos", variable=tipo_consulta, value="todos",
                          bg=self.COL_BG, fg=self.COL_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=5)
            tk.Radiobutton(search_frame, text="Inicial", variable=tipo_consulta, value="inicial",
                          bg=self.COL_BG, fg=self.COL_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=5)
            tk.Radiobutton(search_frame, text="Seguimiento", variable=tipo_consulta, value="seguimiento",
                          bg=self.COL_BG, fg=self.COL_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=5)
            
            def buscar_registros():
                texto_busqueda = search_var.get().strip().lower()
                tipo_busqueda = search_type.get()
                tipo_filtro = tipo_consulta.get()
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                if tipo_filtro == "todos":
                    if not texto_busqueda:
                        cursor.execute('''
                            SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                   genero as info_extra, perfil_sugerido as estado
                            FROM terapia_inicial 
                            UNION ALL
                            SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                   estado_3dias as info_extra, emociones_frecuentes as estado
                            FROM seguimientos
                            ORDER BY fecha DESC
                        ''')
                    else:
                        if tipo_busqueda == "paciente_id":
                            cursor.execute('''
                                SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                       genero as info_extra, perfil_sugerido as estado
                                FROM terapia_inicial 
                                WHERE LOWER(paciente_id) LIKE ?
                                UNION ALL
                                SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                       estado_3dias as info_extra, emociones_frecuentes as estado
                                FROM seguimientos
                                WHERE LOWER(paciente_id) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%', f'%{texto_busqueda}%'))
                        else:
                            cursor.execute('''
                                SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                       genero as info_extra, perfil_sugerido as estado
                                FROM terapia_inicial 
                                WHERE LOWER(paciente_nombre) LIKE ?
                                UNION ALL
                                SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                       estado_3dias as info_extra, emociones_frecuentes as estado
                                FROM seguimientos
                                WHERE LOWER(paciente_nombre) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%', f'%{texto_busqueda}%'))
                elif tipo_filtro == "inicial":
                    if not texto_busqueda:
                        cursor.execute('''
                            SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                   genero as info_extra, perfil_sugerido as estado
                            FROM terapia_inicial 
                            ORDER BY fecha DESC
                        ''')
                    else:
                        if tipo_busqueda == "paciente_id":
                            cursor.execute('''
                                SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                       genero as info_extra, perfil_sugerido as estado
                                FROM terapia_inicial 
                                WHERE LOWER(paciente_id) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%',))
                        else:
                            cursor.execute('''
                                SELECT 'Inicial' as tipo, id, fecha, paciente_id, paciente_nombre, 
                                       genero as info_extra, perfil_sugerido as estado
                                FROM terapia_inicial 
                                WHERE LOWER(paciente_nombre) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%',))
                else:  # seguimiento
                    if not texto_busqueda:
                        cursor.execute('''
                            SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                   estado_3dias as info_extra, emociones_frecuentes as estado
                            FROM seguimientos
                            ORDER BY fecha DESC
                        ''')
                    else:
                        if tipo_busqueda == "paciente_id":
                            cursor.execute('''
                                SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                       estado_3dias as info_extra, emociones_frecuentes as estado
                                FROM seguimientos
                                WHERE LOWER(paciente_id) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%',))
                        else:
                            cursor.execute('''
                                SELECT 'Seguimiento' as tipo, id, fecha, paciente_id, paciente_nombre,
                                       estado_3dias as info_extra, emociones_frecuentes as estado
                                FROM seguimientos
                                WHERE LOWER(paciente_nombre) LIKE ?
                                ORDER BY fecha DESC
                            ''', (f'%{texto_busqueda}%',))
                
                nuevos_registros = cursor.fetchall()
                conn.close()
                
                # Procesar nombres limpios para mostrar
                registros_procesados = []
                for registro in nuevos_registros:
                    tipo, id_reg, fecha, paciente_id, paciente_nombre, info_extra, estado = registro
                    nombre_limpio = self._get_nombre_limpio(paciente_nombre)
                    registros_procesados.append((tipo, id_reg, fecha, paciente_id, nombre_limpio, info_extra, estado))
                
                actualizar_tabla(registros_procesados)
            
            def actualizar_tabla(registros_mostrar):
                # Limpiar tabla
                for item in tree.get_children():
                    tree.delete(item)
                
                # Agregar nuevos datos CON NOMBRES LIMPIOS
                for registro in registros_mostrar:
                    tree.insert("", "end", values=registro)
                
                # Actualizar contador
                contador_label.config(text=f"Total de registros: {len(registros_mostrar)}")
            
            self._button(search_frame, "🔍 Buscar", buscar_registros, primary=True).pack(side="left", padx=5)
            self._button(search_frame, "🔄 Mostrar Todos", lambda: actualizar_tabla(registros_procesados), primary=False).pack(side="left", padx=5)
            
            # Frame con scroll
            frame = tk.Frame(ventana, bg=self.COL_BG)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Treeview para mostrar datos en tabla
            columns = ("Tipo", "ID", "Fecha", "Paciente ID", "Paciente Nombre", "Info Extra", "Estado")
            
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
            
            # Configurar columnas
            column_widths = {
                "Tipo": 80, "ID": 50, "Fecha": 120, "Paciente ID": 100, 
                "Paciente Nombre": 150, "Info Extra": 150, "Estado": 200
            }
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=column_widths.get(col, 100))
            
            # Agregar datos iniciales CON NOMBRES LIMPIOS
            for registro in registros_procesados:
                tree.insert("", "end", values=registro)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Botones de acción
            btn_frame = tk.Frame(ventana, bg=self.COL_BG)
            btn_frame.pack(pady=10)
            
            self._button(btn_frame, "📊 Ver Detalles", lambda: self._ver_detalle_completo(tree), primary=True).pack(side="left", padx=5)
            self._button(btn_frame, "🗑️ Eliminar Registro", lambda: self._eliminar_registro(tree), primary=False).pack(side="left", padx=5)
           
            self._button(btn_frame, "❌ Cerrar", ventana.destroy, primary=False).pack(side="left", padx=5)
            
            contador_label = tk.Label(ventana, text=f"Total de registros: {len(registros_procesados)}", 
                         font=("Segoe UI", 10), bg=self.COL_BG, fg=self.COL_MUTED)
            contador_label.pack(pady=5)
            
            # Configurar búsqueda en tiempo real
            def on_search_change(*args):
                ventana.after(500, buscar_registros)
            
            search_var.trace_add("write", on_search_change)
            tipo_consulta.trace_add("write", lambda *args: buscar_registros())
                         
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la base de datos: {str(e)}")

    def _ver_detalle_completo(self, tree):
        """Muestra los detalles completos de un registro seleccionado"""
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor selecciona un registro de la tabla")
            return
            
        item = tree.item(seleccion[0])
        valores = item['values']
        tipo_registro = valores[0]
        id_registro = valores[1]
        
        try:
            db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if tipo_registro == "Inicial":
                cursor.execute('SELECT * FROM terapia_inicial WHERE id = ?', (id_registro,))
            else:
                cursor.execute('SELECT * FROM seguimientos WHERE id = ?', (id_registro,))
                
            registro = cursor.fetchone()
            conn.close()
            
            if registro:
                self._mostrar_detalles_registro(tipo_registro, registro)
                         
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el detalle: {str(e)}")

    def _eliminar_registro(self, tree):
        """Elimina un registro seleccionado de la base de datos"""
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor selecciona un registro de la tabla")
            return
            
        item = tree.item(seleccion[0])
        valores = item['values']
        tipo_registro = valores[0]
        id_registro = valores[1]
        nombre_paciente = valores[4]
        
        # Confirmar eliminación
        respuesta = messagebox.askyesno(
            "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar el registro de {nombre_paciente}?\n\n"
            f"Tipo: {tipo_registro}\nID: {id_registro}\n\n"
            "Esta acción no se puede deshacer."
        )
        
        if not respuesta:
            return
            
        try:
            db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if tipo_registro == "Inicial":
                cursor.execute('DELETE FROM terapia_inicial WHERE id = ?', (id_registro,))
            else:
                cursor.execute('DELETE FROM seguimientos WHERE id = ?', (id_registro,))
                
            conn.commit()
            conn.close()
            
            # Eliminar de la vista
            tree.delete(seleccion[0])
            
            messagebox.showinfo("Éxito", "Registro eliminado correctamente")
            
            # Actualizar contador
            contador_actual = len(tree.get_children())
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and "Total de registros:" in child.cget("text"):
                            child.config(text=f"Total de registros: {contador_actual}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el registro: {str(e)}")

    def _mostrar_detalles_registro(self, tipo, registro):
        """Muestra ventana con detalles completos del registro"""
        detalle_ventana = tk.Toplevel(self.root)
        detalle_ventana.title(f"Detalles {tipo} - ID: {registro[0]}")
        detalle_ventana.geometry("800x600")
        detalle_ventana.configure(bg=self.COL_BG)
        
        # Frame con scroll
        frame = tk.Frame(detalle_ventana, bg=self.COL_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(frame, bg=self.COL_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.COL_BG)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        if tipo == "Inicial":
            campos = [
                ("ID", registro[0]),
                ("Fecha", registro[1]),
                ("ID Paciente", registro[2]),
                ("Nombre Paciente", self._get_nombre_limpio(registro[3])),  # NOMBRE LIMPIO
                ("Género", registro[4]),
                ("Edad", registro[5]),
                ("Tipo Documento", registro[6]),
                ("Perfil Sugerido", registro[7]),
                ("Módulos Recomendados", registro[8]),
                ("Playlists", registro[9]),
                ("Duración Sesión", registro[10]),
                ("Sensación Post-Sesión", registro[11]),
                ("Lo más valioso", registro[12]),
                ("Recursos Implementados", registro[13]),
                ("Comentarios Finales", registro[14])
            ]
        else:
            campos = [
                ("ID", registro[0]),
                ("Fecha", registro[1]),
                ("ID Paciente", registro[2]),
                ("Nombre Paciente", self._get_nombre_limpio(registro[3])),  # NOMBRE LIMPIO
                ("Estado últimos 3 días", registro[4]),
                ("Sueño última semana", registro[5]),
                ("Alimentación", registro[6]),
                ("Sobre pensamiento", registro[7]),
                ("Emociones frecuentes", registro[8]),
                ("Sensación post-sesión", registro[9]),
                ("Lo más valioso", registro[10]),
                ("Recursos implementados", registro[11]),
                ("Playlists utilizadas", registro[12] if len(registro) > 12 else "No especificado"),
                ("Recomendaciones terapia", registro[13] if len(registro) > 13 else "No especificado")
            ]
        
        for i, (campo, valor) in enumerate(campos):
            tk.Label(scrollable_frame, text=f"{campo}:", font=("Segoe UI", 10, "bold"), 
                     bg=self.COL_BG, fg=self.COL_TEXT, anchor="w").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            tk.Label(scrollable_frame, text=str(valor), font=("Segoe UI", 10), 
                     bg=self.COL_BG, fg=self.COL_MUTED, anchor="w", wraplength=600).grid(row=i, column=1, sticky="w", padx=5, pady=2)
        
        # Botón cerrar
        tk.Button(detalle_ventana, text="Cerrar", command=detalle_ventana.destroy,
                 font=("Segoe UI", 10), bg=self.COL_BTN, fg="white").pack(pady=10)

    def _exportar_csv_completo(self):
        """Exporta todos los datos a CSV"""
        try:
            from datetime import datetime
            filename = f"terapias_completo_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtener datos de ambas tablas
            cursor.execute('''
                SELECT 'Inicial' as tipo, * FROM terapia_inicial 
                UNION ALL
                SELECT 'Seguimiento' as tipo, * FROM seguimientos
            ''')
            registros = cursor.fetchall()
            conn.close()
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Escribir encabezados
                f.write("Tipo,ID,Fecha,Paciente_ID,Paciente_Nombre,Info_Extra1,Info_Extra2,Info_Extra3,Info_Extra4,Info_Extra5,Info_Extra6,Info_Extra7,Info_Extra8,Info_Extra9,Info_Extra10\n")
                
                # Escribir datos
                for registro in registros:
                    linea = ','.join(f'"{str(campo)}"' for campo in registro)
                    f.write(linea + '\n')
            
            messagebox.showinfo("Éxito", f"Datos exportados a: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {str(e)}")

    # ------------------------------- TERAPIA DE SEGUIMIENTO MEJORADA -------------------------------
    def _seguimiento_terapia(self):
        """Pantalla principal de terapia de seguimiento - Primera parte"""
        self._clear()
        self._topbar("Terapia de Seguimiento - Parte 1")
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.78)
        
        tk.Label(card, text="📊 Terapia de Seguimiento - Parte 1", 
                 font=("Segoe UI", 26, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(26, 14))
        
        tk.Label(card, text="Primero ingresa tus datos básicos y responde las primeras preguntas:",
                 font=("Segoe UI", 11), bg=self.COL_CARD, fg=self.COL_MUTED).pack(anchor="w", padx=20, pady=(5, 20))
        
        # Botón para iniciar el cuestionario de seguimiento (primera parte)
        self._button(card, "🧠 Iniciar Datos y Cuestionario", self._datos_seguimiento).pack(pady=20)
        
        # Botones de acción
        action_frame = tk.Frame(card, bg=self.COL_CARD)
        action_frame.pack(pady=20)
        
        self._button(action_frame, "← Volver al Menú Principal", self._programa, primary=False).pack(side="left", padx=10)

    def _datos_seguimiento(self):
        """Pantalla para ingresar datos demográficos en seguimiento"""
        self._clear()
        self._topbar("Datos para Seguimiento")
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)
        
        tk.Label(card, text="Datos del Paciente - Seguimiento",
                 font=("Segoe UI", 22, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(16, 6))
        
        def val_letras(P): return re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]*", P or "") is not None
        def val_digs(P):   return re.fullmatch(r"[0-9]*", P or "") is not None
        v_letras = (self.root.register(val_letras), '%P')
        v_digs   = (self.root.register(val_digs), '%P')

        # Datos básicos del paciente
        g1 = self._section(card, "Identificación del Paciente")
        
        row1 = tk.Frame(g1, bg=self.COL_CARD); row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Nombre completo:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=15, anchor="w").pack(side="left")
        self.seg_nombre = tk.Entry(row1, validate="key", validatecommand=v_letras,
                                   bg=self.COL_INPUT, fg=self.COL_INPUT_TX, font=("Segoe UI", 11),
                                   relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B)
        self.seg_nombre.pack(side="left", fill="x", expand=True, padx=(8, 0))
        
        # --- Validaciones ---
        vcmd_doc = self.root.register(lambda P: P.isdigit() and len(P) <= 10 or P == "")
        vcmd_edad = self.root.register(lambda P: P.isdigit() and 0 <= int(P) <= 99 if P else True)

        # --- Campo N° documento ---
        row2 = tk.Frame(g1, bg=self.COL_CARD); row2.pack(fill="x", pady=4)
        tk.Label(row2, text="N° documento:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                width=15, anchor="w").pack(side="left")

        self.seg_documento = tk.Entry(
            row2,
            validate="key",
            validatecommand=(vcmd_doc, "%P"),
            bg=self.COL_INPUT,
            fg=self.COL_INPUT_TX,
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.COL_INPUT_B
        )
        self.seg_documento.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # --- Variable para Edad ---
        self.seg_edad_var = tk.StringVar()

        # --- Campo Edad ---
        row3 = tk.Frame(g1, bg=self.COL_CARD); row3.pack(fill="x", pady=4)
        tk.Label(
            row3,
            text="Edad:",
            bg=self.COL_CARD,
            fg=self.COL_TEXT,
            font=("Segoe UI", 11),
            width=15,
            anchor="w"
        ).pack(side="left")

        self.seg_edad = tk.Entry(
            row3,
            textvariable=self.seg_edad_var,
            width=10,
            validate="key",
            validatecommand=(self.root.register(lambda P: P.isdigit() or P == ""), "%P"),
            bg=self.COL_INPUT,
            fg=self.COL_INPUT_TX,
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.COL_INPUT_B
        )
        self.seg_edad.pack(side="left", padx=(8, 0))

        # --- Función para limitar la edad entre 0 y 99 ---
        def limitar_edad(*_):
            try:
                edad = int(self.seg_edad_var.get())
            except:
                return

            if edad < 0:
                self.seg_edad_var.set("0")
            elif edad > 99:
                self.seg_edad_var.set("99")

        # --- Enlazar evento ---
        self.seg_edad_var.trace_add("write", limitar_edad)


        # --- Campo Género ---
        tk.Label(row3, text="Género:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=10, anchor="w").pack(side="left", padx=(20,0))
        self.seg_genero = tk.StringVar(value="")
        genero_frame = tk.Frame(row3, bg=self.COL_CARD)
        genero_frame.pack(side="left", fill="x", expand=True)
        for opt in ["Masculino", "Femenino", "No binario"]:
            tk.Radiobutton(genero_frame, text=opt, value=opt, variable=self.seg_genero,
                           bg=self.COL_CARD, fg=self.COL_TEXT, selectcolor=self.COL_HEADER,
                           font=("Segoe UI", 10)).pack(side="left", padx=10)

        action = tk.Frame(card, bg=self.COL_CARD); action.pack(pady=10)
        self._button(action, "Continuar a Preguntas →", self._validar_datos_seguimiento).pack(side="left", padx=8)
        self._button(action, "← Volver", self._seguimiento_terapia, primary=False).pack(side="left", padx=8)

    def _validar_datos_seguimiento(self):
        """Valida los datos ingresados antes de continuar a las preguntas"""
        nombre = self.seg_nombre.get().strip()
        documento = self.seg_documento.get().strip()
        edad = self.seg_edad.get().strip()
        genero = self.seg_genero.get().strip()
        
        if not nombre:
            messagebox.showerror("Campo requerido", "Ingresa el nombre completo.")
            return
        
        if not documento or not documento.isdigit():
            messagebox.showerror("Campo requerido", "Ingresa un número de documento válido.")
            return
            
        if not edad or not edad.isdigit():
            messagebox.showerror("Campo requerido", "Ingresa una edad válida.")
            return
            
        if not genero:
            messagebox.showerror("Campo requerido", "Selecciona el género.")
            return
        
        # Guardar datos en demographics para uso posterior
        self.demographics = {
            "nombre": nombre,
            "num_doc_pac": documento,
            "edad": int(edad),
            "genero": genero
        }
        
        # Inicializar respuestas de seguimiento
        self.seguimiento_respuestas = {
            'estado_3dias': tk.StringVar(),
            'sueño_semana': tk.StringVar(),
            'alimentacion_semana': tk.StringVar(),
            'sobre_pensamiento': tk.StringVar(),
            'emociones_frecuentes': [],
            'sensacion_post_sesion': "",
            'mas_valioso': "",
            'recursos_implementados': tk.StringVar()
        }
        
        self._cuestionario_seguimiento_parte1()

    def _cuestionario_seguimiento_parte1(self):
        """Primera parte del cuestionario de seguimiento (5 primeras preguntas)"""
        self._clear()
        self._topbar("Cuestionario de Seguimiento - Parte 1")
        
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)
        
        # Información del paciente
        info_frame = tk.Frame(card, bg=self.COL_CARD)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(info_frame, text=f"Paciente: {self.demographics.get('nombre', '')} - Doc: {self.demographics.get('num_doc_pac', '')}",
                 font=("Segoe UI", 12, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(anchor="w")
        
        tk.Label(info_frame, text="Responde las siguientes preguntas sobre tu estado en la última semana:",
                 font=("Segoe UI", 11), bg=self.COL_CARD, fg=self.COL_MUTED).pack(anchor="w", pady=(5, 0))
        
        # Frame con scroll para las primeras 5 preguntas
        canvas = tk.Canvas(card, bg=self.COL_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.COL_CARD)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Pregunta 1: Estado últimos 3 días
        q1_frame = self._section(scrollable_frame, "1. ¿Cómo te has sentido en los últimos 3 días?")
        opciones = ["Muy bien", "Bien", "Ni bien ni mal", "Mal"]
        for opcion in opciones:
            tk.Radiobutton(q1_frame, text=opcion, variable=self.seguimiento_respuestas['estado_3dias'],
                          value=opcion, bg=self.COL_CARD, fg=self.COL_TEXT, 
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11)).pack(anchor="w", pady=2)
        
        # Pregunta 2: Sueño última semana
        q2_frame = self._section(scrollable_frame, "2. ¿Has dormido bien en la última semana?")
        for opcion in opciones:
            tk.Radiobutton(q2_frame, text=opcion, variable=self.seguimiento_respuestas['sueño_semana'],
                          value=opcion, bg=self.COL_CARD, fg=self.COL_TEXT,
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11)).pack(anchor="w", pady=2)
        
        # Pregunta 3: Alimentación
        q3_frame = self._section(scrollable_frame, "3. ¿Te has alimentado bien en la última semana?")
        for opcion in opciones:
            tk.Radiobutton(q3_frame, text=opcion, variable=self.seguimiento_respuestas['alimentacion_semana'],
                          value=opcion, bg=self.COL_CARD, fg=self.COL_TEXT,
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11)).pack(anchor="w", pady=2)
        
        # Pregunta 4: Sobre pensamiento
        q4_frame = self._section(scrollable_frame, "4. ¿Has sobre pensado mucho en la última semana?")
        opciones_sobrepensar = ["Sí", "No", "Regular"]
        for opcion in opciones_sobrepensar:
            tk.Radiobutton(q4_frame, text=opcion, variable=self.seguimiento_respuestas['sobre_pensamiento'],
                          value=opcion, bg=self.COL_CARD, fg=self.COL_TEXT,
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11)).pack(anchor="w", pady=2)
        
        # Pregunta 5: Emociones frecuentes (múltiple selección)
        q5_frame = self._section(scrollable_frame, "5. ¿Cuáles emociones aparecen con más frecuencia en la última semana?")
        emociones = ["Rabia", "Tristeza", "Ansiedad", "Alegría", "Temor"]
        for emocion in emociones:
            var = tk.BooleanVar()
            tk.Checkbutton(q5_frame, text=emocion, variable=var,
                          bg=self.COL_CARD, fg=self.COL_TEXT,
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11),
                          command=lambda e=emocion, v=var: self._actualizar_emociones(e, v)).pack(anchor="w", pady=2)
        
        # Botones de acción
        action_frame = tk.Frame(scrollable_frame, bg=self.COL_CARD)
        action_frame.pack(fill="x", pady=20)
        
        self._button(action_frame, "🎭 Continuar a Terapia", self._iniciar_terapia_seguimiento).pack(side="left", padx=10)
        self._button(action_frame, "← Volver", self._datos_seguimiento, primary=False).pack(side="left", padx=10)

    def _actualizar_emociones(self, emocion, variable):
        """Actualiza la lista de emociones seleccionadas"""
        if variable.get():
            if emocion not in self.seguimiento_respuestas['emociones_frecuentes']:
                self.seguimiento_respuestas['emociones_frecuentes'].append(emocion)
        else:
            if emocion in self.seguimiento_respuestas['emociones_frecuentes']:
                self.seguimiento_respuestas['emociones_frecuentes'].remove(emocion)

    def _iniciar_terapia_seguimiento(self):
        """Ejecuta la terapia después de las primeras 5 preguntas"""
        # Validar que las primeras 5 preguntas estén respondidas
        if not all([
            self.seguimiento_respuestas['estado_3dias'].get(),
            self.seguimiento_respuestas['sueño_semana'].get(),
            self.seguimiento_respuestas['alimentacion_semana'].get(),
            self.seguimiento_respuestas['sobre_pensamiento'].get()
        ]):
            messagebox.showerror("Error", "Por favor responde todas las preguntas antes de continuar con la terapia")
            return
        
        # Ejecutar la terapia de seguimiento
        self._therapy_seguimiento_mejorada()

    def _therapy_seguimiento_mejorada(self):
        """TERAPIA DE SEGUIMIENTO MEJORADA - Interfaz de dos columnas"""
        self._clear()
        self._topbar("RECONEXIÓN – Sesión de Terapia de Seguimiento")
        
        # Contenedor principal
        main_container = tk.Frame(self.root, bg=self.COL_BG)
        main_container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Configurar grid para dos columnas
        main_container.grid_columnconfigure(0, weight=1)  # Columna izquierda
        main_container.grid_columnconfigure(1, weight=1)  # Columna derecha
        main_container.grid_rowconfigure(0, weight=1)
        
        # ========== COLUMNA IZQUIERDA - TERAPIA EN CURSO ==========
        left_frame = tk.Frame(main_container, bg=self.COL_CARD, relief='raised', bd=1)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Título columna izquierda
        left_header = tk.Frame(left_frame, bg=self.COL_HEADER)
        left_header.pack(fill="x", padx=10, pady=10)
        tk.Label(left_header, text="🌊 Terapia en Curso", 
                 font=("Segoe UI", 16, "bold"), bg=self.COL_HEADER, fg=self.COL_TEXT).pack(anchor="w")
        
        # Estado de la terapia
        terapia_content = tk.Frame(left_frame, bg=self.COL_CARD)
        terapia_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Elementos de terapia activos
        elementos_terapia = [
            "✅ Terapia de luz activada",
            "🎵 Sonidos terapéuticos reproduciendo", 
            "❤️ Monitoreando variabilidad cardíaca",
            "🌬️ Sesión de respiración guiada",
            "🔊 Vibroacústica en funcionamiento"
        ]
        
        for elemento in elementos_terapia:
            tk.Label(terapia_content, text=elemento, font=("Segoe UI", 12),
                    bg=self.COL_CARD, fg="#15803d", anchor="w").pack(fill="x", pady=5)
        
        # Tiempo transcurrido
        tiempo_frame = tk.Frame(terapia_content, bg=self.COL_CARD)
        tiempo_frame.pack(fill="x", pady=15)
        
        self.start_time = time.time()
        self.time_lbl_seg = tk.Label(tiempo_frame, text="⏱️ Tiempo transcurrido: 00:00", 
                                   font=("Segoe UI", 13, "bold"), bg=self.COL_CARD, fg="#b45309")
        self.time_lbl_seg.pack(anchor="w")
        
        # Visualización de colores y patrones
        vis_frame = tk.Frame(terapia_content, bg=self.COL_CARD)
        vis_frame.pack(fill="x", pady=10)
        
        tk.Label(vis_frame, text="🎨 Colores y Patrones:", font=("Segoe UI", 12, "bold"),
                bg=self.COL_CARD, fg=self.COL_TEXT).pack(anchor="w")
        
        tk.Label(vis_frame, text="🔄 Visualización activa", font=("Segoe UI", 11),
                bg=self.COL_CARD, fg=self.COL_MUTED).pack(anchor="w", pady=5)
        
        # Botones de control de terapia
        control_frame = tk.Frame(terapia_content, bg=self.COL_CARD)
        control_frame.pack(fill="x", pady=15)
        
        self._button(control_frame, "🔆 Iluminación  ", self._abrir_iluminacion, primary=True).pack(side="left", padx=5)
        self._button(control_frame, "📺 Visualización", self._abrir_ventana_video, primary=True).pack(side="left", padx=5)
        
        # Iniciar timer
        self._tick_seguimiento()
        
        # ========== COLUMNA DERECHA - PLAYLISTS RECOMENDADAS ==========
        right_frame = tk.Frame(main_container, bg=self.COL_CARD, relief='raised', bd=1)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Título columna derecha
        right_header = tk.Frame(right_frame, bg=self.COL_HEADER)
        right_header.pack(fill="x", padx=10, pady=10)
        tk.Label(right_header, text="🎵 Playlists Recomendadas", 
                 font=("Segoe UI", 16, "bold"), bg=self.COL_HEADER, fg=self.COL_TEXT).pack(anchor="w")
        
        # Contenido de playlists
        playlist_content = tk.Frame(right_frame, bg=self.COL_CARD)
        playlist_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Playlists para seguimiento
        playlists_seguimiento = [
            ("Relajación Profunda", "Sonidos suaves para meditación y calma", "https://open.spotify.com/playlist/3Hd0OMHMLmllUiOGjCQUAU"),
            ("Sonidos Sanadores", "Naturaleza y frecuencias curativas", "https://open.spotify.com/playlist/5ejkNv0mGtwqg3TpRmIrC0"),
            ("Frecuencias Curativas", "432Hz y 528Hz para sanación emocional", "https://open.spotify.com/playlist/5L0pZc5oNutFxMY1xOss84"),
            ("Naturaleza y Calma", "Sonidos naturales para relajación", "https://open.spotify.com/playlist/0ESkeDIKVDNL0lskLr4ftk")
        ]
        
        for i, (nombre, descripcion, url) in enumerate(playlists_seguimiento):
            playlist_item = tk.Frame(playlist_content, bg=self.COL_CARD2, relief='raised', bd=1)
            playlist_item.pack(fill="x", pady=8)
            
            # Nombre de la playlist
            name_label = tk.Label(playlist_item, text=nombre, font=("Segoe UI", 12, "bold"),
                                 bg=self.COL_CARD2, fg=self.COL_TEXT, anchor="w")
            name_label.pack(anchor="w", padx=10, pady=(8, 0))
            
            # Descripción
            desc_label = tk.Label(playlist_item, text=descripcion, font=("Segoe UI", 10),
                                 bg=self.COL_CARD2, fg=self.COL_MUTED, anchor="w")
            desc_label.pack(anchor="w", padx=10, pady=(0, 5))
            
            # Botón reproducir
            btn_frame = tk.Frame(playlist_item, bg=self.COL_CARD2)
            btn_frame.pack(fill="x", padx=10, pady=(0, 8))
            
            self._button(btn_frame, "▶ Reproducir", lambda u=url: self._open_spotify(u), primary=True).pack(side="right")
        
        # ========== BOTONES INFERIORES ==========
        bottom_frame = tk.Frame(self.root, bg=self.COL_BG)
        bottom_frame.pack(fill="x", side="bottom", pady=10)
        
        btn_container = tk.Frame(bottom_frame, bg=self.COL_BG)
        btn_container.pack(expand=True)
        
        self._button(btn_container, "⭐ Calificar Terapia", self._cuestionario_seguimiento_parte2, primary=True).pack(side="left", padx=10)
        self._button(btn_container, "💾 Guardar en Base de Datos", self._guardar_seguimiento_desde_terapia, primary=False).pack(side="left", padx=10)
        self._button(btn_container, "🏠 Menú Principal", self._home, primary=False).pack(side="left", padx=10)
        
        # Guardar las playlists utilizadas para la base de datos
        self.playlists_seguimiento_utilizadas = [nombre for nombre, _, _ in playlists_seguimiento]
        
        # Reproducir automáticamente la primera playlist
        if playlists_seguimiento:
            try: 
                self._open_spotify(playlists_seguimiento[0][2])
            except: 
                pass

    def _tick_seguimiento(self):
        """Actualiza el timer en la terapia de seguimiento"""
        if hasattr(self, "start_time") and hasattr(self, "time_lbl_seg"):
            el = int(time.time() - self.start_time)
            m, s = divmod(el, 60)
            self.time_lbl_seg.configure(text=f"⏱️ Tiempo transcurrido: {m:02d}:{s:02d}")
            self.root.after(1000, self._tick_seguimiento)

    def _guardar_seguimiento_desde_terapia(self):
        """Guarda el seguimiento directamente desde la terapia"""
        messagebox.showinfo("Guardar", "Los datos se guardarán al finalizar la sesión con el botón 'Calificar Terapia'")

    def _cuestionario_seguimiento_parte2(self):
        """Segunda parte del cuestionario de seguimiento (últimas 3 preguntas)"""
        self._clear()
        self._topbar("Evaluación Final - Parte 2")
        
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)
        
        tk.Label(card, text="📝 Evaluación Final - Parte 2", 
                 font=("Segoe UI", 26, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(26, 14))
        
        tk.Label(card, text="Responde las últimas 3 preguntas sobre tu experiencia en la sesión:",
                 font=("Segoe UI", 11), bg=self.COL_CARD, fg=self.COL_MUTED).pack(anchor="w", padx=20, pady=(5, 20))
        
        # Frame con scroll para las últimas 3 preguntas
        canvas = tk.Canvas(card, bg=self.COL_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.COL_CARD)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Pregunta 6: Sensación post-sesión
        q6_frame = self._section(scrollable_frame, "6. ¿Cómo te sientes al terminar la sesión?")
        self.sensacion_text = tk.Text(q6_frame, height=3, width=60, font=("Segoe UI", 11),
                                 bg=self.COL_INPUT, fg=self.COL_INPUT_TX, relief="solid", bd=1)
        self.sensacion_text.pack(fill="x", padx=10, pady=5)
        
        # Pregunta 7: Lo más valioso
        q7_frame = self._section(scrollable_frame, "7. ¿Qué fue lo más valioso para ti hoy en la sesión?")
        self.valioso_text = tk.Text(q7_frame, height=3, width=60, font=("Segoe UI", 11),
                               bg=self.COL_INPUT, fg=self.COL_INPUT_TX, relief="solid", bd=1)
        self.valioso_text.pack(fill="x", padx=10, pady=5)
        
        # Pregunta 8: Recursos implementados
        q8_frame = self._section(scrollable_frame, "8. ¿Has implementado en casa algún recurso utilizado en la terapia?")
        opciones_recursos = ["Sí", "No", "Regularmente"]
        for opcion in opciones_recursos:
            tk.Radiobutton(q8_frame, text=opcion, variable=self.seguimiento_respuestas['recursos_implementados'],
                          value=opcion, bg=self.COL_CARD, fg=self.COL_TEXT,
                          selectcolor=self.COL_HEADER, font=("Segoe UI", 11)).pack(anchor="w", pady=2)
        
        # Botones de acción
        action_frame = tk.Frame(scrollable_frame, bg=self.COL_CARD)
        action_frame.pack(fill="x", pady=20)
        
        self._button(action_frame, "💾 Guardar Seguimiento Completo", self._guardar_seguimiento).pack(side="left", padx=10)
        self._button(action_frame, "← Volver a Terapia", self._therapy_seguimiento_mejorada, primary=False).pack(side="left", padx=10)

    def _guardar_seguimiento(self):
        """Guarda las respuestas del seguimiento en la base de datos"""
        # Validar que todas las preguntas estén respondidas
        if not all([
            self.seguimiento_respuestas['estado_3dias'].get(),
            self.seguimiento_respuestas['sueño_semana'].get(),
            self.seguimiento_respuestas['alimentacion_semana'].get(),
            self.seguimiento_respuestas['sobre_pensamiento'].get(),
            self.seguimiento_respuestas['recursos_implementados'].get()
        ]):
            messagebox.showerror("Error", "Por favor responde todas las preguntas obligatorias")
            return
        
        # Obtener texto de las preguntas abiertas
        sensacion = self.sensacion_text.get("1.0", "end-1c").strip()
        valioso = self.valioso_text.get("1.0", "end-1c").strip()
        
        if not sensacion:
            messagebox.showerror("Error", "Por favor responde cómo te sientes al terminar la sesión")
            return
        
        # Guardar en base de datos
        try:
            db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # OBTENER NOMBRE LIMPIO
            nombre_completo = f"{self.demographics.get('nombre', '')}"
            
            cursor.execute('''
                INSERT INTO seguimientos (
                    paciente_id, paciente_nombre, estado_3dias, sueño_semana, 
                    alimentacion_semana, sobre_pensamiento, emociones_frecuentes,
                    sensacion_post_sesion, mas_valioso, recursos_implementados,
                    playlists_utilizadas, recomendaciones_terapia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.demographics.get('num_doc_pac', ''),
                nombre_completo,  # SOLO NOMBRE, sin género ni edad
                self.seguimiento_respuestas['estado_3dias'].get(),
                self.seguimiento_respuestas['sueño_semana'].get(),
                self.seguimiento_respuestas['alimentacion_semana'].get(),
                self.seguimiento_respuestas['sobre_pensamiento'].get(),
                ', '.join(self.seguimiento_respuestas['emociones_frecuentes']),
                sensacion,
                valioso,
                self.seguimiento_respuestas['recursos_implementados'].get(),
                ', '.join(getattr(self, 'playlists_seguimiento_utilizadas', ['Relajación Profunda'])),
                'Terapia de seguimiento con playlists de relajación y sonidos terapéuticos'
            ))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Éxito", "✅ Seguimiento guardado correctamente en la base de datos")
            self._programa()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el seguimiento: {str(e)}")

    # ------------------------------- Consentimiento -------------------------------
    def _consent(self):
        self._clear()
        self._topbar()
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)
        header = tk.Frame(card, bg=self.COL_HEADER,
                           highlightbackground=self.COL_BORDER, highlightthickness=1)
        header.pack(fill="x", padx=14, pady=(14, 10))
        tk.Label(header, text="Consentimiento Informado",
                 font=("Segoe UI", 20, "bold"), bg=self.COL_HEADER, fg=self.COL_TEXT).pack(padx=12, pady=10, anchor="w")
        text_wrap = tk.Frame(card, bg=self.COL_CARD); text_wrap.pack(fill="x", padx=14, pady=(2, 8))
        inner = tk.Frame(text_wrap, bg=self.COL_CARD, height=360); inner.pack(fill="x"); inner.pack_propagate(False)
        txt = tk.Text(inner, wrap="word", bg=self.COL_INPUT, fg=self.COL_INPUT_TX,
                      relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B,
                      font=("Segoe UI", 11), padx=14, pady=14, height=18)
        scr = ttk.Scrollbar(inner, command=txt.yview); txt.configure(yscrollcommand=scr.set)
        txt.pack(side="left", fill="both", expand=True); scr.pack(side="right", fill="y")
        txt.insert("1.0", load_consent_text(self.base_path)); txt.config(state="disabled")
        actions = tk.Frame(card, bg=self.COL_CARD); actions.pack(pady=8)
        self._button(actions, "✅ Acepto las condiciones", self._demographics).pack(side="left", padx=6)
        self._button(actions, "← Volver", self._programa, primary=False).pack(side="left", padx=6)

    # ------------------------------- Demográficos -------------------------------
    def _demographics(self):
        self._clear(); self._topbar("Datos Demográficos")
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)
        tk.Label(card, text="Datos Demográficos",
                 font=("Segoe UI", 22, "bold"), bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(16, 6))
        def val_letras(P): return re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]*", P or "") is not None
        def val_digs(P):   return re.fullmatch(r"[0-9]*", P or "") is not None
        v_letras = (self.root.register(val_letras), '%P')
        v_digs   = (self.root.register(val_digs), '%P')

        g1 = self._section(card, "Identificación")
        
        # AGREGAR CAMPO DE NOMBRE COMPLETO
        row0 = tk.Frame(g1, bg=self.COL_CARD); row0.pack(fill="x", pady=4)
        
        tk.Label(row0, text="Nombre completo:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=15, anchor="w").pack(side="left")
        self.nombre_completo = tk.Entry(row0, validate="key", validatecommand=v_letras,
                                       bg=self.COL_INPUT, fg=self.COL_INPUT_TX, font=("Segoe UI", 11),
                                       relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B)
        self.nombre_completo.pack(side="left", fill="x", expand=True, padx=(8, 0))
        
        genero_f = tk.Frame(g1, bg=self.COL_CARD); self.genero = tk.StringVar(value="")
        for opt in ["Masculino", "Femenino", "No binario"]:
            tk.Radiobutton(genero_f, text=opt, value=opt, variable=self.genero,
                           bg=self.COL_CARD, fg=self.COL_TEXT, selectcolor=self.COL_HEADER,
                           font=("Segoe UI", 11)).pack(side="left", padx=10)
        row1 = tk.Frame(g1, bg=self.COL_CARD); row1.pack(fill="x", pady=4)
        
        tk.Label(row1, text="Género:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=10, anchor="w").pack(side="left")
        genero_f.pack(side="left", padx=(4, 18))
        
        tk.Label(row1, text="Edad:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=8, anchor="w").pack(side="left")
        self.edad_var = tk.StringVar()
        edad_e = tk.Entry(row1, width=10, validate="key", validatecommand=v_digs,
                          bg=self.COL_INPUT, fg=self.COL_INPUT_TX, font=("Segoe UI", 11),
                          relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B)
        edad_e.configure(textvariable=self.edad_var); edad_e.pack(side="left", padx=(4, 18))
        
        
        # --- Tipo de documento ---
        tk.Label(
            row1, text="Tipo doc. (paciente):",
            bg=self.COL_CARD, fg=self.COL_TEXT,
            font=("Segoe UI", 11), anchor="w"
        ).pack(side="left")

        self.tipo_doc_pac = tk.StringVar()
        tipos = [
            "CC - Cédula de ciudadanía",
            "TI - Tarjeta de Identidad",
            "RC - Registro civil",
            "CE - Cédula de extranjería",
            "PA - Pasaporte",
            "Otro"
        ]

        tipo_cb = ttk.Combobox(
            row1, textvariable=self.tipo_doc_pac,
            values=tipos, state="readonly", font=("Segoe UI", 11)
        )
        tipo_cb.pack(side="left", padx=(4, 0), fill="x", expand=True)

        # --- Número de documento ---
        row2 = tk.Frame(g1, bg=self.COL_CARD)
        row2.pack(fill="x", pady=6)

        tk.Label(
            row2, text="N° doc. (paciente):",
            bg=self.COL_CARD, fg=self.COL_TEXT,
            font=("Segoe UI", 11), anchor="w"
        ).pack(side="left")

        # --- Validación: solo números y máximo 10 dígitos ---
        def validar_doc(nuevo_valor):
            # Si está vacío, permitir
            if nuevo_valor == "":
                return True
            # Si no son solo dígitos o excede 10 caracteres, bloquear
            return nuevo_valor.isdigit() and len(nuevo_valor) <= 10

        v_cmd_doc = row2.register(validar_doc)

        self.num_doc_pac = tk.Entry(
            row2,
            validate="key",
            validatecommand=(v_cmd_doc, "%P"),  # %P = valor potencial
            bg=self.COL_INPUT,
            fg=self.COL_INPUT_TX,
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.COL_INPUT_B
        )
        self.num_doc_pac.pack(side="left", fill="x", expand=True, padx=(8, 0))



        acud = self._section(card, "Datos del Acudiente")
        rowa = tk.Frame(acud, bg=self.COL_CARD); rowa.pack(fill="x", pady=4)
        # AGREGAR CAMPOS DE ACUDIENTE
        # -- Nombre --
        tk.Label(rowa, text="Nombre:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=10, anchor="w").pack(side="left")
        self.ac_nom = tk.Entry(rowa, validate="key", validatecommand=v_letras,
                               bg=self.COL_INPUT, fg=self.COL_INPUT_TX, font=("Segoe UI", 11),
                               relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B)
        self.ac_nom.pack(side="left", fill="x", expand=True, padx=(4, 18))
        
        # -- Celular --
        tk.Label(
            rowa,
            text="Celular:",
            bg=self.COL_CARD,
            fg=self.COL_TEXT,
            font=("Segoe UI", 11),
            width=10,
            anchor="w"
        ).pack(side="left")

        # --- Validación: solo números y máximo 10 dígitos ---
        def validar_celular(nuevo_valor):
            if nuevo_valor == "":
                return True  # permite borrar
            return nuevo_valor.isdigit() and len(nuevo_valor) <= 10

        v_cmd_celular = rowa.register(validar_celular)

        self.ac_cel = tk.Entry(
            rowa,
            validate="key",
            validatecommand=(v_cmd_celular, "%P"),
            bg=self.COL_INPUT,
            fg=self.COL_INPUT_TX,
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.COL_INPUT_B
        )
        self.ac_cel.pack(side="left", fill="x", expand=True, padx=(4, 0))

        rowb = tk.Frame(acud, bg=self.COL_CARD)
        rowb.pack(fill="x", pady=4)

        
        # -- Parentesco --
        tk.Label(rowb, text="Parentesco:", bg=self.COL_CARD, fg=self.COL_TEXT, font=("Segoe UI", 11),
                 width=10, anchor="w").pack(side="left")
        self.ac_par = tk.Entry(rowb, validate="key", validatecommand=v_letras,
                               bg=self.COL_INPUT, fg=self.COL_INPUT_TX, font=("Segoe UI", 11),
                               relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B)
        self.ac_par.pack(side="left", fill="x", expand=True, padx=(4, 0))
        rowc = tk.Frame(acud, bg=self.COL_CARD); rowc.pack(fill="x", pady=4)
        
        # -- Tipo y N° de documento --
        tk.Label(rowc, text="Tipo doc. (acudiente):", bg=self.COL_CARD, fg=self.COL_TEXT,
                 font=("Segoe UI", 11), anchor="w").pack(side="left")
        self.tipo_doc_acu = tk.StringVar()
        tipo_acu_cb = ttk.Combobox(rowc, textvariable=self.tipo_doc_acu, values=tipos, state="readonly")
        tipo_acu_cb.configure(font=("Segoe UI", 11)); tipo_acu_cb.pack(side="left", fill="x", expand=True, padx=(6, 18))
        
        tk.Label(
            rowc,
            text="N° doc. (acudiente):",
            bg=self.COL_CARD,
            fg=self.COL_TEXT,
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(side="left")

        # --- Validación: solo números y máximo 10 dígitos ---
        def validar_doc_acu(nuevo_valor):
            if nuevo_valor == "":
                return True
            return nuevo_valor.isdigit() and len(nuevo_valor) <= 10

        v_cmd_doc_acu = rowc.register(validar_doc_acu)

        self.num_doc_acu = tk.Entry(
            rowc,
            validate="key",
            validatecommand=(v_cmd_doc_acu, "%P"),  # %P = nuevo valor potencial
            bg=self.COL_INPUT,
            fg=self.COL_INPUT_TX,
            font=("Segoe UI", 11),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.COL_INPUT_B
        )
        self.num_doc_acu.pack(side="left", fill="x", expand=True, padx=(6, 0))




        # 🔹 Función limitar la edad
        def refresh():
            try:
                edad = int(self.edad_var.get())
            except:
                edad = None

            # 🔹 Validar rango permitido (0 a 110)
            if edad is not None:
                if edad < 0:
                    edad = 0
                    self.edad_var.set("0")
                    
                elif edad > 99:
                    edad = 99
                    self.edad_var.set("99")

            # 🔹 Detectar si es menor de edad
            menor = edad is not None and edad < 18
            for w in (self.ac_nom, self.ac_cel, self.ac_par, self.num_doc_acu):
                w.configure(state="normal" if menor else "disabled")
            tipo_acu_cb.configure(state="readonly" if menor else "disabled")
            self._is_minor = menor

        self._is_minor = False
        self.edad_var.trace_add("write", lambda *_: refresh())
        refresh()


        if hasattr(self, "demographics") and self.demographics:
            d = self.demographics
            # Paciente
            self.nombre_completo.delete(0, "end")
            self.nombre_completo.insert(0, d.get("nombre", ""))

            self.genero.set(d.get("genero", ""))
            self.edad_var.set(str(d.get("edad", "")))
            self.tipo_doc_pac.set(d.get("tipo_doc_pac", ""))
            self.num_doc_pac.delete(0, "end")
            self.num_doc_pac.insert(0, d.get("num_doc_pac", ""))

            # Acudiente (solo si era menor)
            if d.get("menor", False):
                self.ac_nom.delete(0, "end")
                self.ac_nom.insert(0, d.get("acudiente_nombre", ""))

                self.ac_cel.delete(0, "end")
                self.ac_cel.insert(0, d.get("acudiente_cel", ""))

                self.ac_par.delete(0, "end")
                self.ac_par.insert(0, d.get("acudiente_parentesco", ""))

                self.tipo_doc_acu.set(d.get("tipo_doc_acu", ""))
                self.num_doc_acu.delete(0, "end")
                self.num_doc_acu.insert(0, d.get("num_doc_acu", ""))

                # Mantener habilitados los campos de acudiente
                self._is_minor = True
                for w in (self.ac_nom, self.ac_cel, self.ac_par, self.num_doc_acu):
                    w.configure(state="normal")
                tipo_acu_cb.configure(state="readonly")
            else:
                self._is_minor = False



        action = tk.Frame(card, bg=self.COL_CARD)
        action.pack(pady=10)
        self._button(action, "Continuar →", self._validate_and_questions).pack(side="left", padx=8)
        self._button(action, "← Volver", self._consent, primary=False).pack(side="left", padx=8)


    def _validate_and_questions(self):
        nombre = self.nombre_completo.get().strip()
        genero = self.genero.get().strip()
        edad_s = self.edad_var.get().strip()
        tipo_p = self.tipo_doc_pac.get().strip()
        num_p  = self.num_doc_pac.get().strip()
        
        if not nombre:
            messagebox.showerror("Campo requerido","Ingresa el nombre completo."); return
        if not genero:
            messagebox.showerror("Campo requerido","Selecciona el género."); return
        if not edad_s.isdigit():
            messagebox.showerror("Campo requerido","Ingresa una edad válida."); return
        if not tipo_p:
            messagebox.showerror("Campo requerido","Selecciona el tipo de documento del paciente."); return
        if not num_p or not num_p.isdigit():
            messagebox.showerror("Campo requerido","Ingresa un N° de documento válido para el paciente."); return
        
        self.demographics = {
            "nombre": nombre,
            "genero": genero,
            "edad": int(edad_s),
            "tipo_doc_pac": tipo_p,
            "num_doc_pac": num_p
        }
        
        if self._is_minor:
            nom = self.ac_nom.get().strip(); cel = self.ac_cel.get().strip()
            par = self.ac_par.get().strip(); tipo_a = self.tipo_doc_acu.get().strip(); num_a = self.num_doc_acu.get().strip()
            if not nom or not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", nom):
                messagebox.showerror("Campo requerido","Nombre del acudiente inválido."); return
            if not cel or not cel.isdigit():
                messagebox.showerror("Campo requerido","Celular del acudiente inválido."); return
            if not par or not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]+", par):
                messagebox.showerror("Campo requerido","Parentesco inválido."); return
            if not tipo_a:
                messagebox.showerror("Campo requerido","Selecciona el tipo de documento del acudiente."); return
            if not num_a or not num_a.isdigit():
                messagebox.showerror("Campo requerido","N° de documento del acudiente inválido."); return
            self.demographics.update({
                "acudiente_nombre":nom,"acudiente_cel":cel,"acudiente_parentesco":par,
                "tipo_doc_acu":tipo_a,"num_doc_acu":num_a,"menor":True
            })
        else:
            self.demographics["menor"] = False
        self._questionnaire()

    # ------------------------------- Cuestionario inicial -------------------------------
    def _setup_questions(self):
        self.questions = [
            {"id":1, "text":"¿Con qué frecuencia siente ansiedad intensa o ataques de pánico en una semana?", "options":["Nunca","1-2 veces","3-4 veces","Más de 4 veces"]},
            {"id":2, "text":"¿Presenta dificultad para conciliar o mantener el sueño?", "options":["Nunca","Ocasionalmente","Frecuentemente","Todas las noches"]},
                        {"id":3, "text":"¿Ha perdido interés o placer en actividades que antes disfrutaba?", "options":["No","Sí, algunas veces","Sí, la mayor parte del tiempo"]},
            {"id":4, "text":"¿En qué momento del día sus síntomas son más intensos?", "options":["Mañana","Tarde","Noche","No hay un patrón"]},
            {"id":5, "text":"¿Su estado de ánimo mejora con exposición a luz natural o actividades al aire libre?", "options":["Sí","No","No lo sé"]},
            {"id":6, "text":"¿Se siente físicamente agitado o con tensión muscular constante?", "options":["Nunca","Ocasionalmente","Frecuentemente"]},
            {"id":7, "text":"¿Ha sido diagnosticado con algún trastorno del sueño como insomnio o hipersomnia?", "options":["No","Sí, insomnio","Sí, hipersomnia"]},
            {"id":8, "text":"¿Presenta antecedentes de migraña o sensibilidad a luces parpadeantes?", "options":["Sí","No"]},
            {"id":9, "text":"¿Cuál es su nivel de energía general en el día?", "options":["Alto","Moderado","Bajo","Muy bajo"]},
            {"id":10,"text":"¿Ha utilizado previamente estrategias terapéuticas como respiración guiada, sonidos relajantes o luz brillante?", "options":["No","Sí, con beneficio","Sí, sin beneficio"]},
        ]

    def _questionnaire(self):
        self._clear(); self._topbar("Cuestionario de Evaluación")
        card = self._card(self.root, 0.5, 0.5, 0.86, 0.82)

        head = tk.Frame(card, bg=self.COL_HEADER,
                        highlightbackground=self.COL_BORDER, highlightthickness=1)
        head.pack(fill="x", padx=14, pady=(14, 8))
        tk.Label(head, text="Cuestionario de Evaluación", font=("Segoe UI", 20, "bold"),
                bg=self.COL_HEADER, fg=self.COL_TEXT).pack(side="left", padx=12, pady=8)
        tk.Label(head, text=f"{self.current+1}/{len(self.questions)}", font=("Segoe UI", 12),
                bg=self.COL_HEADER, fg=self.COL_ACCENT2).pack(side="right", padx=12)

        q = self.questions[self.current]
        tk.Label(card, text=q["text"], font=("Segoe UI", 14, "bold"),
                bg=self.COL_CARD, fg=self.COL_TEXT, wraplength=780, justify="center").pack(pady=14, padx=24)

        # opciones
        saved = self.answers.get(q["id"])  # <- lo que ya respondió antes (si existe)
        opts = tk.Frame(card, bg=self.COL_CARD); opts.pack(pady=8)
        for opt in q["options"]:
            # si tienes 'primary=' en tu _button, úsalo para resaltar la opción ya elegida
            self._button(opts, opt, lambda o=opt: self._answer(o),
                        primary=True).pack(pady=6, padx=40, fill="x")

        ttk.Progressbar(card, maximum=len(self.questions), value=self.current+1, length=620).pack(pady=12)

        # navegación inferior
        nav = tk.Frame(card, bg=self.COL_CARD); nav.pack(pady=(6,0))
        if self.current > 0:
            self._button(nav, "← Anterior", self._go_prev, primary=False).pack(side="left", padx=6)
        self._button(nav, "← Volver", self._demographics, primary=False).pack(side="left", padx=6)


    def _answer(self, opt):
        self.answers[self.questions[self.current]["id"]] = opt
        if self.current < len(self.questions) - 1:
            self.current += 1; self._questionnaire()
        else:
            self._build_plan()
            self._results()

    # Botón "Anterior": función simple para retroceder una pregunta
    def _go_prev(self):
        if self.current > 0:
            self.current -= 1
            self._questionnaire()


    # ------------------------------- Reglas, módulos y playlists -------------------------------
    def _setup_playlists(self):
        self.PLAYLISTS = {
            "Anxiety Relief (432 Hz)": "https://open.spotify.com/playlist/3Hd0OMHMLmllUiOGjCQUAU",
            "Binaural Beats for Healing Depression & Anxiety": "https://open.spotify.com/playlist/5ejkNv0mGtwqg3TpRmIrC0",
            "Solfeggio Frequencies to Help With Depression": "https://open.spotify.com/playlist/5L0pZc5oNutFxMY1xOss84",
            "Healing From Depression – playlist": "https://open.spotify.com/playlist/1nAd9W6i53T8QOiwFY3t1k",
            "Mental Health & Depression: Sound Therapy To Reduce Anxiety": "https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO",
            "Depression Relief Frequencies 528 Hz": "https://open.spotify.com/playlist/6TmvRUpaNfKfJnbhv8cebz",
            "Naturaleza / Relax visual (genérico)": "https://open.spotify.com/playlist/0ESkeDIKVDNL0lskLr4ftk",
            "Ruido rosa / marrón (sueño)": "https://open.spotify.com/playlist/6sPkDFYJLQ1eNNjURZbAoZ",
        }

    def _setup_rules(self):
        self.MODULES = {
            "HRV":"Respiración guiada HRV a 6 rpm (0,1 Hz), 10–15 min, 3–4 veces/semana.",
            "SONIDOS":"Sonidos relajantes + visual naturaleza, 10–15 min/sesión, volumen moderado.",
            "VIBRO":"Vibroacústica 30–80 Hz, 20–25 min, 2–3/semana.",
            "LUZ_AM":"Terapia de luz 10.000 lux, 20–30 min por la mañana, 5–7/semana.",
            "HIGIENE_SUEÑO":"Rutina de sueño, luz cálida por la tarde, ruido rosa opcional.",
            "ACT_CONDUCTUAL":"Activación conductual diaria.",
            "RMP":"Relajación muscular progresiva (10–12 min)."
        }
        self.RULES = {
            (1,"1-2 veces"):["SONIDOS"], (1,"3-4 veces"):["HRV","SONIDOS"], (1,"Más de 4 veces"):["HRV","SONIDOS"],
            (2,"Frecuentemente"):["VIBRO","HIGIENE_SUEÑO"], (2,"Todas las noches"):["VIBRO","HIGIENE_SUEÑO"],
            (3,"Sí, algunas veces"):["ACT_CONDUCTUAL"], (3,"Sí, la mayor parte del tiempo"):["LUZ_AM","ACT_CONDUCTUAL"],
            (4,"Mañana"):["LUZ_AM"], (4,"Tarde"):["SONIDOS"], (4,"Noche"):["SONIDOS","HRV"],
            (5,"Sí"):["LUZ_AM"], (6,"Frecuentemente"):["HRV","RMP"],
            (7,"Sí, insomnio"):["VIBRO","HIGIENE_SUEÑO"], (7,"Sí, hipersomnia"):["LUZ_AM","ACT_CONDUCTUAL"],
            (8,"Sí"):[], (9,"Bajo"):["ACT_CONDUCTUAL"], (9,"Muy bajo"):["ACT_CONDUCTUAL","LUZ_AM"],
        }
        self.MODULE_PL = {
            "HRV":["Anxiety Relief (432 Hz)","Binaural Beats for Healing Depression & Anxiety"],
            "SONIDOS":["Mental Health & Depression: Sound Therapy To Reduce Anxiety","Solfeggio Frequencies to Help With Depression","Naturaleza / Relax visual (genérico)"],
            "VIBRO":["Mental Health & Depression: Sound Therapy To Reduce Anxiety"],
            "LUZ_AM":["Depression Relief Frequencies 528 Hz","Healing From Depression – playlist"],
            "HIGIENE_SUEÑO":["Ruido rosa / marrón (sueño)"],
            "ACT_CONDUCTUAL":["Healing From Depression – playlist","Depression Relief Frequencies 528 Hz"],
            "RMP":["Anxiety Relief (432 Hz)","Binaural Beats for Healing Depression & Anxiety"],
        }

    def _infer_modules(self):
        mods = set()
        for qid, opt in self.answers.items():
            if (qid, opt) in self.RULES:
                mods.update(self.RULES[(qid, opt)])
        return sorted(mods) or ["SONIDOS"]
    
    def _infer_profile(self):
        res = []
        a1 = self.answers.get(1)
        if a1 == "1-2 veces": 
            res.append(("Ansiedad","leve"))
        if a1 == "3-4 veces": 
            res.append(("Ansiedad","moderada"))
        if a1 == "Más de 4 veces": 
            res.append(("Ansiedad","alta"))
        
        a3 = self.answers.get(3)
        if a3 == "Sí, algunas veces": 
            res.append(("Ánimo bajo/anhedonia","leve"))
        if a3 == "Sí, la mayor parte del tiempo": 
            res.append(("Ánimo bajo/anhedonia","marcada"))
        
        a2 = self.answers.get(2)
        a7 = self.answers.get(7)
        if a2 in ["Frecuentemente","Todas las noches"] or a7 == "Sí, insomnio":
            res.append(("Problemas de sueño (insomnio)","presentes"))
        if a7 == "Sí, hipersomnia":
            res.append(("Somnolencia/hipersomnia","presente"))
        
        a6 = self.answers.get(6)
        if a6 == "Frecuentemente": 
            res.append(("Tensión corporal/agitación","elevada"))
        elif a6 == "Ocasionalmente": 
            res.append(("Tensión corporal/agitación","ocasional"))
        
        a8 = self.answers.get(8)
        if a8 == "Sí": 
            res.append(("Sensibilidad a luz/migraña","precaución con luz"))
        
        a9 = self.answers.get(9)
        if a9 == "Bajo": 
            res.append(("Energía","baja"))
        if a9 == "Muy bajo": 
            res.append(("Energía","muy baja"))
        
        return res

    def _build_plan(self):
        mods = self._infer_modules()
        profile = self._infer_profile()
        self.profile_infer = profile
        self.modules_selected = mods[:]
        objetivos = []
        if any("Ansiedad" in p[0] for p in profile): objetivos.append("Reducir activación fisiológica y ansiedad.")
        if any("Ánimo" in p[0] for p in profile): objetivos.append("Mejorar el estado de ánimo y la motivación.")
        if any("sueño" in p[0].lower() for p in profile): objetivos.append("Regular el ciclo de sueño y la higiene del descanso.")
        if any("Energía" in p[0] for p in profile): objetivos.append("Incrementar energía y vitalidad cotidiana.")
        if any("Tensión" in p[0] for p in profile): objetivos.append("Disminuir tensión muscular y agitación.")
        if any("luz" in p[0].lower() for p in profile): objetivos.append("Prevenir molestias por sensibilidad a la luz.")
        severity = 0
        if self.answers.get(1) in ["3-4 veces","Más de 4 veces"]: severity += 1
        if self.answers.get(2) in ["Frecuentemente","Todas las noches"]: severity += 1
        if self.answers.get(3) == "Sí, la mayor parte del tiempo": severity += 1
        if self.answers.get(9) in ["Bajo","Muy bajo"]: severity += 1
        if severity == 0: freq = "Leve: 2 sesiones/semana por 6–8 semanas."
        elif severity == 1: freq = "Leve-Moderado: 2–3 sesiones/semana por 6–8 semanas."
        elif severity == 2: freq = "Moderado: 3/semana por 6–8 semanas + seguimiento."
        else: freq = "Moderado-Severo: 3/semana por 8 semanas + control clínico semanal."
        lines = []
        if profile:
            lines.append("— Perfil sugerido (NO diagnóstico) —")
            for n, sev in profile: lines.append(f"• {n}: {sev}")
            lines.append("")
        if objetivos:
            lines.append("— Objetivos terapéuticos —")
            for o in objetivos: lines.append(f"• {o}")
            lines.append("")
        lines.append("— Cronograma recomendado —"); lines.append(freq); lines.append("")
        lines.append("— Módulos recomendados —")
        playlists = []
        for m in mods:
            lines.append(f"• {m}: {self.MODULES[m]}")
            for p in self.MODULE_PL.get(m, []):
                if p not in playlists and self.PLAYLISTS.get(p):
                    playlists.append(p); lines.append(f"   - Playlist: {p}")
        safety = []
        if self.answers.get(8) == "Sí": safety.append("Evitar luces brillantes/parpadeantes; usar iluminación estable y cálida.")
        if self.answers.get(4) in ["Tarde","Noche"]: safety.append("Preferir luz cálida tenue por la tarde/noche (<10 lux melanópicos).")
        if safety: lines += ["", "— Precauciones —"] + ["- " + s for s in safety]
        lines += ["", "Esta app es de apoyo y no sustituye atención profesional."]
        self.plan_text = "\n".join(lines)
        self.plan_playlists = [(n, self.PLAYLISTS[n]) for n in playlists]

    # ------------------------------- Resultados/Plan -------------------------------
    def _results(self):
        self._clear(); self._topbar("RECONEXIÓN – Resultados y Plan")
        plan = self._card(self.root, 0.32, 0.5, 0.60, 0.86)
        tk.Label(plan, text="🧠 Plan Recomendado", font=("Segoe UI", 18, "bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).pack(anchor="w", padx=18, pady=(18, 8))
        box = tk.Frame(plan, bg=self.COL_CARD, highlightbackground=self.COL_INPUT_B, highlightthickness=1)
        box.pack(expand=True, fill="both", padx=12, pady=(0, 12))
        t = tk.Text(box, wrap="word", bg=self.COL_CARD, fg=self.COL_TEXT, relief="flat",
                    font=("Segoe UI", 11), padx=14, pady=14)
        t.insert("1.0", self.plan_text); t.config(state="disabled"); t.pack(expand=True, fill="both")
        side = self._card(self.root, 0.80, 0.5, 0.35, 0.86)
        tk.Label(side, text="🎵 Playlists Terapéuticas", font=("Segoe UI", 16, "bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).pack(anchor="w", padx=18, pady=(18, 8))
        wrap = tk.Frame(side, bg=self.COL_CARD); wrap.pack(expand=True, fill="both", padx=12, pady=8)
        canvas = tk.Canvas(wrap, bg=self.COL_CARD, highlightthickness=0); sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.COL_CARD); inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=inner, anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for name, url in self.plan_playlists:
            card = tk.Frame(inner, bg=self.COL_CARD2, highlightbackground=self.COL_BORDER, highlightthickness=1)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=f"🔗  {name}", font=("Segoe UI", 11, "bold"), bg=self.COL_CARD2, fg=self.COL_TEXT,
                     anchor="w").pack(side="left", padx=10, pady=10, fill="x", expand=True)
            self._button(card, "Abrir", lambda u=url: self._open_spotify(u), primary=False).pack(side="right", padx=8, pady=6)
        actions = tk.Frame(self.root, bg=self.COL_BG); actions.place(relx=0.96, rely=0.96, anchor="se")
        self._button(actions, "▶️ Iniciar Terapia", self._therapy).pack(side="right", padx=8)
        self._button(actions, "🔄 Nueva Evaluación", self._reset, primary=False).pack(side="right", padx=8)

    # ------------------------------- Terapia -------------------------------
    def _https_to_spotify_uri(self, url):
        m = re.search(r"open\.spotify\.com/(playlist|track|album|artist|show|episode)/([A-Za-z0-9]+)", url or "")
        return f"spotify:{m.group(1)}:{m.group(2)}" if m else (url or "")

    def _open_spotify(self, url):
        try:
            uri = self._https_to_spotify_uri(url)
            if os.name == "nt": os.startfile(uri)
            elif sys.platform == "darwin": subprocess.run(["open", uri], check=False)
            else: subprocess.run(["xdg-open", uri], check=False)
        except Exception:
            try: webbrowser.open(url)
            except Exception: pass

    # ------------------------------- Pantalla de ejecución de Terapia  -------------------------------
    def _therapy(self):
        self._clear(); self._topbar("RECONEXIÓN – Sesión de Terapia")
        rootwrap = tk.Frame(self.root, bg=self.COL_BG); rootwrap.pack(expand=True, fill="both")
        main = tk.Frame(rootwrap, bg=self.COL_BG); main.pack(side="top", expand=True, fill="both", padx=18, pady=(12,0))
        main.grid_columnconfigure(0, weight=1); main.grid_columnconfigure(1, weight=2); main.grid_rowconfigure(0, weight=1)
        left = tk.Frame(main, bg=self.COL_BG); left.grid(row=0, column=0, sticky="nsew", padx=(0,14))
        tk.Label(left, text="🌊 Ejecutando Terapia", font=("Segoe UI", 22, "bold"), bg=self.COL_BG, fg=self.COL_TEXT).pack(anchor="w", pady=(0,12))
        for s in ["☀️ Terapia de luz activada","🎵 Sonidos terapéuticos reproduciendo","❤️ Monitoreando variabilidad cardíaca","🧘 Sesión de respiración guiada","🌊 Vibroacústica en funcionamiento"]:
            tk.Label(left, text=s, font=("Segoe UI", 13), bg=self.COL_BG, fg="#15803d").pack(anchor="w", pady=6)
        self.start_time = time.time()
        self.time_lbl = tk.Label(left, text="⏱️ Tiempo transcurrido: 00:00", font=("Segoe UI", 13, "bold"),
                                  bg=self.COL_BG, fg="#b45309")
        self.time_lbl.pack(anchor="w", pady=(10,0))

        
        self._button(left, "🔆 Iluminación  ", self._abrir_iluminacion, primary=True).pack(anchor="w", pady=(15, 0))
        self._button(left, "🎥 Visualización", self._abrir_ventana_video, primary=True).pack(anchor="w", pady=(15, 0))

        self._tick()
        right = tk.Frame(main, bg=self.COL_BG); right.grid(row=0, column=1, sticky="n")
        if self.relax_tk and ImageTk is not None:
            tk.Label(right, image=self.relax_tk, bg=self.COL_BG).pack(pady=8)
        bottom = tk.Frame(rootwrap, bg=self.COL_CARD, highlightbackground=self.COL_BORDER, highlightthickness=1)
        bottom.pack(side="bottom", fill="x")
        rightgrp = tk.Frame(bottom, bg=self.COL_CARD); rightgrp.pack(side="right", padx=18, pady=10)
        self._button(rightgrp, "🏠 Abandonar", self._home, primary=False).pack(side="left", padx=8)
        self._button(rightgrp, "🛑 Terminar Terapia", lambda: self._finish_terapia_inicial(auto=False)).pack(side="left", padx=8)
        if self.plan_playlists:
            try: self._open_spotify(self.plan_playlists[0][1])
            except: pass

    # === Definicion de las funciones Botones de color ===
    def _blanco(self):
        print("Blanco")
        if arduino: arduino.write(b'b')
        self.color_terapia="blanco"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")
    
    def _rojopast(self):
        print("Rojo pastel")
        if arduino: arduino.write(b'r')
        self.color_terapia="rojo pastel"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")
        
    def _celeste(self):
        print("Celeste")
        if arduino: arduino.write(b'c')    
        self.color_terapia="celeste"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")

    def _amarillo(self):
        print("Amarillo")
        if arduino: arduino.write(b'a')  
        self.color_terapia="amarillo"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")

    def _azul(self):
        print("Azul")
        if arduino: arduino.write(b'z')  
        self.color_terapia="azul"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")

    def _morado(self):
        print("Morado")
        if arduino: arduino.write(b'm')  
        self.color_terapia="morado"
        messagebox.showinfo("Selección de color", f"Color {self.color_terapia} seleccionado para la terapia de luz.")

    #Definicion funciones de los patrones
    def _patron1(self):
        print("Patron 1")
        if arduino: arduino.write(b'l')    

    def _patron2(self):
        print("Patron 2")
        if arduino: arduino.write(b'w')  

    def _patron3(self):
        print("Patron 3")
        if arduino: arduino.write(b't')  



    def _abrir_iluminacion(self):
        ventana_simple = tk.Toplevel(self.root)
        ventana_simple.title("Selección de Iluminación")
        ventana_simple.geometry("420x220")
        ventana_simple.configure(bg=self.COL_BG)
        ventana_simple.transient(self.root)
        ventana_simple.grab_set()

        tk.Label(
            ventana_simple,
            text="Iluminación de la terapia",
            font=("Segoe UI", 14, "bold"),
            bg=self.COL_BG, fg=self.COL_TEXT
        ).pack(pady=(20, 10))

        # --- Contenedor para los botones de color y patrones ---
        btns = tk.Frame(ventana_simple, bg=self.COL_BG)
        btns.pack(fill="x", padx=40, pady=10)

        # Botones principales (2 columnas)
        self._button(
            btns,
            "🎨 Colores",
            self._abrir_ventana_colores,
            primary=True
        ).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self._button(
            btns,
            "✨ Patrones",
            self._abrir_ventana_Patrones,
            primary=True
        ).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Hacer columnas de igual ancho y expansión simétrica
        btns.grid_columnconfigure(0, weight=1, uniform="ilum")
        btns.grid_columnconfigure(1, weight=1, uniform="ilum")

        # --- Contenedor inferior (Instrucciones + Cerrar) ---
        bottom_frame = tk.Frame(ventana_simple, bg=self.COL_BG)
        bottom_frame.pack(pady=20)

        def _instrucciones():
            msg = (
                "Instrucciones de uso:\n\n"
                "Para seleccionar un color haga clic en 'Colores' y elija una paleta disponible. Inmediatamente la banda LED se iluminará con el color seleccionado.\n\n"
                "Si desea usar un patrón, haga clic en 'Patrones' y seleccione uno. La banda LED ejecutará el patrón correspondiente.\n\n"
                "Presione Aceptar para salir de esta ventana."
            )
            messagebox.showinfo("Instrucciones", msg, parent=ventana_simple)

        # --- Botones inferiores ---
        self._button(
            bottom_frame,
            "ℹ️  Instrucciones",
            _instrucciones,
            primary=False
        ).pack(side="left", padx=8)

        self._button(
            bottom_frame,
            "❌ Cerrar",
            ventana_simple.destroy,
            primary=False
        ).pack(side="left", padx=8)


    #Definicion de funciones para abrir las ventanas para colores y patrones
    def _abrir_ventana_colores(self):
        ventana_simple = tk.Toplevel(self.root)
        ventana_simple.title("Seleccion de Colores")
        ventana_simple.geometry("600x350")
        ventana_simple.configure(bg=self.COL_BG)
        ventana_simple.transient(self.root)
        ventana_simple.grab_set()

        tk.Label(
            ventana_simple,
            text="Seleccione un Color para las luces de la terapia",
            font=("Segoe UI", 14, "bold"),
            bg=self.COL_BG, fg=self.COL_TEXT
        ).pack(pady=(16, 10))

        # --- Contenedor para botones de color (usamos grid aquí) ---
        btns = tk.Frame(ventana_simple, bg=self.COL_BG)
        btns.pack(fill="x", padx=32, pady=6)

        # Definición de botones (texto, callback)
        opciones = [
            ("Blanco",        self._blanco),
            ("Morado",        self._morado),
            ("Celeste",       self._celeste),
            ("Rojo Pastel",   self._rojopast),
            ("Azul",          self._azul),
            ("Amarillo",      self._amarillo),
        ]

        # Colocar en 2 columnas
        for i, (texto, cmd) in enumerate(opciones):
            r, c = divmod(i, 2)  # fila, columna (0 o 1)
            btn = self._button(btns, f"  {texto}  ", cmd, primary=True)
            btn.grid(row=r, column=c, padx=8, pady=8, sticky="ew")

        # Hacer columnas de igual ancho y expansibles
        btns.grid_columnconfigure(0, weight=1, uniform="colores")
        btns.grid_columnconfigure(1, weight=1, uniform="colores")

        # --- Fila inferior (usa pack, distinto contenedor) ---
        bottom_frame = tk.Frame(ventana_simple, bg=self.COL_BG)
        bottom_frame.pack(pady=20)

        self._button(
            bottom_frame,
            "❌ Cerrar",
            ventana_simple.destroy,
            primary=False
        ).pack(side="left", padx=8)

    def _abrir_ventana_Patrones(self):
        ventana_simple = tk.Toplevel(self.root)
        ventana_simple.title("Selección de Patrones")
        ventana_simple.geometry("500x220")
        ventana_simple.configure(bg=self.COL_BG)
        ventana_simple.transient(self.root)
        ventana_simple.grab_set()

        tk.Label(
            ventana_simple,
            text="Seleccione un Patrón para las luces de la terapia",
            font=("Segoe UI", 14, "bold"),
            bg=self.COL_BG, fg=self.COL_TEXT
        ).pack(pady=(20, 10))

        # --- Contenedor para los botones (usa grid con 3 columnas) ---
        btns = tk.Frame(ventana_simple, bg=self.COL_BG)
        btns.pack(fill="x", padx=40, pady=10)

        patrones = [
            ("Patrón 1", self._patron1),
            ("Patrón 2", self._patron2),
            ("Patrón 3", self._patron3)
        ]

        for i, (texto, cmd) in enumerate(patrones):
            btn = self._button(btns, texto, cmd, primary=True)
            btn.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

        # Hacer columnas de igual ancho y expandibles
        for i in range(3):
            btns.grid_columnconfigure(i, weight=1, uniform="patrones")

        # --- Fila inferior: Instrucciones y Cerrar ---
        bottom_frame = tk.Frame(ventana_simple, bg=self.COL_BG)
        bottom_frame.pack(pady=20)

        self._button(
            bottom_frame,
            "ℹ️  Instrucciones",
            lambda: messagebox.showinfo(
                "Instrucciones",
                (
                    "Seleccione un patrón para controlar la secuencia de luces:\n\n"
                    "• Patrón 1: alternancia rápida de colores.\n"
                    "• Patrón 2: transición suave.\n"
                    "• Patrón 3: ritmo de respiración.\n\n"
                    "Presione Aceptar para salir de esta ventana."
                ),
                parent=ventana_simple
            ),
            primary=False
        ).pack(side="left", padx=8)

        self._button(
            bottom_frame,
            "❌ Cerrar",
            ventana_simple.destroy,
            primary=False
        ).pack(side="left", padx=8)


    def _tick(self):
        if hasattr(self, "start_time") and hasattr(self, "time_lbl"):
            el = int(time.time() - self.start_time)
            m, s = divmod(el, 60)
            self.time_lbl.configure(text=f"⏱️ Tiempo transcurrido: {m:02d}:{s:02d}")
            self.root.after(1000, self._tick)

    # ------------------------------- Cierre / Encuesta final para TERAPIA INICIAL -------------------------------
    def _finish_terapia_inicial(self, auto=False):
        """Cierre específico para terapia inicial que guarda en base de datos"""
        elapsed = int(time.time() - getattr(self, "start_time", time.time()))
        self._close_dialog_terapia_inicial(elapsed, auto)
        print("Apagando Luces")
        if arduino: arduino.write(b'k') 

    def _close_dialog_terapia_inicial(self, elapsed, auto_trig):
        """Diálogo de cierre para terapia inicial que guarda en BD"""
        m, s = divmod(elapsed, 60); dur = f"{m:02d}:{s:02d}"
        dlg = tk.Toplevel(self.root); dlg.title("Cierre de Sesión Terapéutica")
        dlg.transient(self.root); dlg.grab_set(); dlg.geometry("820x720"); dlg.minsize(720,620)
        dlg.configure(bg=self.COL_BG); dlg.resizable(True, True)
        outer = tk.Frame(dlg, bg=self.COL_BG); outer.pack(expand=True, fill="both", padx=16, pady=12)
        card  = tk.Frame(outer, bg=self.COL_CARD, highlightbackground=self.COL_BORDER, highlightthickness=1)
        card.pack(expand=True, fill="both")
        tk.Label(card, text="Cierre de Sesión – Encuesta Final", font=("Segoe UI",18,"bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).pack(pady=(14,4))
        tk.Label(card, text=f"Duración registrada: {dur}" + (" (auto)" if auto_trig else ""),
                 font=("Segoe UI",11), bg=self.COL_CARD, fg=self.COL_MUTED).pack()
        body = tk.Frame(card, bg=self.COL_CARD, highlightbackground=self.COL_BORDER, highlightthickness=1)
        body.pack(expand=True, fill="both", padx=16, pady=14)
        body.grid_columnconfigure(0, weight=2, minsize=360)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(5, weight=1)
        def v_letras(P): return re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ ]*", P or "") is not None
        vcmd = (self.root.register(v_letras), '%P')
        
        # NOMBRE LIMPIO - SOLO EL NOMBRE
        nombre_completo = f"{self.demographics.get('nombre', '')}"  # SOLO NOMBRE
        
        tk.Label(body, text="Paciente:", font=("Segoe UI",11,"bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).grid(row=0, column=0, sticky="w", padx=10, pady=(10,6))
        tk.Label(body, text=nombre_completo, font=("Segoe UI",11),
                 bg=self.COL_CARD, fg=self.COL_MUTED).grid(row=0, column=1, sticky="w", padx=(10,12), pady=(10,6))
        
        tk.Label(body, text="1) ¿Cómo te sientes al terminar la \nsesión?", wraplength=360, justify="left", anchor="w",
                 font=("Segoe UI",11,"bold"), bg=self.COL_CARD, fg=self.COL_TEXT).grid(row=1, column=0, sticky="nw", padx=10, pady=(6,4))
        q1 = tk.Text(body, wrap="word", height=3, bg=self.COL_INPUT, fg=self.COL_INPUT_TX,
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B, font=("Segoe UI",11))
        q1.grid(row=1, column=1, sticky="ew", padx=(10,12), pady=(6,4))
        tk.Label(body, text="2) ¿Qué fue lo más valioso para ti hoy en la \nsesión?", wraplength=360, justify="left", anchor="w",
                 font=("Segoe UI",11,"bold"), bg=self.COL_CARD, fg=self.COL_TEXT).grid(row=2, column=0, sticky="nw", padx=10, pady=(6,4))
        q2 = tk.Text(body, wrap="word", height=3, bg=self.COL_INPUT, fg=self.COL_INPUT_TX,
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B, font=("Segoe UI",11))
        q2.grid(row=2, column=1, sticky="ew", padx=(10,12), pady=(6,4))
        tk.Label(body, text="3) ¿Has implementado en casa algún recurso utilizado en la terapia?", wraplength=360, justify="left", anchor="w",
                 font=("Segoe UI",11,"bold"), bg=self.COL_CARD, fg=self.COL_TEXT).grid(row=3, column=0, sticky="nw", padx=10, pady=(6,4))
        q3 = tk.Text(body, wrap="word", height=3, bg=self.COL_INPUT, fg=self.COL_INPUT_TX,
                     relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B, font=("Segoe UI",11))
        q3.grid(row=3, column=1, sticky="ew", padx=(10,12), pady=(6,4))
        tk.Label(body, text="Comentarios finales:", font=("Segoe UI",11,"bold"),
                 bg=self.COL_CARD, fg=self.COL_TEXT).grid(row=4, column=0, sticky="nw", padx=10, pady=(6,10))
        comments = tk.Text(body, wrap="word", height=6, bg=self.COL_INPUT, fg=self.COL_INPUT_TX,
                           relief="solid", bd=1, highlightthickness=1, highlightbackground=self.COL_INPUT_B, font=("Segoe UI",11))
        comments.grid(row=4, column=1, sticky="nsew", padx=(10,12), pady=(6,10))
        btns = tk.Frame(card, bg=self.COL_CARD); btns.pack(pady=10)
        save = self._button(btns, "💾 Guardar en Base de Datos", lambda: None)
        cancel = self._button(btns, "Cancelar (volver al menú)", lambda: [dlg.destroy(), self._reset()], primary=False)
        save.pack(side="left", padx=8); cancel.pack(side="left", padx=8)
        
        def form_ok():
            return (q1.get("1.0","end").strip() or q2.get("1.0","end").strip() or 
                   q3.get("1.0","end").strip() or comments.get("1.0","end").strip())
        
        def update_state(*_): 
            save.configure(state="normal" if form_ok() else "disabled")
        
        for widget in (q1, q2, q3, comments): 
            widget.bind("<KeyRelease>", update_state)
        update_state()
        
        def do_save():
            # Guardar en base de datos
            try:
                db_path = os.path.join(self.base_path, 'terapia_seguimientos.db')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO terapia_inicial (
                        paciente_id, paciente_nombre, genero, edad, tipo_documento,
                        perfil_sugerido, modulos_recomendados, playlists, duracion_sesion,
                        sensacion_post_sesion, mas_valioso, recursos_implementados, comentarios_finales
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.demographics.get('num_doc_pac', ''),
                    nombre_completo,  # NOMBRE LIMPIO
                    self.demographics.get('genero', ''),
                    self.demographics.get('edad', ''),
                    self.demographics.get('tipo_doc_pac', ''),
                    str(self.profile_infer),
                    ', '.join(self.modules_selected),
                    ', '.join([p[0] for p in self.plan_playlists]),
                    dur,
                    q1.get("1.0","end").strip(),
                    q2.get("1.0","end").strip(),
                    q3.get("1.0","end").strip(),
                    comments.get("1.0","end").strip()
                ))
                
                conn.commit()
                conn.close()
                
                # También guardar en txt como respaldo
                data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "name": nombre_completo,  # NOMBRE LIMPIO
                    "duration": dur,
                    "auto_finish": "Sí" if auto_trig else "No",
                    "q1": q1.get("1.0","end").strip(),
                    "q2": q2.get("1.0","end").strip(),
                    "q3": q3.get("1.0","end").strip(),
                    "comments_final": comments.get("1.0","end").strip(),
                    "plan_playlists": [p[0] for p in self.plan_playlists],
                    "perfil_sugerido": self.profile_infer,
                    "modulos_recomendados": self.modules_selected,
                    **self.demographics
                }
                path = self._save_txt(data)
                
                dlg.destroy()
                messagebox.showinfo("Sesión guardada", f"✅ Datos guardados en base de datos\n📄 Respaldo en: {path}")
                self._reset()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar en la base de datos: {str(e)}")
        
        save.configure(command=do_save)

    # ------------------------------- Persistencia -------------------------------
    def _save_txt(self, data: dict) -> str:
        folder = os.path.join(self.base_path, "sesiones"); os.makedirs(folder, exist_ok=True)
        safe = "".join(ch for ch in data["name"] if ch.isalnum() or ch in (" ","_","-")).strip() or "Paciente"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{safe.replace(' ','_')}_{ts}.txt")
        lines = [
            "=== Registro de Sesión Terapéutica ===",
            f"Fecha/Hora: {data['timestamp']}",
            f"Paciente: {data['name']}",
            f"Duración: {data['duration']} (auto: {data['auto_finish']})",
            "", "-- Demográficos --",
            f"Género: {data.get('genero')}",
            f"Edad: {data.get('edad')}",
            f"Tipo doc. (paciente): {data.get('tipo_doc_pac')}",
            f"N° doc. (paciente): {data.get('num_doc_pac')}",
            f"Menor de edad: {'Sí' if data.get('menor') else 'No'}"
        ]
        if data.get('menor'):
            lines += ["-- Datos de acudiente --",
                      f"Nombre: {data.get('acudiente_nombre')}",
                      f"Celular: {data.get('acudiente_cel')}",
                      f"Parentesco: {data.get('acudiente_parentesco')}",
                      f"Tipo doc. (acudiente): {data.get('tipo_doc_acu')}",
                      f"N° doc. (acudiente): {data.get('num_doc_acu')}"]
        lines += ["", "-- Recomendación de cuadro clínico (NO diagnóstico) --"]
        perfil = data.get("perfil_sugerido") or []
        if perfil: lines += [f"• {n}: {sev}" for n, sev in perfil]
        else: lines.append("(sin hallazgos destacados)")
        mods = data.get("modulos_recomendados") or []
        lines += ["", "-- Módulos recomendados (resumen) --"]
        if mods: lines += [f"• {m}: {self.MODULES.get(m, '')}" for m in mods]
        else: lines.append("(no se recomendaron módulos)")
        lines += ["", "-- Cierre --", "Respuestas de encuesta final:",
                  f"1) ¿Cómo te sientes al terminar la sesión?: \"{data.get('q1', '')}\"",
                  f"2) ¿Qué fue lo más valioso para ti hoy en la sesión?: \"{data.get('q2', '')}\"",
                  f"3) ¿Has implementado en casa algún recurso utilizado en la terapia?: \"{data.get('q3', '')}\"",
                  "Comentarios finales:", data.get('comments_final') or "(sin comentarios)", "",
                  "-- Playlists recomendadas --"]
        for p in (data.get('plan_playlists') or []): lines.append(f"• {p}")
        with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        return path

    def _reset(self):
        self.current = 0; self.answers = {}; self.plan_text = ""; self.plan_playlists = []
        self.demographics = {}; self.profile_infer = []; self.modules_selected = []
        self._home()

    # ------------------------------- Pantalla de selección de vídeo -------------------------------
    def _abrir_ventana_video(self):
        import tkinter as tk
        import os, random, subprocess, platform, sys
        from tkinter import messagebox
        from pathlib import Path
        from shutil import which

        ventana_simple = tk.Toplevel(self.root)
        ventana_simple.title("Reproducción de Video")
        ventana_simple.geometry("400x220")
        ventana_simple.configure(bg=self.COL_BG)
        ventana_simple.transient(self.root)
        ventana_simple.grab_set()

        tk.Label(
            ventana_simple,
            text="Reproducción automática de video",
            font=("Segoe UI", 14, "bold"),
            bg=self.COL_BG,
            fg=self.COL_TEXT
        ).pack(pady=20)

        def __locate_vlc() -> str | None:
            system = platform.system()
            candidates = []
            if system == "Windows":
                for name in ("vlc", "vlc.exe"):
                    p = which(name)
                    if p:
                        return p
                candidates += [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                ]
                base_dir = Path(getattr(sys, "_MEIPASS", Path.cwd()))
                candidates += [
                    str(base_dir / "vlc" / "vlc.exe"),
                    str(base_dir / "VLC" / "vlc.exe"),
                    str(base_dir / "vlc.exe"),
                ]
            elif system == "Darwin":
                p = which("vlc")
                if p:
                    return p
                candidates += [
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                    "/usr/local/bin/vlc",
                    "/opt/homebrew/bin/vlc",
                ]
            else:
                p = which("vlc")
                if p:
                    return p
                candidates += [
                    "/usr/bin/vlc",
                    "/usr/local/bin/vlc",
                    "/snap/bin/vlc",
                    "/flatpak/exports/bin/org.videolan.VLC",
                ]

            for c in candidates:
                if Path(c).exists():
                    return c
            return None

        def reproducir_video_loop():
            from pathlib import Path
            import platform, subprocess, os, random
            from tkinter import messagebox

            color = self.color_terapia

            if not color:   
                messagebox.showwarning("Aviso","Por favor, seleccione un color o patrón antes de reproducir un vídeo.")  
                return

            #base_dir = Path(getattr(sys, "_MEIPASS", Path.cwd()))

            # >>> Base del proyecto: carpeta REAL del .py (o del .exe si es PyInstaller)
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                base_dir = Path(sys._MEIPASS)                # cuando está empacado
            else:
                base_dir = Path(__file__).resolve().parent   # carpeta donde vive este .py

            carpeta_videos = base_dir / "videos" / color
            extensiones = (".mp4", ".avi", ".mov", ".mkv")

            if not carpeta_videos.exists():
                messagebox.showwarning(
                    "Carpeta no encontrada",
                    f"No existe la carpeta de videos:\n{carpeta_videos}"
                )
                return

            videos = [
                p for p in carpeta_videos.iterdir()
                if p.is_file() and p.suffix.lower() in extensiones and p.stem.isdigit()
            ]

            if not videos:
                messagebox.showwarning(
                    "Sin videos",
                    f"No se encontraron archivos de video en la carpeta /videos. {color}"
                )
                return

            video = random.choice(videos)
            video_path = str(video.resolve())

            vlc_path = __locate_vlc()
            if vlc_path:
                try:
                    vlc_dir = Path(vlc_path).parent
                    env = os.environ.copy()
                    env["VLC_PLUGIN_PATH"] = str(vlc_dir / "plugins")

                    args = [
                        vlc_path,
                        "--fullscreen",
                        "--loop",
                        "--no-video-title-show",
                        video_path
                    ]

                    creationflags = 0
                    if platform.system() == "Windows":
                        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)

                    subprocess.Popen(
                        args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        cwd=str(vlc_dir),
                        creationflags=creationflags
                    )

                    ventana_simple.destroy()
                    return
                except Exception as e:
                    messagebox.showwarning("VLC falló", f"No se pudo lanzar VLC:\n{e}\n\nSe intentará con el reproductor por defecto.")

            sistema = platform.system()
            try:
                if sistema == "Windows":
                    os.startfile(video_path)
                elif sistema == "Darwin":
                    subprocess.Popen(["open", video_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["xdg-open", video_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                messagebox.showerror("Error al abrir el video", str(e))
                return

            ventana_simple.destroy()




         # --- Botón principal: reproducir ---
        self._button(
            ventana_simple,
            f"🎥 Reproducir la paleta de color: {self.color_terapia}",
            reproducir_video_loop,
            primary=True
        ).pack(anchor="w", pady=(20, 0), padx=40)

        # --- Contenedor horizontal para los botones de Instrucciones y Cerrar ---
        bottom_frame = tk.Frame(ventana_simple, bg=self.COL_BG)
        bottom_frame.pack(pady=20)


        def _instrucciones():
            msg = (
                "Instrucciones de uso:\n\n"
                "Asegúrese de haber seleccionado un color en la ventana de colores.\n\n"
                "Una vez seleccionado el color, haga clic en 'Reproducir la paleta de color'. Seguido, se ejecutará el vídeo en bucle en pantalla completa correspondiente a la paleta seleccionada.\n\n"
                "Para salir, oprima la tecla ESC en su teclado y cierre manualmente el reproductor multimedia.\n\n\n"
                "NOTA: Los vídeos se eligen al azar dentro de la carpeta del color.\n\n"
                "Presione Aceptar para salir de esta ventana."
            )
            messagebox.showinfo("Instrucciones", msg, parent=ventana_simple)
        
        # --- Botón Instrucciones ---
        self._button(
            bottom_frame,
            "ℹ️  Instrucciones",
            _instrucciones,
            primary=False
        ).pack(side="left", padx=8)


        # --- Botón Cerrar ---
        self._button(
            bottom_frame,
            "❌ Cerrar",
            ventana_simple.destroy,
            primary=False
        ).pack(side="left", padx=8)


# ------------------------------- Punto de entrada -------------------------------
if __name__ == "__main__":
    App().root.mainloop()