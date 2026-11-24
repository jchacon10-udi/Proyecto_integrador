#!/usr/bin/env bash
# Instala Oracle Instant Client 11.2 (macOS Intel x86_64) y deja el backend ENPH listo para conectarse
# al servidor Oracle 10g de la universidad.
#
# Oracle no publica Instant Client 11.2 para Apple Silicon (arm64). En un Mac M1/M2/M3/M4 se usa la
# versión Intel con Rosetta 2 y un Python x86_64 en un entorno virtual aparte (.venv-x86).
# Oracle no ofrece instalador: el .zip exige iniciar sesión (cuenta gratuita) para descargarlo.
#
# Uso:  bash Oracle10g/instalar_cliente_macos.sh [ruta/al/instantclient-basic-macos.x64-11.2.0.4.0.zip]
# Variables opcionales: ENPH_SERVIDOR, ENPH_PUERTO, ENPH_SID, ENPH_USUARIO, ENPH_ESQUEMA
set -euo pipefail

SERVIDOR=${ENPH_SERVIDOR:-192.168.254.215}
PUERTO=${ENPH_PUERTO:-1521}
SID=${ENPH_SID:-orcl}
USUARIO=${ENPH_USUARIO:-ENPH_APP}
ESQUEMA=${ENPH_ESQUEMA:-ENPH}
DESTINO="$HOME/oracle"
CLIENTE="$DESTINO/instantclient_11_2"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$REPO/Codigo/backend"
X86="arch -x86_64"

paso() { printf '\n== %s\n' "$1"; }

# 1. Rosetta ---------------------------------------------------------------------------------------
paso "Rosetta 2"
if [ "$(uname -m)" = "arm64" ]; then
  if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    softwareupdate --install-rosetta --agree-to-license
  fi
  echo "Disponible."
else
  X86=""
  echo "Mac Intel: no se necesita."
fi

# 2. Instant Client --------------------------------------------------------------------------------
paso "Oracle Instant Client 11.2"
ZIP=${1:-$(ls -t "$HOME"/Downloads/instantclient-basic-macos.x64-11.2*.zip 2>/dev/null | head -1 || true)}
if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
  echo "No se encontró instantclient-basic-macos.x64-11.2.0.4.0.zip en Descargas."
  echo "Descárguelo (requiere cuenta gratuita de Oracle) desde:"
  echo "  https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html"
  echo "  -> Version 11.2.0.4.0 -> Basic Package (y opcional SQL*Plus)"
  exit 1
fi
mkdir -p "$DESTINO"
unzip -oq "$ZIP" -d "$DESTINO"
# Los archivos vienen de solo lectura: sin permiso de escritura no se puede quitar la cuarentena
# y macOS muestra "No se abrió libclntsh.dylib.11.1".
chmod -R u+w "$CLIENTE"
xattr -dr com.apple.quarantine "$CLIENTE"
cd "$CLIENTE"
ln -sf libclntsh.dylib.11.1 libclntsh.dylib
ln -sf libocci.dylib.11.1 libocci.dylib
# Las bibliotecas 11.2 de macOS referencian rutas de compilación de Oracle (/ade/...).
# Se reescriben para que cada una busque sus dependencias en su misma carpeta.
for f in *.dylib* adrci genezi uidrvci; do
  [ -f "$f" ] && [ ! -L "$f" ] || continue
  otool -L "$f" | awk '/\/ade\//{print $1}' | while read -r dep; do
    install_name_tool -change "$dep" "@loader_path/$(basename "$dep")" "$f" 2>/dev/null
  done
  case "$f" in *.dylib*) install_name_tool -id "$CLIENTE/$f" "$f" 2>/dev/null || true ;; esac
done
$X86 ./genezi -v | grep -q "Instant Client mode" || { echo "Instant Client no quedó operativo"; exit 1; }
echo "Instant Client en $CLIENTE"

# 3. Python x86_64 y entorno virtual ---------------------------------------------------------------
paso "Python x86_64 y entorno virtual (.venv-x86)"
PY=$(command -v python3)
PY_REAL=$(python3 -c 'import sys, os; print(os.path.realpath(sys.executable))')
if [ -n "$X86" ] && ! lipo -archs "$PY_REAL" 2>/dev/null | grep -q x86_64; then
  echo "$PY_REAL no incluye x86_64. Instale Python desde https://www.python.org/downloads/macos/ (universal2)."
  exit 1
fi
cd "$BACKEND"
[ -x .venv-x86/bin/python ] || $X86 "$PY_REAL" -m venv .venv-x86
$X86 .venv-x86/bin/python -m pip install --quiet --upgrade pip
# cryptography (dependencia de oracledb) dejó de publicar paquetes x86_64 para macOS en la versión 49;
# sin esta restricción pip intenta compilarla con Rust y falla bajo Rosetta.
$X86 .venv-x86/bin/python -m pip install --quiet --only-binary=:all: "cryptography<49"
$X86 .venv-x86/bin/python -m pip install --quiet --only-binary=cryptography -e ".[test]"

# 4. Archivo .env ----------------------------------------------------------------------------------
paso "Configuración (.env)"
read -r -s -p "Contraseña de $USUARIO en el servidor $SERVIDOR: " CLAVE; echo
[ -f .env ] && cp .env .env.anterior && echo "El .env anterior quedó en .env.anterior"
umask 077
cat > .env <<EOF
# Generado por Oracle10g/instalar_cliente_macos.sh. No se sube al repositorio.
ENPH_MODO=oracle
ORACLE_DSN=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$SERVIDOR)(PORT=$PUERTO))(CONNECT_DATA=(SID=$SID)))
ORACLE_USUARIO=$USUARIO
ORACLE_CLAVE=$CLAVE
ORACLE_ESQUEMA=$ESQUEMA
ORACLE_CLIENTE=$CLIENTE
EOF
echo "Escrito $BACKEND/.env"

# 5. Prueba de conexión ----------------------------------------------------------------------------
paso "Prueba de conexión"
# El cliente 11.2 abre libociei.dylib (zonas horarias) solo por nombre: sin esta ruta falla con ORA-01804.
# arch borra las variables DYLD_*, por eso se pasan con -e.
arch -x86_64 -e DYLD_FALLBACK_LIBRARY_PATH="$CLIENTE:/usr/local/lib:/usr/lib" .venv-x86/bin/python probar_conexion.py

printf '\nListo. Para iniciar el backend contra Oracle 10g:\n'
echo "  bash Oracle10g/iniciar_backend_macos.sh"
