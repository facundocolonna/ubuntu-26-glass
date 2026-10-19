# LittleBigMouse en Ubuntu 26.04 / GNOME 50 Wayland

Compilación local del proyecto oficial, identificada en `build.json`. Incluye el
runtime .NET: no requiere instalar .NET ni Rust en el sistema para ejecutarla.
Licencia GPL-3.0, fuente: https://github.com/mgth/LittleBigMouse.

Ejecutar `./probar.sh` como usuario normal. La autenticación de Linux habilita
temporalmente lectura/escritura del Logitech MX Anywhere 3 y `/dev/uinput`
mediante ACL. El modo manual no modifica grupos, reglas udev ni permisos de teclado o trackpad.
El acceso se pierde al reiniciar; el del mouse también al desconectarlo.

En la aplicación, acomodar las pantallas según su tamaño y posición física y
usar **Start**. El modo normal funciona sin límite de tiempo. Para repetir una
prueba de 30 segundos, detener primero con `./probar.sh --stop` y ejecutar
`./probar.sh --timed`.
Esta es una prueba de compatibilidad: la versión Linux es experimental y el
autor la ha probado principalmente en KDE. La detección de pantallas y el
arranque de la interfaz se verificaron localmente; el movimiento real del
mouse bajo GNOME necesita comprobarse con el usuario.

La carpeta `extension/` contiene una extensión local de GNOME 50 para impedir
que un fragmento del puntero aparezca desplazado en el monitor contiguo.
Mientras el motor está activo, si la imagen del cursor sobresale de una pantalla,
la extensión dibuja una copia recortada al borde de esa pantalla. Dentro de la
pantalla se conserva el cursor nativo. No reproduce un fragmento en el monitor
contiguo: el cursor pasa a la otra pantalla cuando cruza su punto de referencia.
Se restaura el cursor nativo al detener/desconectar el motor, bloquear la sesión
o deshabilitar la extensión. Las capas del cursor no interceptan clics.

Ejecutar `./install.sh` para registrar la extensión y el acceso de aplicaciones.
La primera instalación de una extensión nueva requiere volver a iniciar sesión
para que GNOME la descubra. El instalador no cierra la sesión automáticamente.
Verificación: prueba en GNOME aislado con dos monitores virtuales, conexiones
IPC Running/Stopped/desconexión, recorte en el borde y limpieza al desactivar.
La comprobación visual en los tres monitores reales queda pendiente.

El trackpad conserva el control normal y los gestos. No se aplica la opción
de cambiar la disposición de pantallas del sistema. El inicio automático solo
se registra cuando se instala con `--autostart`.

Detener la interfaz y su motor: `./probar.sh --stop`.
Detener y restaurar las ACL anteriores: `./probar.sh --revoke` (autenticación).
Consultar registros: `journalctl --user -u littlebigmouse-trial -b`.

Para iniciar al entrar a GNOME, ejecutar `./install.sh --autostart`. Este modo
instala una entrada en `~/.config/autostart/` y pide autenticación una vez para
crear `/etc/udev/rules.d/69-gnome-glass-littlebigmouse.rules` y
`/etc/modules-load.d/gnome-glass-littlebigmouse.conf`. Las reglas otorgan al
usuario de la sesión local activa acceso al Logitech MX Anywhere 3 y a uinput,
sin añadirlo al grupo input ni autorizar teclado/trackpad. Así funciona también
después de reiniciar y de reconectar el mouse.

El arranque espera que el mouse y sus permisos estén disponibles, deja tiempo
para que se estabilicen las pantallas, abre la interfaz minimizada y activa la
configuración guardada. La unidad de usuario se detiene con la sesión gráfica.
En GNOME 50, la entrada no debe incluir `X-GNOME-Autostart-Phase`: GNOME
ignora las entradas que contienen esa opción antigua, incluso con el valor
`Applications`. Volver a ejecutar el instalador con `--autostart` reemplaza
las entradas antiguas. La corrección se verificó lanzando la entrada instalada:
la interfaz arrancó minimizada y el motor confirmó el estado `Running`.
Abrir el acceso LittleBigMouse cuando ya está ejecutándose muestra su interfaz.
Para desactivar el inicio automático, borrar
`~/.config/autostart/gnome-glass-littlebigmouse.desktop` y usar `./probar.sh --stop`.
Las reglas persistentes pueden retirarse borrando los dos archivos de `/etc/`
anteriores y reiniciando (requiere administrador).

Conviene validar los
cruces de pantalla, el arrastre, los botones y la rueda en aplicaciones Wayland
y XWayland antes de incorporar este componente al perfil principal.

## Botones laterales y escritorios por pantalla

El paquete actualizado incluye Workspace Islands para GNOME 50. El instalador
registra sus escritorios dinámicos en las pantallas secundarias, con gestos y
separación al maximizar; la principal conserva GNOME nativo. No amplía las ACL.

Con el controlador activo al arrancar Little Big Mouse, el lateral trasero va
al escritorio anterior y el delantero al siguiente de la pantalla bajo el
puntero. Reemplazan Atrás/Adelante en las aplicaciones; el motor consume ambos
botones y emite un pulso completo de `Super+Ctrl+Alt+Page Up/Down`, sin dejar
modificadores presionados. Los demás botones y la rueda no cambian.

Al entrar a GNOME se espera también a que cargue el controlador. Si no está
activo, el motor conserva los botones Atrás/Adelante normales. Reiniciar
Little Big Mouse después de activar o desactivar el controlador actualiza esa
elección. La primera instalación requiere volver a iniciar sesión para que
GNOME descubra la extensión nueva.
