
def fun(data, render_engine, device, txformat):
    import bpy
    import os

    context = bpy.context
    scene = context.scene
    scene.frame_start = data['f1']
    scene.frame_end = data['f2']
    scene.frame_set(data['f1'])

    #idx = data['idx']

    rd = scene.render

    rd.use_file_extension = True
    rd.image_settings.color_mode = 'RGBA'
    rd.image_settings.file_format = txformat

    if txformat == 'OPEN_EXR_MULTILAYER':
        rd.image_settings.color_depth = '32'
        rd.image_settings.exr_codec = 'ZIP'
        outputfn = 'output.exr'
    else:
        rd.image_settings.color_depth = '16'
        outputfn = 'output.png'

    scene.render.filepath = '//' + outputfn

    rd.threads = 1
    rd.threads_mode = 'FIXED'

    #rd.parts_x = 1
    #rd.parts_y = 1

    rd.use_border = True
    rd.use_crop_to_border = True
    rd.border_min_x = data['x1']
    rd.border_max_x = data['x2']
    rd.border_min_y = data['y1']
    rd.border_max_y = data['y2']

    bpy.context.scene.render.engine = render_engine

    if device == 'GPU':
        # GPU https://developer.blender.org/T61838
        prefs = bpy.context.preferences
        cprefs = prefs.addons['cycles'].preferences

        # Attempt to set GPU device types if available
        for compute_device_type in ('CUDA', 'OPENCL', 'NONE'):
            try:
                cprefs.compute_device_type = compute_device_type
                break
            except TypeError:
                pass

        # Enable all CPU and GPU devices
        for device in cprefs.devices:
            device.use = True

        bpy.context.scene.cycles.device = 'GPU'

        bpy.context.preferences.addons['cycles'].preferences.get_devices()

    bpy.ops.render.render(animation=False,
                          write_still=True
                          )

    return {
        'data': data,
    }
