# NeuroClick

## Pasos para ejecutar

```bash
# 1. Instalar dependencias
pip install django

# 2. Crear las tablas
python manage.py migrate

# 3. Crear usuario Guadalupe (automático)
python manage.py crear_superuser

# 4. Iniciar servidor  ← usa puerto 8080 para evitar conflictos
python manage.py runserver 8080
```

Luego entra a: http://127.0.0.1:8080

## Credenciales
| Usuario | Contraseña |
|---|---|
| Guadalupe | neuro123 |

## Si el puerto 8080 también está ocupado
```bash
python manage.py runserver 8001
```
