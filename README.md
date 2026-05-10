[README_habitacion_calma.md](https://github.com/user-attachments/files/27562905/README_habitacion_calma.md)
RECONEXION - Habitacion de la Calma

Sistema terapeutico de software desarrollado en Python para el control de un entorno de bienestar emocional orientado al manejo del estres, la ansiedad y la depresion. Desarrollado en colaboracion con profesionales en psicologia.

Descripcion

"Habitacion de la Calma" es un sistema clinico funcional que gestiona sesiones terapeuticas completas: desde el consentimiento informado y la evaluacion inicial del paciente, hasta el control de hardware en tiempo real (luces LED via Arduino), reproduccion de contenido audiovisual y registro de seguimientos en base de datos.

El sistema fue construido integro en Python con una interfaz grafica profesional, logica de negocio clinica y comunicacion serial con dispositivos fisicos.

Funcionalidades principales

- Pantalla de inicio y menu de programa con navegacion completa
- Consentimiento informado digital con lectura desde archivo .docx o texto de respaldo
- Registro de datos demograficos con validaciones (nombre, documento, edad, acudiente si es menor)
- Cuestionario clinico de 10 preguntas con motor de reglas para recomendar modulos terapeuticos
- Generacion automatica de plan terapeutico personalizado segun respuestas
- Control de luces LED RGB en tiempo real (6 colores + 3 patrones) via comunicacion serial con Arduino
- Reproduccion automatica de videos terapeuticos en VLC segun el color de terapia seleccionado
- Integracion con Spotify para apertura de playlists terapeuticas recomendadas
- Timer de sesion en tiempo real
- Encuesta de cierre de sesion con guardado en base de datos SQLite
- Modulo de terapia de seguimiento con cuestionario de estado semanal del paciente
- Base de datos SQLite con dos tablas (terapia_inicial y seguimientos)
- Visor de base de datos con buscador por nombre o documento y filtros por tipo de terapia
- Ver detalle completo de cada registro y eliminar registros con confirmacion
- Exportacion de sesiones a archivo .txt como respaldo local
- Deteccion automatica del puerto COM del Arduino

Tecnologias utilizadas

| Tecnologia | Uso |
| Python 3 | Logica principal, motor de reglas, control de sesion |
| Tkinter | Interfaz grafica con multiples pantallas y navegacion |
| SQLite3 | Base de datos local para terapias iniciales y seguimientos |
| pyserial | Comunicacion serial con Arduino para control de LEDs |
| Arduino | Control fisico de luces LED RGB (colores y patrones) |
| VLC (via subprocess) | Reproduccion de videos terapeuticos en bucle y pantalla completa |
| python-docx | Lectura del consentimiento informado desde archivo Word |
| Pillow (PIL) | Carga y visualizacion de imagenes en la interfaz |
| subprocess / webbrowser | Apertura de playlists en Spotify |

Arquitectura del sistema

[Interfaz Grafica Tkinter - Multiples Pantallas]
        |
        v
[Motor de Reglas Clinicas]
  - Cuestionario 10 preguntas
  - Inferencia de perfil y modulos
  - Generacion de plan terapeutico
        |
        |-----> [Base de Datos SQLite]
        |         - terapia_inicial
        |         - seguimientos
        |         - Buscador y visor
        |
        |-----> [Modulo de Hardware]
        |         - Deteccion automatica del puerto Arduino
        |         - Control de 6 colores LED
        |         - Control de 3 patrones de luz
        |         - Comunicacion serial (pyserial)
        |
        |-----> [Modulo de Contenido]
                  - Videos terapeuticos por color (VLC)
                  - Playlists Spotify por modulo
                  - Imagen de ambiente relajante

Estructura del proyecto

habitacion-de-la-calma/
|
|-- main.py                          # Aplicacion principal
|-- CONSENTIMIENTO INFORMADO.docx    # Documento de consentimiento (opcional)
|-- logo.jpeg                        # Logo de la aplicacion
|-- terapia_seguimientos.db          # Base de datos SQLite (se genera automaticamente)
|
|-- videos/                          # Videos terapeuticos organizados por color
|   |-- blanco/
|   |-- celeste/
|   |-- azul/
|   |-- morado/
|   |-- rojo pastel/
|   |-- amarillo/
|
|-- sesiones/                        # Respaldos .txt de sesiones (se genera automaticamente)
|
|-- README.md
```

---

## Modulos terapeuticos implementados

| Modulo | Descripcion |
|---|---|
| HRV | Respiracion guiada a 6 rpm (0.1 Hz), 10-15 min |
| SONIDOS | Sonidos relajantes + visual de naturaleza |
| VIBRO | Vibroacustica 30-80 Hz, 20-25 min |
| LUZ_AM | Terapia de luz, 20-30 min por la manana |
| HIGIENE_SUENO | Rutina de sueno, luz calida, ruido rosa |
| ACT_CONDUCTUAL | Activacion conductual diaria |
| RMP | Relajacion muscular progresiva |

Los modulos se asignan automaticamente segun las respuestas del cuestionario mediante un motor de reglas basado en evidencia clinica.

Requisitos

pip install pyserial pillow python-docx

VLC Media Player instalado en el sistema para reproduccion de videos.
Arduino con firmware cargado para recibir comandos seriales de control de LEDs.

Como ejecutar

bash
python main.py

El sistema detecta automaticamente el puerto Arduino. Si no hay Arduino conectado, el software funciona igualmente en modo sin hardware.

Contexto del proyecto

Este sistema nacio de una colaboracion entre ingenieria electronica y psicologia con el objetivo de crear un espacio tecnologico de apoyo emocional accesible. Fue disenado para que profesionales de salud mental pudieran operar el sistema sin conocimientos tecnicos, priorizando la experiencia terapeutica del paciente.

El software gestiona el ciclo completo de una sesion: consentimiento, evaluacion, terapia activa, cierre y seguimiento longitudinal del paciente.

Mejoras futuras

- [ ] Autenticacion de usuario por rol (terapeuta / administrador)
- [ ] Sincronizacion de base de datos en la nube
- [ ] Control inalambrico del Arduino via Wi-Fi con ESP32
- [ ] Modulo de deteccion de emocion con camara integrado a la sesion
- [ ] Exportacion de reportes en PDF por paciente
- [ ] Dashboard de estadisticas de sesiones

Jairo Henao Hernandez
Armenia, Quindio, Colombia
jairohernandez753@gmail.com
