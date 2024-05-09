# Splunk Distributed Architecture Vagrant

## Tabla de contenidos

- [Splunk Distributed Architecture Vagrant](#splunk-distributed-architecture-vagrant)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [Requisitos](#requisitos)
  - [🔑 Credenciales](#-credenciales)
  - [Primer uso](#primer-uso)
  - [Personalizaciones](#personalizaciones)
    - [Copiar archivos a las instancias cuando se crean](#copiar-archivos-a-las-instancias-cuando-se-crean)
  - [Uso](#uso)
    - [Tu primera vez levantando un grupo de servidores de la infraestructura 🚀](#tu-primera-vez-levantando-un-grupo-de-servidores-de-la-infraestructura-)
    - [Comandos](#comandos)
      - [manage](#manage)
      - [info](#info)
      - [config-base-image](#config-base-image)
      - [connect](#connect)
      - [config-instances](#config-instances)
  - [Especificaciones técnicas por defecto de la infraestructura](#especificaciones-técnicas-por-defecto-de-la-infraestructura)
    - [Grupos de servidores](#grupos-de-servidores)
    - [Vagranfiles](#vagranfiles)
    - [Archivos de configuración](#archivos-de-configuración)
  - [Terminología](#terminología)

## Requisitos

- Tener instalado VirtualBox con una versión igual o superior a la 7.
- Tener instalado Python 3.
- Tener instalado Vagrant con una versión igual o superior a la 2.4.1.

## 🔑 Credenciales

Las credenciales del usuario de instalación de Splunk son las siguientes:

- username: admin
- password: admin1234

## Primer uso

- Instalar las dependencias de Python:

  ```bash
  pip install -r requirements.txt
  ```

  Se recomienda usar virtualenv para gestionar las dependencias de forma que no colisionen con otras versiones instaladas para otros proyectos. Para saber mas visitar la documentación <https://virtualenv.pypa.io/en/latest/>.

- Configurar las imagen base para todas las maquinas virtuales del repositorio de imágenes base de Vagrant:

  ```bash
  python cli.py config-base-image -i <imagen_base>
  ```

- Descargar los comprimidos TGZ para Universal Forwarder y Splunk Enterprise con la version que queramos. Situar estos TGZ en el directorio `downloads` con los siguientes nombres:
  - Para el Universal Forwarder el TGZ se debe llamar `universalforwarder.tgz`.
  - Para el Splunk Enterprise el TGZ se debe llamar `splunk-enterprise.tgz`.

  En la carpeta `downloads` podemos guardar TGZ de otras versiones de los productos de Splunk pero solo serán los que se llamen `universalforwarder.tgz` y `splunk-enterprise.tgz`los que el Vagrantfile utilizara para levantar la arquitectura.

## Personalizaciones

### Copiar archivos a las instancias cuando se crean

Para copiar archivos a las instancias cuando se crean debemos poner los archivos en las carpetas dentro de `files_to_copy`. Cada carpeta dentro de `files_to_copy` se asocia con un solo cluster donde se van a copiar los ficheros. A continuación se especifica el cluster con que se asocia cada carpeta:

- idx_de: Indexador de desarrollo
- idx_pr: Indexadores de producción
- sh_de: Search head de desarrollo
- sh_pr: Search heads de producción
- manager: Manager

## Uso

Para gestionar la infraestructura se utilizara el script de Python cli.py. Para obtener información de las cosas que podemos hacer con este script deberemos ejecutar lo siguiente:

```bash
python cli.py --help
```

Si queremos saber mas información sobre un comando en concreto ejecutaremos lo siguiente:

```bash
python cli.py <comando> --help
```

También se puede usar con los comandos de Vagrant directamente. Para saber mas visitar <https://developer.hashicorp.com/vagrant/tutorials/getting-started/getting-started-up>. Para saber mas sobre los Vagrantfiles que hay en cada carpeta del repo ir a [Vagranfiles](#vagranfiles).

### Tu primera vez levantando un grupo de servidores de la infraestructura 🚀

```bash
python cli.py manage --action=start core_de
```

Podemos levantar varios grupos de servidores al mismo tiempo utilizando el comando de esta forma:

```bash
python cli.py manage --action=start core_de core_pr
```

### Comandos

#### manage

Este comando sirve para manejar el estado de los grupos de servidores de la arquitectura. Con este comando podemos pararlos, levantarlos o destruirlos.

Para obtener mas información ejecutar:

```bash
python manage --help
```

#### info

Este comando sirve para obtener información de ayuda. Las opciones que tenemos son las siguientes:

- vms: Nos da información sobre las maquina virtuales que componen toda la infraestructura.

Para obtener mas información ejecutar:

```bash
python info --help
```

#### config-base-image

Este comando sirve para configurar la imagen base de Vagrant que van a utilizar todas las maquinas virtuales de la infraestructura.

Para obtener mas información ejecutar:

```bash
python config-base-image --help
```

#### connect

Este comando sirve para conectarnos a las maquinas virtuales por SSH.

Para obtener mas información ejecutar:

```bash
python connect --help
```

#### config-instances

Este comando sirve para configurar cuantas instancias queremos de los siguientes clusters en producción:

- Forwarders
- Indexadores
- Search heads.

Para obtener mas información ejecutar:

```bash
python config-instances --help
```

## Especificaciones técnicas por defecto de la infraestructura

![Architecture diagram](readme/images/general-archiecture.png)

### Grupos de servidores

- core_pr: Incluye los indexadores de producción, search heads de producción y el manager.
- core_de: Incluye el indexador de desarrollo y el search head de desarrollo.
- lb: Incluye el balanceador de carga para los search heads de producción.
- fwd: Incluye los forwarders.
- hf: Incluye el Heavy Forwarder.

### Vagranfiles

- `src/s14e/Vagrantfile`: Vagrantfile para crear las siguientes maquinas:
  - Indexadores de producción
  - Search heads de producción
  - Manager
  - Indexador de desarrollo
  - Search head de desarrollo
  - Heavy Forwarder
- `src/l10r/Vagrantfile`: Vagrantfile que crea el balanceador de carga para los search heads de producción.
- `src/u16f/Vagrantfile`: Vagrantfile que crea los forwarders.

### Archivos de configuración

- `src/config.json`: Archivo que contiene toda la parametrización de la arquitectura por defecto.
- `user-config.json`: Archivo que contiene toda la parametrización personalizada del usuario de la arquitectura. Este archivo se puede manipular por nosotros mismos y no se subirá al repositorio.

## Terminología

- Clusters: Grupo de instancias del mismo tipo.
- Grupo de servidores: Grupo de varios clusters o instancias.
