# Escritorios por pantalla y botones del mouse

La pantalla principal usa los escritorios nativos de GNOME. Workspace Islands
agrupa las ventanas de cada pantalla secundaria en escritorios independientes.
Se usa `workspaces-only-on-primary=true`, necesario para que los cambios en la
principal no arrastren las secundarias.

- Lateral trasero del Logitech: escritorio anterior de la pantalla bajo el mouse.
- Lateral delantero: escritorio siguiente de esa pantalla.
- Tres dedos a los costados: escritorios de la pantalla correspondiente.
- Tres dedos hacia arriba: vista de actividades de GNOME.
- Maximizar una ventana que comparte escritorio: la separa en un espacio propio.
  Restaurarla o cerrarla vuelve al espacio de origen.

Las pantallas secundarias mantienen un escritorio vacío disponible y crecen
conforme se abren ventanas. Las ventanas nuevas se asignan al escritorio actual,
sin recuperar el último escritorio usado por esa aplicación. Los escritorios
de las otras pantallas conservan su estado.

La extensión usa minimización para ocultar los espacios de las pantallas
secundarias. Al elegir una ventana desde la barra o Alt+Tab, se muestra su
escritorio. `Alt+Tab` y `Alt+Shift+Tab` recorren ventanas de todos los
escritorios y pantallas, sin agruparlas por aplicación; `Super+Tab` conserva el
selector de aplicaciones. Se respeta el orden reciente de GNOME.
Al desactivar la extensión se recuperan las ventanas que ocultó;
las que el usuario minimizó por su cuenta permanecen minimizadas.

## Little Big Mouse

La asignación de botones requiere el paquete local Little Big Mouse actualizado,
que se distribuye por separado como `littlebigmouse-gnome-trial.tar.gz`. No se
añaden paquetes APT ni se amplían los permisos del mouse para esta función.
La calibración personal no pertenece a este repositorio.

Su motor transforma cada pulsación de los botones `BTN_SIDE` y `BTN_EXTRA` en
un pulso de teclado completo. GNOME recibe los controles
`Super+Ctrl+Alt+Page Up` y `Super+Ctrl+Alt+Page Down`; la extensión decide el
monitor por las coordenadas del puntero, incluso si otra pantalla tiene el foco.
El resto de los atajos conserva su configuración anterior.

`launch.py` habilita esa transformación solo si Workspace Islands está activo
al arrancar Little Big Mouse. De lo contrario conserva Atrás/Adelante normales.
Después de activar o desactivar Workspace Islands hay que reiniciar también
Little Big Mouse para actualizar esa elección. El inicio automático hace esa
comprobación después de esperar que se estabilice la sesión.

El código de la integración, las fuentes completas y el parche del motor están
en `integrations/littlebigmouse/`. El archivo `source.tar.gz` ya incluye el
parche aplicado. Para partir del repositorio oficial, usar el commit indicado
en `build.json` y aplicar `workspace-buttons.patch` desde su raíz. Ejecutar
`cargo build --release --locked -p lbm-hook` en la carpeta `rust/`.
Reemplazar `app/lbm-hook` del paquete local con el binario resultante, manteniendo
el resto de su interfaz y su configuración. Su licencia es GPL-3.0.
