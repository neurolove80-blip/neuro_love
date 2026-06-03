# NeuroClick - Django Enrollment Management App

## Setup (exact order)
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py crear_superuser   # creates user "Guadalupe" / "neuro123"
python manage.py runserver 8080     # NOT port 8000
```

## Architecture
- **Django app** with one app: `matriculas`
- **Project config**: `mi_proyecto/settings.py`
- **SQLite DB**: `db.sqlite3`
- **Templates**: `matriculas/templates/matriculas/`
- **No tests** currently exist

## Key Models
| Model | Purpose |
|---|---|
| `PerfilUsuario` | Links User to rol (`psicologo` or `profesor`) |
| `ProcesoPsicologico` | Student psychological processes |
| `ConsejoProceso` | Teacher advice on processes |
| `Libro` | Digital library books |
| `TemaForo` / `RespuestaForo` | Forum topics and replies |

## Role-Based Access
- **Psicólogo**: Full CRUD on procesos, libros, temas (and delete)
- **Profesor**: Can view procesos, add consejos, create forum topics
- Check role via `user.perfil.es_psicologo()` (defined in `views.py:es_psicologo`)

## Custom Management Command
`python manage.py crear_superuser` - Idempotent (safe to re-run), creates Guadalupe with psicologo profile.

## Server
- Port **8080** (README explicitly requires this to avoid conflicts)
- Login URL: `/login/` → redirects to `/` on success
- Admin at `/admin/`

## Language
- UI and Django config in Spanish (`LANGUAGE_CODE = 'es-co'`)
