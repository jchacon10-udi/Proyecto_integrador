#!/usr/bin/env bash
# Inicia el backend ENPH en macOS con el Oracle Instant Client 11.2 que instaló instalar_cliente_macos.sh.
# Uso: bash Oracle10g/iniciar_backend_macos.sh [opciones extra de uvicorn, p. ej. --reload]
set -euo pipefail
BACKEND="$(cd "$(dirname "$0")/.." && pwd)/Codigo/backend"
cd "$BACKEND"
CLIENTE=$(sed -n 's/^ORACLE_CLIENTE=//p' .env 2>/dev/null | tail -1)
[ -n "$CLIENTE" ] || { echo "Falta ORACLE_CLIENTE en $BACKEND/.env: ejecute Oracle10g/instalar_cliente_macos.sh"; exit 1; }
# El cliente 11.2 abre libociei.dylib solo por nombre (ORA-01804 si no lo encuentra); arch borra DYLD_*, por eso -e.
exec arch -x86_64 -e DYLD_FALLBACK_LIBRARY_PATH="$CLIENTE:/usr/local/lib:/usr/lib" \
  .venv-x86/bin/uvicorn app.main:create_app --factory --port 8000 "$@"
