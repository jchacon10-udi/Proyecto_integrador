<#
.SYNOPSIS
  Instala Oracle Instant Client 11.2 (Windows x64) y deja el backend ENPH listo para conectarse
  al servidor Oracle 10g de la universidad.

.DESCRIPTION
  Oracle no publica instalador para Instant Client: se distribuye como un .zip que exige iniciar
  sesión (cuenta gratuita) para descargarlo. Este script hace el resto:
    1. Descomprime el .zip en C:\oracle\instantclient_11_2 (o en -Destino).
    2. Verifica el runtime de Visual C++ 2005 que exige Instant Client 11.2.
    3. Verifica que Python sea de 64 bits y crea el entorno virtual del backend.
    4. Escribe Codigo\backend\.env (pide la contraseña sin mostrarla; no se sube al repositorio).
    5. Prueba la conexión con probar_conexion.py.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Oracle10g\instalar_cliente_windows.ps1
  powershell -ExecutionPolicy Bypass -File Oracle10g\instalar_cliente_windows.ps1 -Zip C:\Descargas\instantclient-basic-windows.x64-11.2.0.4.0.zip -Usuario ENPH
#>
param(
  [string]$Zip,
  [string]$Destino = "C:\oracle",
  [string]$Servidor = "192.168.254.215",
  [int]$Puerto = 1521,
  [string]$Sid = "orcl",
  [string]$Usuario = "ENPH_APP",
  [string]$Esquema = "ENPH"
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Repo "Codigo\backend"

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# 1. Instant Client ------------------------------------------------------------------------------
Paso "Oracle Instant Client 11.2"
if (-not $Zip) {
  $Zip = Get-ChildItem "$env:USERPROFILE\Downloads\instantclient-basic*windows*x64*11.2*.zip" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Zip -or -not (Test-Path $Zip)) {
  Write-Host "No se encontró instantclient-basic-windows.x64-11.2.0.4.0.zip en Descargas." -ForegroundColor Yellow
  Write-Host "Descárguelo (requiere cuenta gratuita de Oracle) desde:"
  Write-Host "  https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html"
  Write-Host "  -> Version 11.2.0.4.0 -> Instant Client Package - Basic (y opcional SQL*Plus)"
  Write-Host "y vuelva a ejecutar este script (o use -Zip <ruta>)."
  exit 1
}
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
Expand-Archive -Path $Zip -DestinationPath $Destino -Force
$Cliente = Join-Path $Destino "instantclient_11_2"
if (-not (Test-Path (Join-Path $Cliente "oci.dll"))) { throw "No se encontró oci.dll en $Cliente" }
Write-Host "Instant Client en $Cliente"

# 2. Runtime de Visual C++ 2005 ------------------------------------------------------------------
Paso "Runtime de Visual C++ 2005 (x64)"
if (Get-ChildItem "$env:windir\WinSxS" -Directory -Filter "amd64_microsoft.vc80.crt*" -ErrorAction SilentlyContinue) {
  Write-Host "Encontrado."
} else {
  Write-Host "No se encontró. Instale 'Microsoft Visual C++ 2005 SP1 Redistributable (x64)' (vcredist_x64.exe):" -ForegroundColor Yellow
  Write-Host "  https://www.microsoft.com/en-us/download/details.aspx?id=26347"
  Write-Host "Sin él, Python muestra DPI-1047 al cargar oci.dll."
}

# 3. Python de 64 bits y entorno virtual ---------------------------------------------------------
Paso "Python y entorno virtual del backend"
$Py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$Bits = & $Py -c "import struct; print(struct.calcsize('P') * 8)"
if ($Bits -ne "64") { throw "Python es de $Bits bits; Instant Client x64 exige Python de 64 bits." }
$Venv = Join-Path $Backend ".venv"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) { & $Py -m venv $Venv }
$VPy = Join-Path $Venv "Scripts\python.exe"
Push-Location $Backend
& $VPy -m pip install --quiet --upgrade pip
& $VPy -m pip install --quiet -e ".[test]"
Pop-Location

# 4. Archivo .env --------------------------------------------------------------------------------
Paso "Configuración (.env)"
$Seguro = Read-Host "Contraseña de $Usuario en el servidor $Servidor" -AsSecureString
$Clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Seguro))
$Dsn = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$Servidor)(PORT=$Puerto))(CONNECT_DATA=(SID=$Sid)))"
$Env = Join-Path $Backend ".env"
if (Test-Path $Env) { Copy-Item $Env "$Env.anterior" -Force; Write-Host "El .env anterior quedó en .env.anterior" }
$Contenido = @"
# Generado por Oracle10g\instalar_cliente_windows.ps1. No se sube al repositorio.
ENPH_MODO=oracle
ORACLE_DSN=$Dsn
ORACLE_USUARIO=$Usuario
ORACLE_CLAVE=$Clave
ORACLE_ESQUEMA=$Esquema
ORACLE_CLIENTE=$Cliente
"@
[IO.File]::WriteAllText($Env, $Contenido, (New-Object Text.UTF8Encoding $false))  # UTF-8 sin BOM
Write-Host "Escrito $Env"

# 5. Prueba de conexión --------------------------------------------------------------------------
Paso "Prueba de conexión"
Push-Location $Backend
& $VPy probar_conexion.py
$Resultado = $LASTEXITCODE
Pop-Location
if ($Resultado -ne 0) { exit $Resultado }

Write-Host "`nListo. Para iniciar el backend contra Oracle 10g:" -ForegroundColor Green
Write-Host "  cd Codigo\backend"
Write-Host "  .venv\Scripts\uvicorn app.main:create_app --factory --port 8000"
