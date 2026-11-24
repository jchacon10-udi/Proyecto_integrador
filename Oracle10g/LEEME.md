# Conexión con el servidor Oracle 10g de la universidad

El servidor de la universidad es **Oracle Database 10g 10.2.0.1** (SID `orcl`, puerto 1521). La librería `python-oracledb` tiene dos modos:

| Modo | Necesita | Conecta a |
|---|---|---|
| thin (por defecto) | nada | Oracle 12.1 o superior |
| thick | Oracle Instant Client | según la versión del cliente |

Oracle 10g **solo** funciona en modo thick, y con **Instant Client 11.2**: los clientes 12c o superiores no soportan servidores 10.2.0.1. El backend activa el modo thick cuando la variable `ORACLE_CLIENTE` apunta a la carpeta del cliente.

## ¿En qué sistemas operativos?

Instant Client 11.2.0.4 existe para:

| Sistema | Paquete | Script |
|---|---|---|
| Windows 64 bits | `instantclient-basic-windows.x64-11.2.0.4.0.zip` | `instalar_cliente_windows.ps1` |
| macOS Intel | `instantclient-basic-macos.x64-11.2.0.4.0.zip` | `instalar_cliente_macos.sh` |
| macOS Apple Silicon (M1–M4) | el mismo paquete Intel, con Rosetta 2 y Python x86_64 | `instalar_cliente_macos.sh` |
| Linux x86_64 | `instantclient-basic-linux.x64-11.2.0.4.0.zip` | manual (ver más abajo) |

Oracle **no ofrece instalador** para Instant Client: es un `.zip`. Para descargar la versión 11.2 hay que iniciar sesión con una cuenta gratuita de Oracle, por eso el `.zip` no está en este repositorio (su licencia tampoco permite publicarlo aquí). Los scripts hacen todo lo demás.

## Pasos

1. Conéctese a la red de la universidad (el servidor `192.168.254.215` solo responde desde allí).
2. Descargue el paquete **Basic** 11.2.0.4.0 de su sistema y déjelo en la carpeta Descargas:
   - Windows: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
   - macOS: https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html
3. Ejecute el script desde la raíz del repositorio:

   **Windows (PowerShell):**
   ```
   powershell -ExecutionPolicy Bypass -File Oracle10g\instalar_cliente_windows.ps1
   ```
   **macOS (Terminal):**
   ```
   bash Oracle10g/instalar_cliente_macos.sh
   ```
4. El script pide la contraseña del usuario de base de datos sin mostrarla, escribe `Codigo/backend/.env` (excluido de Git) y ejecuta `probar_conexion.py`. El resultado esperado es:
   ```
   Modo thick · Instant Client 11.2.0.4.0 en ...
   Conectado como ENPH_APP · servidor Oracle 10.2.0.1.0
   Objetos del esquema ENPH: N válidos, 0 inválidos
   ```
5. Inicie el backend con el comando que muestra el script y el frontend como siempre (`npm run dev`).

Parámetros opcionales: servidor, puerto, SID, usuario y esquema. Por defecto son `192.168.254.215`, `1521`, `orcl`, `ENPH_APP` y `ENPH`.
- Windows: `-Servidor`, `-Puerto`, `-Sid`, `-Usuario`, `-Esquema`.
- macOS: variables `ENPH_SERVIDOR`, `ENPH_PUERTO`, `ENPH_SID`, `ENPH_USUARIO`, `ENPH_ESQUEMA`.

Si en el servidor solo existe el usuario dueño `ENPH`, use `-Usuario ENPH` (Windows) o `ENPH_USUARIO=ENPH bash Oracle10g/instalar_cliente_macos.sh` (macOS).

## Notas por sistema

**Windows.** Instant Client 11.2 exige el *Microsoft Visual C++ 2005 SP1 Redistributable (x64)*; el script avisa si falta. Python debe ser de 64 bits.

**macOS Apple Silicon.** Oracle no publicó Instant Client 11.2 para arm64. El script:
- Usa la versión Intel con Rosetta 2.
- Crea un entorno virtual aparte, `Codigo/backend/.venv-x86`, con Python x86_64; el Python universal de python.org sirve.
- Enlaza las bibliotecas en `~/lib`, donde macOS las busca.

El backend se inicia con:
```
arch -x86_64 .venv-x86/bin/uvicorn app.main:create_app --factory --port 8000
```

**Linux.**
1. Descomprima el `.zip` en `/opt/oracle`.
2. Instale `libaio1`.
3. Cree `Codigo/backend/.env` a partir de `.env.example`, con `ORACLE_CLIENTE=/opt/oracle/instantclient_11_2`.

## Errores frecuentes

| Error | Causa y solución |
|---|---|
| `DPI-1047: Cannot locate a 64-bit Oracle Client library` | `ORACLE_CLIENTE` mal escrito, Python de 32 bits o (Windows) falta el runtime de Visual C++ 2005. |
| `DPY-3010: connections to this database server version are not supported` | Se usó el modo thin: falta `ORACLE_CLIENTE` en `.env`. |
| `ORA-12170` / `ORA-12541` | No hay red hacia el servidor: confirme la conexión a la red de la universidad. |
| `ORA-12505` | El SID no es `orcl`: pregunte el SID o use el alias TNS del laboratorio. |
| `ORA-01017` | Usuario o contraseña incorrectos. |
| macOS: `Failed building wheel for cryptography` | Versión vieja del script: actualice el repositorio (`git pull`). El script instala `cryptography<49`, la última con paquete x86_64. |
| `ORA-00942` al iniciar el backend | El usuario no ve los objetos de ENPH: ejecute `BaseDeDatos/07_roles_privilegios.sql` o conéctese como `ENPH`. |
