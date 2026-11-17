# mix_rater

Parte de [REPEAT-ONE](https://github.com/volteret4/repeat-one-web). Puntúa cada tema de tu
carpeta de mezclas en 12 dimensiones (alegre/melancólica, relajada/enérgica…) y busca
después temas parecidos por similitud entre esos vectores.

[Demo con datos reales](https://volteret4.github.io/repeat-one-web/demo/rater/)

- **Web** (`web/app.py`): puntuar, recomendaciones al azar o por vector, estadísticas.
- **CLI** (`music_rater.py`): escanear una carpeta y puntuar desde la terminal.

## Instalación

Con el instalador de REPEAT-ONE (módulo `mix_rater`), o a mano:

```bash
pip install -r requirements.txt
```

```bash
python music_rater.py scan /ruta/a/tu/carpeta/de/mezclas
```

```bash
python web/app.py --host 0.0.0.0 --port 5001
```

Configuración en `.env` (ver `.env.example`). La base de datos es un SQLite que se crea solo.
