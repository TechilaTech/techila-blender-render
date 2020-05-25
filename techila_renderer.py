bl_info = {
    "name": "Techila Renderer",
    "description": "Render .blend in Techila.",
    "author": "Kari Koskinen <kari.koskinen@techilatechnologies.com>, Teppo Tammisto <teppo.tammisto@techilatechnologies.com>",
    "version": (0, 3),
    "blender": (2, 82, 0),
    "location": "Render > Engine > Techila",
    "warning": "Experimental",  # used for warning icon and text in addons panel
    # "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/Scripts/My_Script",
    "category": "Render"}

import bpy
import bpy_extras.image_utils
from bpy.props import IntProperty, PointerProperty
import os
import tempfile
import techila


class TechilaSettings(bpy.types.PropertyGroup):
    slicex: IntProperty(name = 'X Slices',
                        description = 'Number of pieces in dimension X',
                        min = 1,
                        max = 100,
                        soft_min = 1,
                        soft_max = 100,
                        default = 2)

    slicey: IntProperty(name = 'Y Slices',
                        description = 'Number of pieces in dimension Y',
                        min = 1,
                        max = 100,
                        soft_min = 1,
                        soft_max = 100,
                        default = 2)


class XXXMenu(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_label = 'Settings'
    COMPAT_ENGINES = set(['TECHILA_RENDER'])

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return (rd.use_game_engine is False) and (rd.engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.techila_render
        layout.prop(settings, 'slicex')
        layout.prop(settings, 'slicey')


class TechilaRenderer(bpy.types.RenderEngine):
    bl_idname = 'TECHILA_RENDER'
    bl_label = 'Techila'
    #bpy.ops.wm.save_mainfile()

    def render(self, depsgraph):

        print('depsgraph.mode = {}'.format(depsgraph.mode))

        scene = depsgraph.scene

        print('is_animation = {}'.format(self.is_animation))

        #blendfile = bpy.data.filepath
        index = bpy.data.filepath.rindex('/')
        datadir = '.'  # bpy.data.filepath[:index]
        blendfile = bpy.data.filepath[index + 1:]

        datafiles = []

        for root, dirs, files in os.walk(datadir):
            if '.git' in dirs:
                dirs.remove('.git')
            for fn in files:
                if (fn.endswith('blend1')
                    or fn.endswith('blend2')
                    or fn.endswith('state')
                    or fn == 'worker_fun.py'
                    or fn == 'techila_renderer.py'
                    or fn == blendfile
                    ):
                    continue

                fullname = os.path.join(root, fn)
                datafiles.append(fullname[len(datadir) + 1:])

        print('datadir is   ' + datadir)
        #print('blendfile is ' + blendfile)
        print('files are    ' + str(datafiles))

        #settings = scene.techila_render
        tiles_x = 1 #settings.slicex
        tiles_y = 1 #settings.slicey

        step_x = 1.0 / tiles_x
        step_y = 1.0 / tiles_y

        pv = []
        for frameno in range(scene.frame_start, scene.frame_end + 1):
            for x in range(tiles_x):
                for y in range(tiles_y):

                    idx = x * tiles_x + y

                    x1 = x * step_x
                    x2 = x1 + step_x

                    y1 = y * step_y
                    y2 = y1 + step_y

                    data = {
                        'f1': frameno,
                        'f2': frameno,
                        'x1': x1,
                        'x2': x2,
                        'y1': y1,
                        'y2': y2,
                        'idx': idx,
                    }

                    pv.append(data)

        results = techila.peach(funcname = 'fun',
                                params = ['<param>'],
                                files = ['worker_fun.py'],
                                executable = True,
                                realexecutable = '%L(blender)/blender;osname=Linux,%L(blender)\\\\blender.exe;osname=Windows',
                                python_required = False,
                                #outputfiles = ['output;regex=true;file=image_\\\\d+_\\\\d+.png'],
                                exeparams = '-noaudio --python-use-system-env -b ' + blendfile + ' -P peachclient.py -- <peachclientparams>',
                                binary_bundle_parameters = {
                                    'Environment': 'PYTHONPATH;value=%P(tmpdir),SYSTEMROOT;value=C:\\\\Windows;osname=Windows',
                                },
                                databundles = [
                                    {
                                        'datafiles': [blendfile],
                                        'datadir': datadir,
                                        'libraryfiles': False,
                                        'flatten': False,
                                    },
                                    {
                                        'datafiles': datafiles,
                                        'datadir': datadir,
                                        'libraryfiles': False,
                                        'flatten': False,
                                    }],
                                project_parameters={
                                    'techila_worker_os': 'Linux,amd64',
                                },
                                peachvector = pv,
                                imports = ['Blender 2.82a Linux amd64'],
                                #filehandler = copyhandler,
                                return_iterable = True,
                                stream = True,
                                #resultfile = '/tmp/z/project12817.zip',
                                #projectid = 12817,
                                )

        results.set_return_idx(True)

        tmpfile = tempfile.mkstemp(prefix='techila-blender-', suffix='.exr')
        tmpfile = tmpfile[1]

        for res in results:
            idx = res[0]
            resdata = res[1]
            data = resdata['data']
            imagedata = resdata['imagedata']

            # stupid?
            f = open(tmpfile, 'wb')
            f.write(imagedata)
            f.close()

            frameno = data['f1']

            x1 = data['x1'] * scene.render.resolution_x * scene.render.resolution_percentage / 100
            x2 = data['x2'] * scene.render.resolution_x * scene.render.resolution_percentage / 100
            y1 = data['y1'] * scene.render.resolution_y * scene.render.resolution_percentage / 100
            y2 = data['y2'] * scene.render.resolution_y * scene.render.resolution_percentage / 100

            x = int(x1)
            y = int(y1)
            w = round(x2 - x1)
            h = (y2 - y1)

            print('h = {}'.format(h))

            h = round(h)

            print('frameno {}'.format(frameno))
            scene.frame_set(frameno)
            print('data {} {} {} {}'.format(data['x1'], data['y1'], data['x2'], data['y2']))
            print('jee {} {} {} {}'.format(x1, y1, x2, y2))
            print('moi {} {} {} {}'.format(x, y, w, h))
            result = self.begin_result(x, y, w, h)
            print('result = ', result)
            if result is not None:
                #lay = result.layers[0]
                #lay.load_from_file(tmpfile)
                try:
                    result.load_from_file(tmpfile)
                except Exception as e:
                    print(e)
                self.end_result(result)

        os.remove(tmpfile)


def register():
    from bpy.utils import register_class
    register_class(TechilaRenderer)

    register_class(TechilaSettings)

    bpy.types.Scene.techila_render = PointerProperty(type = TechilaSettings,
                                                     name = 'Techila Render',
                                                     description = 'Techila Render Settings')

    # bpy.utils.register_class(TechilaRenderer)
    # from bl_ui import (
    #     properties_render,
    #     properties_material,
    #     )
    # properties_render.RENDER_PT_render.COMPAT_ENGINES.add(TechilaRenderer.bl_idname)
    # properties_material.RENDER_PT_render.COMPAT_ENGINES.add(TechilaRenderer.bl_idname)


def unregister():
    from bpy.utils import unregister_class
    unregister_class(TechilaRenderer)

    # bpy.utils.unregister_class(TechilaRenderer)
    # from bl_ui import (
    #     properties_render,
    #     properties_material,
    #     )
    # properties_render.RENDER_PT_render.COMPAT_ENGINES.remove(TechilaRenderer.bl_idname)
    # properties_material.RENDER_PT_render.COMPAT_ENGINES.remove(TechilaRenderer.bl_idname)

if __name__ == "__main__":
    register()
