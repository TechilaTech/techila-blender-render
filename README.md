# Techila Blender plugin

This is a plugin to render [Blender](https://www.blender.org/) files with Techila Distributed Computing Engine (TDCE).

## Rendering

* Start some Techila Workers (Linux) from the Techila Configuration Wizard

* **Important!** Blender should be started from a clean directory containing only the blend file and other required assets (or current working directory changed). Also the worker_fun.py must be in the current working directory. Everything in the current working directory will be copied to the Techila Server (you probably don't want your whole home directory there). See datadir setting in ./techila_renderer.py

* Save your work (blend file), this file is uploaded to the TDCE system and rendered on the workers with the settings saved in the file.

* Select Techila Renderer and select number of slices in x and y directions

* Click Render

* The results will be streamed back to your computer and shown as they complete


## Prerequisites

* Launch Techila Distributed Computing Engine available in GCP Marketplace https://console.cloud.google.com/marketplace/details/techila-public/techila

* Download Techila SDK from the Techila Server as instructed

* Blender needs to be bundled for use in TDCE (see below) and uploaded to your Techila Server.

* Techila Python package must be installed within Blender's Python
  * cd into Techila SDK techila/lib/python3 directory
  * Using Blender's Python, run setup.py, e.g.: `/opt/blender-2.82a-linux64/2.82/python/bin/python3.7m setup.py install`

* Install this plugin into your Blender installation and enable it


## Bundling Blender

* Download Blender for Linux 64 bit from https://www.blender.org/download/ and unpack it

* Run the following command to create the bundle (check the paths for techila.jar and where you unpacked blender). This will create a bundle and upload it to your Techila server.

```java -jar ~/techila/lib/techila.jar createBundle bundlename="Blender 2.82a Linux amd64" expiration=365d resource=blender export=blender.282a Environment="LD_LIBRARY_PATH;value=%L(blender)/lib" ExternalResources="blender;resource=blender" natives="blender;osname=Linux;processor=amd64" trimpath=/tmp/blender-2.82a-linux64/ /tmp/blender-2.82a-linux64```
