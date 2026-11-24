# ENPH · Cuadernillo 2 urbano

Software para el registro y procesamiento del Cuadernillo 2 urbano (gastos diarios del hogar) de la Encuesta Nacional de Presupuestos de los Hogares. Proyecto Integrador, cuarto semestre de Ingeniería de Sistemas, UDI, 2026-II.

Arquitectura cliente-servidor con persistencia en Oracle:

| Carpeta | Contenido |
|---|---|
| `Codigo/backend` | API REST en Python (FastAPI): casos de uso CU-01 a CU-14, reglas de negocio y repositorios en memoria y Oracle |
| `Codigo/frontend` | Cliente web en React + TypeScript para los cuatro roles |
| `BaseDeDatos` | Scripts Oracle 10g: tablas, secuencias, disparadores, funciones, procedimientos, vistas, roles, datos y pruebas |
| `Oracle10g` | Instalación de Oracle Instant Client 11.2 (Windows y macOS) para conectar el backend al servidor Oracle 10g |

## Base de datos

Ejecutar en orden desde `BaseDeDatos` (Oracle 10g o superior):

```
sqlplus ENPH/<clave>@<servicio> @00_diagnostico.sql
sqlplus system/<clave>@<servicio> @00_crear_esquema_DBA.sql
sqlplus ENPH/<clave>@<servicio> @instalar.sql
```

`instalar.sql` genera `instalacion.log` y `pruebas.log`; el resultado esperado es `38 pasan, 0 fallan`. `00_crear_esquema_DBA.sql` pide las contraseñas de los usuarios al ejecutarse y no las guarda.

## Backend

Requiere Python 3.11 o superior.

```
cd Codigo/backend
python -m venv .venv
.venv/bin/pip install -e ".[test]"        # Windows: .venv\Scripts\pip
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

Modo de datos por variables de entorno (ver `Codigo/backend/.env.example`):

- `ENPH_MODO=memoria` (por defecto): datos de prueba en memoria, equivalentes a `08_datos_prueba.sql`.
- `ENPH_MODO=oracle`: esquema ENPH. Variables `ORACLE_DSN`, `ORACLE_USUARIO` (ENPH_APP), `ORACLE_CLAVE`. Para Oracle 10g se requiere el modo thick: `ORACLE_CLIENTE` con la ruta de Oracle Instant Client 11.2.

### Servidor Oracle 10g de la universidad

Oracle 10g solo acepta el modo *thick* de python-oracledb con **Oracle Instant Client 11.2**, disponible para Windows x64, macOS (Intel, y Apple Silicon con Rosetta 2) y Linux x86_64. Oracle no publica instalador: el cliente es un `.zip` que se descarga con una cuenta gratuita de Oracle. Los scripts de [`Oracle10g/`](Oracle10g/LEEME.md) lo instalan, generan `.env` y prueban la conexión:

```
powershell -ExecutionPolicy Bypass -File Oracle10g\instalar_cliente_windows.ps1   # Windows
bash Oracle10g/instalar_cliente_macos.sh                                         # macOS
```

`python probar_conexion.py` (en `Codigo/backend`) verifica la conexión en cualquier momento. Instrucciones completas y errores frecuentes en [`Oracle10g/LEEME.md`](Oracle10g/LEEME.md).

Pruebas: `.venv/bin/python -m pytest`. Contra Oracle: agregar `ENPH_PRUEBAS_ORACLE=1` y las variables `ORACLE_*`; cada prueba se revierte al terminar.

## Frontend

Requiere Node.js 20 o superior.

```
cd Codigo/frontend
npm ci
npm run dev
```

Abrir http://127.0.0.1:5173. Cuentas de prueba (contraseña `enph-demo`): `pruiz` y `jgomez` (informantes), `ccastro` (encuestador), `mlopez` (supervisor), `acritico` (crítico-digitador).
