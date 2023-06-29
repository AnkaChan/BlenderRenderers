import json, sys, os, math
import bpy, pathlib
import mathutils

fPath = pathlib.Path(__file__).parent.absolute()
pi = 3.1415926535897932

def addCameras(camSpecs, useDof=True, changePositionToM=False):
    for cam in camSpecs:
        cameraData = bpy.data.cameras.new(cam.name + '_data')

        # create object camera data and insert the camera data
        cam_ob = bpy.data.objects.new(cam.name, cameraData)

        # worldMatrix = np.array([[rotation[0][0], rotation[0][1], rotation[0][2], translation[0]], \
        #                         [rotation[1][0], rotation[1][1], rotation[1][2], translation[1]], \
        #                         [rotation[2][0], rotation[2][1], rotation[2][2], translation[2]], [0, 0, 0, 1]])

        cam_ob.matrix_world = cam.matrixWorld
        if changePositionToM:
            cam_ob.location = mathutils.Vector((cam.location[0]/1000, cam.location[1]/1000, cam.location[2]/1000))
        else:
            cam_ob.location = mathutils.Vector((cam.location[0], cam.location[1], cam.location[2]))
        cam_ob.rotation_euler[0] = cam_ob.rotation_euler[0] + pi

        focal_lengths = cam.focalLength
        cam_ob.data.lens = focal_lengths
        cam_ob.data.sensor_fit = 'HORIZONTAL'
        cam_ob.data.sensor_width = cam.sensorSize[0]
        cam_ob.data.sensor_height = cam.sensorSize[1]
        cam_ob.data.shift_x = 0
        cam_ob.data.shift_y = 0

        if useDof:
            cam_ob.data.dof.use_dof = True
            cam_ob.data.dof.aperture_fstop = cam.aperture
            cam_ob.data.dof.focus_distance = cam.focusDistance / 1000 if changePositionToM else cam.focusDistance

        pixel_aspect = 1
        bpy.context.scene.render.pixel_aspect_x = 1.0
        bpy.context.scene.render.pixel_aspect_y = pixel_aspect

        if bpy.context.scene.unit_settings.length_unit == 'MILLIMETERS':
            cam_ob.location[0] = cam_ob.location[0] / 1000
            cam_ob.location[1] = cam_ob.location[1] / 1000
            cam_ob.location[2] = cam_ob.location[2] / 1000
        # else:
        #     sys.stderr.write("ERROR: CHANGE UNIT LENGTH TO MILLIMETERS")

        bpy.context.collection.objects.link(cam_ob)

def delAllCams():
    # orphan_cameras = [c for c in bpy.data.cameras if not c.users]
    orphan_cameras = [c for c in bpy.data.cameras]
    while orphan_cameras:
        bpy.data.cameras.remove(orphan_cameras.pop())



def enable_gpus(device_type, use_cpus=False):
    preferences = bpy.context.preferences
    cycles_preferences = preferences.addons["cycles"].preferences
    cuda_devices, opencl_devices = cycles_preferences.get_devices()

    if device_type == "CUDA":
        devices = cuda_devices
    elif device_type == "OPENCL":
        devices = opencl_devices
    else:
        raise RuntimeError("Unsupported device type")

    activated_gpus = []

    for device in devices:
        if device.type == "CPU":
            device.use = use_cpus
        else:
            device.use = True
            activated_gpus.append(device.name)

    print("Activated GPUS:", activated_gpus)
    cycles_preferences.compute_device_type = device_type
    bpy.context.scene.cycles.device = "GPU"

    return activated_gpus


