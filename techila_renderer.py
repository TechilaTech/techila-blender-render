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


class TechilaCache(object):
    cached_results = None


class TechilaRenderer(bpy.types.RenderEngine):
    bl_idname = 'TECHILA_RENDER'
    bl_label = 'Techila'
    #bl_use_save_buffers = True
    #bpy.ops.wm.save_mainfile()

    def render(self, depsgraph):
        print('render {}'.format(depsgraph.scene.frame_current))

        scene = depsgraph.scene

        frame_current = scene.frame_current
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        if not self.is_animation:
            frame_start = frame_current
            frame_end = frame_current

        if TechilaCache.cached_results is None:
            # first frame, start new Techila project
            self.new_render(scene, frame_start, frame_end)

        if TechilaCache.cached_results is not None:
            resultdata = TechilaCache.cached_results[frame_current]
            print('popped {}'.format(resultdata))
            self.load_result(scene, resultdata)

        if frame_current == frame_end:
            print('last frame')
            TechilaCache.cached_results = None

    def new_render(self, scene, frame_start, frame_end):
        index = bpy.data.filepath.rindex('/')
        datadir = bpy.data.filepath[:index]
        blendfile = bpy.data.filepath[index + 1:]

        print('datadir = {}'.format(datadir))
        print('blendfile = {}'.format(blendfile))

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

        print('files are    ' + str(datafiles))

        #settings = scene.techila_render
        tiles_x = 1 #settings.slicex
        tiles_y = 1 #settings.slicey

        step_x = 1.0 / tiles_x
        step_y = 1.0 / tiles_y

        pv = []
        for frameno in range(frame_start, frame_end + 1):
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
                                #filehandler = self.filehandler,
                                #return_iterable = True,
                                stream = True,
                                #resultfile = '/tmp/z/project12817.zip',
                                #projectid = 12817,
                                #outputfiles=['output.png'],
                                )

        #results.set_return_idx(True)

        TechilaCache.cached_results = {}

        for resdata in results:
            data = resdata['data']
            frameno = data['f1']

            imagedata = resdata['imagedata']

            tmpfile = tempfile.mkstemp(prefix=f'techila-blender-{frameno}-', suffix='.png')

            f = open(tmpfile[0], 'wb')
            f.write(imagedata)
            f.close()

            data['filename'] = tmpfile[1]
            print('data = {}'.format(data))
            TechilaCache.cached_results[frameno] = data

    def load_result(self, scene, data):
        frameno = data['f1']

        x1 = data['x1'] * scene.render.resolution_x * scene.render.resolution_percentage / 100
        x2 = data['x2'] * scene.render.resolution_x * scene.render.resolution_percentage / 100
        y1 = data['y1'] * scene.render.resolution_y * scene.render.resolution_percentage / 100
        y2 = data['y2'] * scene.render.resolution_y * scene.render.resolution_percentage / 100

        x = int(x1)
        y = int(y1)
        w = round(x2 - x1)
        h = (y2 - y1)

        #print('h = {}'.format(h))

        h = round(h)

        print('frameno {}'.format(frameno))
        scene.frame_set(frameno)
        print('data {} {} {} {}'.format(data['x1'], data['y1'], data['x2'], data['y2']))
        print('jee {} {} {} {}'.format(x1, y1, x2, y2))
        print('moi {} {} {} {}'.format(x, y, w, h))
        result = self.begin_result(x, y, w, h)
        print('result = ', result)
        if result is not None:
            try:
                lay = result.layers[0]
                lay.load_from_file(data['filename'])

                # result.load_from_file(tmpfile)
            except Exception as e:
                print(e)
            self.end_result(result)

        os.remove(data['filename'])


    def filehandler(self, filename):
        pass


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
