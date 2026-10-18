# Validación de la versión inicial

Fecha: 18 de octubre de 2026.
Entorno de referencia: Ubuntu 26.04.1, GNOME Shell 50.1, Wayland, amd64,
Mutter `50.1-0ubuntu2.4`.

Comprobaciones completadas:

- Integridad de todos los archivos del manifiesto SHA-256 y validación de
  tipos y rangos del perfil contra los esquemas de GSettings incluidos.
- `./install.sh --check`: compatible; todos los paquetes necesarios presentes.
- Instalación en carpetas XDG temporales con un bus D-Bus privado y backend
  keyfile; verificación de todos los valores del perfil y del orden de activación.
- Reinstalación del mismo perfil y restauración de ambas copias: recupera
  archivos previos, elimina los agregados y restaura tanto valores explícitos
  como claves que antes no tenían un valor de usuario.
- Fallo provocado a mitad del reemplazo de archivos: la recuperación automática
  devolvió los archivos y ajustes al estado anterior.
- Compilación del fuente nativo incluido, generación del typelib y creación
  del paquete Debian con dependencia exacta del Mutter instalado. El paquete se
  generó sin instalarlo sobre el sistema de referencia.
- Compositor GNOME de prueba con las cuatro extensiones del repositorio:
  todas activas, desenfoque nativo detectado y CPU/RAM con valores numéricos
  en el extremo inferior izquierdo. Se probó también usando la biblioteca
  recién compilada mediante `LD_LIBRARY_PATH` y `GI_TYPELIB_PATH`.

La prueba gráfica se ejecutó sin reiniciar ni reemplazar la sesión del usuario.
El entorno headless emite avisos de servicios ausentes (IBus, permisos de
geolocalización y fondos de GNOME no incluidos en Ubuntu); no impidieron las
comprobaciones. No hubo errores JavaScript de las extensiones en la ejecución
final. No se ha probado una instalación desde cero de Ubuntu ni otra arquitectura.

## Repetir la compilación sin instalar el paquete

Después de instalar las dependencias de compilación de `PAQUETES.md`:

```bash
python3 - /ruta/temporal/nueva <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path('scripts').resolve()))
from native import build_package
print(build_package(Path.cwd(), Path(sys.argv[1]).resolve()))
PY
```

Usá una carpeta temporal nueva. No necesita sudo. Para instalar y configurar
normalmente, usá siempre `./install.sh`.
