# Fuentes de Little Big Mouse y asignación de botones

El runtime compilado se conserva en el paquete local separado
`littlebigmouse-gnome-trial.tar.gz`. Esta carpeta guarda las fuentes, el parche,
la procedencia y los scripts que acompañan ese paquete. No incluye la
calibración personal ni los binarios de la interfaz.

`source.tar.gz` contiene las fuentes completas con el parche ya aplicado.
Para reconstruir se usaron .NET 10.0.402 y Rust 1.98.1, indicados también en
`build.json`. Desde las fuentes descomprimidas:

```bash
cd LittleBigMouse/rust
cargo build --release --locked -p lbm-hook
cd ../LittleBigMouse.Ui/LittleBigMouse.Ui.Avalonia
dotnet publish -c Release -r linux-x64 --self-contained true -o ../../../app
```

Copiar `rust/target/release/lbm-hook` a `app/lbm-hook` junto a la interfaz
publicada. El paquete completo añade los scripts de esta carpeta, `extension/`
(incluida aquí) con la corrección del cursor y `workspace-extension/` con la copia de Workspace
Islands que está en `vendor/extensions/` del repositorio principal. Su
`workspace-settings.json` contiene los valores de ese esquema en
`profile/settings.json`. Con esa estructura, `install.sh --autostart` registra
el acceso, las extensiones y el inicio automático del paquete.

Para reconstruir únicamente el motor sobre un paquete ya instalado, basta
reemplazar su `app/lbm-hook` después de detener Little Big Mouse. Conservar la
interfaz y los archivos de configuración existentes.

El motor solo remapea `BTN_SIDE` y `BTN_EXTRA` cuando el lanzador detecta el
controlador de escritorios activo. Los eventos originales no se reenvían al
navegador. Cada pulsación produce un acorde completo con sus liberaciones;
mantener el botón pulsado no repite el cambio ni deja teclas presionadas.
