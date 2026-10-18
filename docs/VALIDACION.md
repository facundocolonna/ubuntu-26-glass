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

## Versión 1.1.0: escritorios al maximizar

El mismo día se agregó ScreenToSpace 15, descargado del catálogo oficial de
extensiones GNOME, y se desactivó `isolate-workspaces` de Dash to Panel.
No se agregan dependencias APT para esta extensión.

Prueba en GNOME separado, con las cinco extensiones activas y ventanas reales
del ayudante de pruebas de GNOME:

- Maximizar una de dos ventanas la separa en otro escritorio y lo activa.
- La otra ventana conserva su escritorio de origen.
- La lista de ventanas utilizada por la barra incluye las de ambos escritorios.
- Restaurar la ventana la devuelve al escritorio de origen y lo activa.
- Ponerla en pantalla completa no cambia de escritorio con este perfil.
- Volver a maximizarla y cerrarla regresa al escritorio de origen.

Estas comprobaciones no requieren reiniciar la sesión real del usuario.

## Versión 1.2.0: varias pantallas

Se corrigieron los contenedores de Desktop Icons NG que aparecían como ventanas,
la herencia del diseño en una pantalla sin configuración y el indicador de
CPU/RAM en barras secundarias. El selector de foco libera sus actores al
reconstruir las barras. Se mantiene la pantalla principal seleccionada en GNOME.

Prueba con GNOME y tres pantallas virtuales de 1280×720, 1024×768 y 1600×900:

- Las tres pantallas, sin identificadores configurados, heredan aplicaciones
  centradas y el botón de aplicaciones oculto.
- Las tres barras muestran CPU/RAM, solo esas métricas, en el extremo izquierdo.
- Una ventana real marcada como superficie DING se excluye de la barra y de
  ScreenToSpace; al retirar la marca vuelve a tratarse como ventana normal.
- El paso de tres barras a una y luego a tres reconstruye los indicadores,
  con lecturas válidas y sin duplicarlos. Se usa la misma ruta de reconstrucción
  de Dash to Panel que ante cambios de monitor.

El diseño se aplicó también a las tres pantallas físicas conectadas del usuario.
La carga del código nuevo en esa sesión queda pendiente de cerrar sesión y
volver a entrar. Los registros del compositor de prueba incluyen avisos de la
extensión existente de esquinas al destruir una ventana del ayudante de prueba;
las comprobaciones de las barras y del monitor de sistema finalizaron correctamente.

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
