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

## Compilación de la biblioteca nativa

También se incluyen todos los paquetes que agregamos para compilar:

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

Son herramientas de compilación; la biblioteca compilada no necesita el
compilador para ejecutarse. El instalador las comprueba igualmente para que el
entorno pueda reconstruir el desenfoque en una futura reinstalación.

## `gnome-rounded-blur-local`

Es un paquete local, no un paquete oficial de Ubuntu. Incluye
`libblur-effect-1.0.so.1` y `Blur-1.0.typelib`, utilizados por Blur my Shell.
Se incluye el fuente completo de `kancko/gnome-rounded-blur`, commit
`a4db9e5947b1cea0a05c57768356921420f91293`.

El instalador compara la arquitectura y la versión de `libmutter-18-0`:

1. Si hay una instalación local compatible y sus archivos existen, la conserva.
2. Para amd64 y Mutter `50.1-0ubuntu2.4`, usa el `.deb` incluido.
3. Para otro Mutter 50, compila sin privilegios, arma un `.deb` temporal y usa
   `sudo dpkg -i` para instalarlo. No instala compilaciones en `/usr/local`.

El paquete declara dependencia exacta de la versión de Mutter contra la que
se compiló, porque usa su API interna. Si una actualización de Ubuntu necesita
cambiar Mutter y APT informa un conflicto con este paquete local, quitá
`gnome-rounded-blur-local`, completá la actualización y ejecutá de nuevo
`./install.sh` para recompilarlo. Una nueva versión mayor de GNOME requiere
revisar también las extensiones y este perfil.

La restauración de usuario conserva los paquetes del sistema. Si además querés
quitar la biblioteca local, después de desactivar la personalización:

```bash
sudo apt-get remove gnome-rounded-blur-local
```

No se ejecuta `autoremove` ni se desinstalan compiladores automáticamente, para
evitar afectar herramientas utilizadas por otros programas.
