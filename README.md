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

## Instalación con Docker Compose

```bash
cp .env.example .env
```

Rellena `.env` (credenciales y carpetas de tu equipo) y arranca:

```bash
docker compose up -d --build
```

Los datos que genera (bases, cachés) se quedan en esta misma carpeta, fuera de git.

## Actualizaciones automáticas

El `docker-compose.yml` trae su propia [Ofelia](https://github.com/mcuadros/ofelia), que lanza dentro del contenedor los mismos trabajos y a las mismas horas que en REPEAT-ONE (formato con segundos: `seg min hora día mes día-semana`, hora de `TZ`, por defecto Europe/Madrid):

| Trabajo | Cuándo | Qué lanza |
|---|---|---|
| `mix-rater-scan` | `0 50 1 * * *` | `python3 music_rater.py scan /music` |

Para cambiar una hora, edita su etiqueta `ofelia.job-exec.<trabajo>.schedule` en `docker-compose.yml` y vuelve a hacer `docker compose up -d`. Para lanzarlo a mano: `docker compose exec <servicio> <orden>`. Para no tener actualizaciones automáticas: `docker compose stop ofelia`.

Esta Ofelia solo ve los contenedores de este repo (etiqueta `repeat-one.ofelia`), así que puedes tener varios módulos instalados por separado sin que se pisen. Necesita el socket de Docker en solo lectura.
