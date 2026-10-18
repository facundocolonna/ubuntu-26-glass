# GNOME Glass

Configuración reproducible del escritorio que armamos el 18 de octubre de 2026.
Preparada para **Ubuntu 26.04, GNOME Shell 50 y Wayland**. Conserva GNOME y sus
gestos nativos.

## Instalar

Desde una terminal de tu sesión de escritorio, dentro de esta carpeta:

```bash
./install.sh
```

Ejecutalo **sin sudo**. El instalador usa `sudo` solamente para instalar los
paquetes APT y la biblioteca de desenfoque. Al terminar, guardá tu trabajo,
cerrá sesión y volvé a entrar para cargar el código nuevo de las extensiones.
No cierra la sesión automáticamente.

Para revisar la integridad, la compatibilidad y los paquetes pendientes:

```bash
./install.sh --check
./install.sh --dry-run
```

Estos dos modos no instalan paquetes ni escriben ajustes. Las extensiones,
temas y fuentes de la biblioteca están incluidas: no se descargan versiones
variables de Internet. APT necesita acceso a los repositorios de Ubuntu si
faltan dependencias. La instalación está probada en amd64; para otras
arquitecturas se intenta compilar la biblioteca y se detiene si no es compatible.

## Qué instala

- Dash to Panel 74 modificado: barra inferior flotante, aplicaciones centradas,
  radios de 12 px, fondo glass y selector animado de la aplicación con foco.
- Reloj a la derecha y botón discreto para mostrar el escritorio al final.
  Las aplicaciones abiertas sin foco mantienen un indicador fino.
- Corrección para que pulsar el espacio vacío de la barra no active otra ventana.
- Blur my Shell 75 modificado: geometría corregida del desenfoque, paneles y
  menús del Shell con tinte y esquinas coherentes, actividades y búsqueda.
- Biblioteca nativa `gnome-rounded-blur`: evita el fondo cuadrado detrás de las
  esquinas redondeadas. Incluye un `.deb` para Mutter `50.1-0ubuntu2.4` amd64 y
  el código fuente para recompilar con otro Mutter 50.
- Rounded Window Corners Reborn 25: esquinas de 12 px en ventanas flotantes,
  borde y sombra suaves; respeta las ventanas maximizadas y las aplicaciones
  que ya decoran sus esquinas.
- System Monitor 6: **solo CPU y RAM**, a la izquierda de todo, cada 2 segundos.
  Incluye integración local con Dash to Panel para mostrar el indicador en cada
  pantalla y reconstruirlo cuando cambian las barras.
- ScreenToSpace 15: al maximizar una ventana que comparte escritorio, la separa
  en un espacio propio y te lleva allí. Al restaurarla o cerrarla, vuelve al
  escritorio de origen. Se activa al maximizar, no al entrar en pantalla completa.
- La barra muestra las aplicaciones abiertas de **todos los escritorios**;
  sus ventanas siguen perteneciendo a su escritorio, no se duplican en los demás.
- Iconos WhiteSur-dark, cursor Bibata-Modern-Ice de 24 px, Yaru-blue-dark y
  acento azul. Incluye también los temas WhiteSur base y claro.
- Extension Manager, Retoques y las dependencias documentadas en
  [docs/PAQUETES.md](docs/PAQUETES.md), incluidas las herramientas que instalamos
  para compilar el desenfoque.

Activa la esquina superior izquierda para abrir actividades con el mouse.
No modifica los gestos, los atajos del sistema, la lista de aplicaciones
favoritas, el fondo de pantalla ni las
preferencias internas de las aplicaciones. Los menús propios de una aplicación
no usan necesariamente los estilos de GNOME Shell. Ubuntu Dock se desactiva
para que no compita con Dash to Panel; las otras extensiones se conservan.
Activa los escritorios dinámicos de GNOME para que ScreenToSpace pueda usar
espacios vacíos automáticamente. Los gestos de tres dedos siguen manejando
actividades y el cambio de escritorio.

Las pantallas nuevas heredan el diseño de la barra cuando está activada la
sincronización entre monitores: aplicaciones centradas y botón de aplicaciones
oculto. Se sigue la pantalla principal elegida en GNOME. Los contenedores de
Desktop Icons NG en Wayland se excluyen de la barra y del manejo de escritorios
de ScreenToSpace, conservando los iconos del escritorio.

## Copia y restauración

Antes de reemplazar archivos o ajustes de usuario se crea una copia en:

```text
~/.local/share/gnome-glass/backups/FECHA-HORA/
```

Si usás `XDG_DATA_HOME`, se usa esa ubicación. La copia incluye las extensiones
y temas anteriores, los valores previos de las claves que se modifican y el
estado de activación de las extensiones. El instalador imprime su ruta exacta.
Si falla la instalación de los archivos o ajustes, intenta restaurar esa copia
automáticamente y devuelve un error.

Para volver al estado anterior:

```bash
./install.sh --restore "$HOME/.local/share/gnome-glass/backups/FECHA-HORA"
```

Después cerrá sesión y volvé a entrar. La restauración recupera los archivos y
ajustes de usuario. **No desinstala paquetes APT ni revierte actualizaciones del
sistema**. Consultá [docs/PAQUETES.md](docs/PAQUETES.md) para el componente nativo.
No borres una copia mientras quieras poder restaurarla. Las copias son privadas
y no se guardan en este repositorio.
También se aceptan las copias de la versión 1.0: recuperan los componentes que
registraron y su lista anterior de extensiones activas. Los archivos de una
extensión agregada después pueden conservarse instalados, pero desactivados.

Podés ejecutar el instalador varias veces: cada ejecución vuelve a aplicar el
mismo perfil y crea su propia copia. No se habilitan actualizaciones automáticas
de las extensiones desde este instalador. Una actualización manual de Dash to
Panel, Blur my Shell, System Monitor o ScreenToSpace puede reemplazar los cambios locales; ejecutá de nuevo el
instalador para recuperar esta versión.

## Mantenerlo y llevarlo a otra computadora

- `profile/settings.json`: ajustes tipados de GSettings. Los diseños por monitor
  usan índices genéricos; no contiene identificadores de la pantalla original.
- `profile/packages.json`: dependencias explícitas que resolverá APT.
- `profile/components.json`: versiones, UUID, repositorios y commits de referencia.
- `vendor/extensions/`: código exacto de las cinco extensiones instaladas.
- `vendor/themes/`: temas completos, con sus enlaces simbólicos.
- `vendor/native/`: biblioteca nativa, fuentes y paquete binario de referencia.
- `vendor/sources/`: fuentes originales de WhiteSur y Bibata.
- `patches/`: diferencias locales de las extensiones modificadas respecto de
  sus paquetes originales. Son documentación; el instalador ya usa el código
  modificado y no necesita aplicar parches.

Para comprobar los archivos después de copiarlos:

```bash
sha256sum -c SHA256SUMS
```

Después de editar el perfil o el código, regenerá las sumas y hacé un commit:

```bash
python3 scripts/update-checksums.py
git add .
git commit -m "Actualizar personalización"
```

Las sumas detectan corrupción o cambios accidentales; no reemplazan una firma.
La configuración original se conserva en la etiqueta Git `v1.0.0`; `v1.1.0`
agrega ScreenToSpace y la barra con aplicaciones de todos los escritorios.
`v1.2.0` agrega el soporte de varias pantallas y el filtrado de Desktop Icons.
Copiá el
repositorio o su archivo `.bundle` a otro disco o a un remoto para tener una
copia fuera de este equipo. Para recuperar un bundle:

```bash
git clone /ruta/gnome-glass.bundle gnome-glass
cd gnome-glass
./install.sh
```

## Pruebas

```bash
./tests/run.sh
```

Usa un bus D-Bus privado, GSettings con backend keyfile y carpetas temporales.
Prueba instalación, reinstalación, restauración y recuperación ante un fallo
parcial sin cambiar tu escritorio ni instalar paquetes del sistema.

`./tests/headless.sh` realiza además una prueba con las cinco extensiones en
un compositor GNOME separado, comprueba el desenfoque nativo y la posición
inferior izquierda de CPU/RAM, y prueba maximizar, restaurar y cerrar ventanas,
así como la visibilidad global de la barra. Requiere la biblioteca nativa ya instalada y
`gnome-shell-test-tool` disponible. No necesita cerrar tu sesión.

`./tests/multimonitor.sh` ejecuta GNOME con tres pantallas virtuales, prueba
la herencia del diseño y CPU/RAM en cada barra, descarta las superficies de
escritorio y comprueba la reconstrucción de una a tres barras sin duplicados.

Los scripts de este repositorio se distribuyen bajo GPL-3.0-or-later. Los
componentes incluidos conservan sus autores y licencias originales; ver
[THIRD_PARTY.md](THIRD_PARTY.md).
