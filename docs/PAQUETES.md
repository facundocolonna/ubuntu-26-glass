# Paquetes y dependencias

`profile/packages.json` es la lista que usa el instalador. Instala solamente
los paquetes que falten; APT resuelve sus dependencias transitivas. No fuerza
versiones antiguas de Ubuntu. El registro de los paquetes agregados durante la
personalización, con versiones y dependencias automáticas, se conserva en
`paquetes-instalados-referencia.json` como referencia histórica.

## Administración y apariencia

| Paquete | Uso |
| --- | --- |
| `gnome-shell-extension-manager` | Administrar las extensiones |
| `gnome-tweaks` | Retoques de apariencia |
| `yaru-theme-gtk`, `yaru-theme-icon` | Tema Yaru y sus recursos |
| `fonts-ubuntu` | Tipografías Ubuntu |

WhiteSur y Bibata ya están incluidos como temas de usuario. No hace falta
instalar sus paquetes desde otro repositorio. Papirus fue una prueba anterior;
el perfil final usa WhiteSur y no necesita Papirus.

## Ejecución y preferencias

`python3-gi`, `gjs`, `libglib2.0-bin`, `dconf-gsettings-backend`,
`gsettings-desktop-schemas`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`, `gir1.2-handy-1`,
`gir1.2-gnomedesktop-4.0`, `gir1.2-mutter-18`, `libmutter-18-0` y
`libglib2.0-0t64` cubren GSettings, compilación de esquemas, ejecución de las
extensiones y sus ventanas de preferencias. GNOME Shell y Wayland deben estar
ya instalados: el instalador no reemplaza el entorno de escritorio.

## Herramientas históricas de compilación

La lista `legacy_build` conserva los paquetes que agregamos para compilar la
biblioteca usada por Blur my Shell 75:

```text
build-essential
meson
ninja-build
pkg-config
libglib2.0-dev
gobject-introspection
libgirepository1.0-dev
libmutter-18-dev
```

Blur my Shell 76 ya no necesita esa biblioteca. El instalador actual no instala
ni recompila esas herramientas; los paquetes existentes se conservan.

## `gnome-rounded-blur-local` (histórico)

Las fuentes, licencia y paquete de referencia siguen en `vendor/native/` para
recuperar instalaciones anteriores. El paquete se compilaba contra una versión
exacta de Mutter y su lista de herramientas permanece en `legacy_build`.
La versión actual de Glass no carga `Blur-1.0.typelib` ni instala ese paquete.

Restaurar una copia cambia los archivos y ajustes del usuario. No desinstala
paquetes APT ni revierte actualizaciones del sistema.
