
def fun(data):
    import bpy
    import os
    import time

    context = bpy.context
    scene = context.scene
    scene.frame_start = data['f1']
    scene.frame_end = data['f2']

    idx = data['idx']

    #bpy.data.scenes["Scene"].render.filepath = '//out'
    #scene.render.filepath = '//image_#####_' + str(idx) + '.png'

    rd = scene.render

    rd.use_file_extension = True
    rd.image_settings.file_format='PNG'
    rd.image_settings.color_mode='RGBA'

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

    bpy.ops.render.render(animation = True,
                          #write_still = True
                          )

    image = bpy.data.images['Render Result']


    outputfn = 'output.png'
    image.save_render(outputfn)

    files = os.listdir('.')

    f = open(outputfn, 'rb')

    content = f.read()
    f.close()

    return {'files' : files,
            'imagedata' : content}

