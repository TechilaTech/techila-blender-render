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
from bpy.props import IntProperty, PointerProperty, EnumProperty
import os
import shutil
import tempfile
import techila


# Cycles is the only one that works
# others error out with "Unable to open a display"
enum_render_engine = (
    #('BLENDER_EEVEE', 'Eevee', ''),
    #('BLENDER_WORKBENCH', 'Workbench', ''),
    ('CYCLES', 'Cycles', ''),
)

enum_txformat = (
    ('PNG', 'PNG', ''),
    ('OPEN_EXR_MULTILAYER', 'OpenEXR MultiLayer', ''),
)

enum_device = (
    ('CPU', 'CPU', ''),
    ('GPU', 'GPU', ''),
)


class TechilaSettings(bpy.types.PropertyGroup):
    slicex: IntProperty(
        name='X Slices',
        description='Number of pieces in dimension X',
        min=1,
        max=1,
        soft_min=1,
        soft_max=1,
        default=1)

    slicey: IntProperty(
        name='Y Slices',
        description='Number of pieces in dimension Y',
        min=1,
        max=1,
        soft_min=1,
        soft_max=1,
        default=1)

    render_engine: EnumProperty(
        name='Render Engine',
        description='Render Engine used on worker',
        items=enum_render_engine,
        default='CYCLES',
    )

    txformat: EnumProperty(
        name='Transfer format',
        description='File format for result transfer',
        items=enum_txformat,
        default='PNG',
    )

    device: EnumProperty(
        name='Render Device',
        description='Device to use for rendering',
        items=enum_device,
        default='CPU',
    )

    @classmethod
    def register(cls):
        bpy.types.Scene.techila_render = PointerProperty(
            name='Techila Render Settings',
            description='Techila Render Settings',
            type=cls,
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.techila_render


class TechilaRenderPanel(bpy.types.Panel):
    bl_idname = 'RENDER_PT_Techila'
    bl_label = 'Render Settings'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    COMPAT_ENGINES = {'TECHILA_RENDER'}

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        tscene = scene.techila_render

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(tscene, 'render_engine')
        layout.prop(tscene, 'device')
        layout.prop(tscene, 'txformat')

        col = layout.column(align=True)

        col.prop(tscene, 'slicex')
        col.prop(tscene, 'slicey')


class TechilaCache(object):
    cached_results = None
    txformat = None


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
            try:
                resultdata = TechilaCache.cached_results[frame_current]
                print('popped {}'.format(resultdata))
                self.load_result(scene, resultdata)
            except KeyError:
                # reset state
                TechilaCache.cached_results = None

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

        settings = scene.techila_render

        render_engine = settings.render_engine
        device = settings.device
        txformat = settings.txformat
        tiles_x = settings.slicex
        tiles_y = settings.slicey

        if txformat == 'OPEN_EXR_MULTILAYER':
            outputfile = 'output.exr'
        else:
            outputfile = 'output.png'

        print('render_engine = {}'.format(render_engine))
        print('device = {}'.format(device))
        print('txformat = {}'.format(txformat))
        print('slicex = {}, slicey = {}'.format(tiles_x, tiles_y))

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

        obj = {}
        results = techila.peach(funcname='fun',
                                params=['<param>', render_engine, device, txformat],
                                files=['worker_fun.py'],
                                executable=True,
                                realexecutable='%L(blender)/blender;osname=Linux,%L(blender)\\\\blender.exe;osname=Windows',
                                python_required=False,
                                exeparams='-noaudio --python-use-system-env -b ' + blendfile + ' -P peachclient.py -- <peachclientparams>',
                                binary_bundle_parameters={
                                    'Environment': 'PYTHONPATH;value=%P(tmpdir),SYSTEMROOT;value=C:\\\\Windows;osname=Windows',
                                    #'ErrorCodes': 'ignore;codes=11',
                                },
                                databundles=[
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
                                peachvector=pv,
                                imports=['blender.2830'],
                                callback=self.callback,
                                filehandler=self.filehandler,
                                stream=True,
                                #resultfile='/tmp/project31.zip',
                                #projectid=31,
                                outputfiles=[outputfile],
                                callback_obj=obj,
                                )

        #results.set_return_idx(True)

        TechilaCache.cached_results = {}
        TechilaCache.txformat = txformat

        for resdata in results:
            data = resdata['data']
            frameno = data['f1']

            #print('data = {}'.format(data))
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
        h = round(y2 - y1)

        print('frameno {}'.format(frameno))
        print('data {} {} {} {}'.format(data['x1'], data['y1'], data['x2'], data['y2']))
        print('x1 {} y1 {} x2 {} y2 {}'.format(x1, y1, x2, y2))
        print('x {} y {} w {} h {}'.format(x, y, w, h))
        result = self.begin_result(x, y, w, h)
        #print('result = ', result)
        if result is not None:
            try:
                if TechilaCache.txformat == 'OPEN_EXR_MULTILAYER':
                    result.load_from_file(data['filename'])
                else:
                    lay = result.layers[0]
                    lay.load_from_file(data['filename'])

            except Exception as e:
                print(e)
            self.end_result(result)

        os.remove(data['filename'])

    def callback(self, result, obj):
        print('** CB {} {}'.format(result, obj))
        frameno = result['data']['f1']

        if TechilaCache.txformat == 'OPEN_EXR_MULTILAYER':
            suffix = '.exr'
        else:
            suffix = '.png'

        tmpfile = tempfile.mkstemp(prefix=f'techila-blender-{frameno}-', suffix=suffix)
        obj['filename'] = tmpfile[1]
        result['data']['filename'] = tmpfile[1]
        return result

    def filehandler(self, filename, obj):
        print('## FH {} {}'.format(filename, obj))
        shutil.move(filename, obj['filename'])


def get_panels():
    exclude_panels = [
        'RENDER_PT_simplify',
        'RENDER_PT_freestyle',
        'RENDER_PT_color_management',
        'RENDER_PT_color_management_curve',
    ]

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)

    return panels


def register():
    from bpy.utils import register_class
    register_class(TechilaRenderer)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add('TECHILA_RENDER')

    register_class(TechilaSettings)
    register_class(TechilaRenderPanel)


def unregister():
    from bpy.utils import unregister_class

    unregister_class(TechilaRenderPanel)
    unregister_class(TechilaSettings)

    unregister_class(TechilaRenderer)

    for panel in get_panels():
        if 'TECHILA_RENDER' in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove('TECHILA_RENDER')


if __name__ == "__main__":
    register()
