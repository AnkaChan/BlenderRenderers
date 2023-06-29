import os
import glob
import sys
import bpy
import mathutils
import json
import math
from bpy.props import *
from os.path import join
from pathlib import Path
import time
import copy

pi = 3.14159265358979

exampleObjList = [
    {
        "path": None,
        "translation": [0, 0, 0],
        "rotation": [0, 0, 0],
        "location": [0, 0, 0],
        "scaling": [0, 0, 0],
        "texture": "textureName",
        "smoothedRendering": True,
    },
]


class BWrapper:
    def __init__(s):
        s.cameraRotation = None
        s.cameraZoomIn = None

        # batched processing options
        s.renderStride = 1
        s.waitForNewFrames = False

        # rendering options
        s.globalAutoSmooth = False
        s.globalSubdiv = False
        s.globalSubdivLvl = 1

        s.fileId = 0
        s.fps = 60

    def renderObjects(s, objectList, outPath, ):

        for objInfo in objectList:
            print("Importing: ", objInfo['path'])

            # adjust camera focus
            cam_ob = bpy.context.scene.camera
            _, inModelExt = os.path.splitext(objInfo['path'])

            print("Importing ", inModelExt, " file.")
            if inModelExt == '.ply':
                bpy.ops.import_mesh.ply(filepath=objInfo['path'])
            elif inModelExt == '.obj':
                bpy.ops.import_scene.obj(filepath=objInfo['path'], )
            else:
                Exception()

            bpy.ops.object.select_all(action='DESELECT')
            obj = s.selectObjByPrefix(Path(objInfo['path']).stem)

            for i in range(3):
                if objInfo.get("rotation", None) and objInfo['rotation'][i] is not None:
                    obj.rotation_euler[i] = objInfo['rotation'][i]
                    # print("obj.rotation_euler", obj.rotation_euler)
                if objInfo.get("location", None) and objInfo['location'][i] is not None:
                    obj.location[i] = objInfo['location'][i]
                if objInfo.get("scale", None) and objInfo['scale'][i] is not None:
                    obj.scale[i] = objInfo['scale'][i]

            if objInfo.get("smoothedRendering", None):
                if objInfo['smoothedRendering']:
                    obj.data.use_auto_smooth = True
                    obj.data.auto_smooth_angle = math.radians(180)
                    mesh = obj.data
                    for f in mesh.polygons:
                        f.use_smooth = True
            elif s.globalAutoSmooth:
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = math.radians(180)
                mesh = obj.data
                for f in mesh.polygons:
                    f.use_smooth = True

            # subdivide surface
            if s.globalSubdiv:
                obj.modifiers.new('My SubDiv', 'SUBSURF')
                for mod in obj.modifiers:
                    if mod.type == 'SUBSURF':
                        mod.levels = s.globalSubdiv

            mat = bpy.data.materials.get(objInfo['texture'])

            if len(obj.material_slots) < 1:  # if no materials on the object
                obj.data.materials.append(mat)
                # this will create a slot and add the material
            else:
                obj.material_slots[obj.active_material_index].material = mat
                # if there are slots, assign the material to the active one

            obj.data.materials[0] = mat

        bpy.context.scene.render.filepath = outPath
        bpy.ops.render.render(write_still=True)

        for objInfo in objectList:
            bpy.ops.object.select_all(action='DESELECT')
            obj = s.selectObjByPrefix(Path(objInfo['path']).stem)
            bpy.ops.object.delete()

        for block in bpy.data.meshes:
            # print("block:", block.name)
            for objInfo in objectList:
                if block.users == 0 and s.checkNameByPrefix(block, Path(objInfo['path']).stem):
                    # print("Matched, deleting: ", block.name)
                    bpy.data.meshes.remove(block)

                    break

    def batchedRendering(s, inFolder, numFrames, outPath=None, cam_name="Camera", inModelExt="ply", filePrefix="A0"):
        bpy.context.scene.camera = bpy.context.scene.objects[cam_name]

        scene = bpy.data.scenes["Scene"]

        if s.cameraRotation is not None:
            s.rotSceneCamera(bpy.context.scene.camera, s.cameraRotation.startAngle)

        if outPath is None:
            outPath = inFolder + "\\Rendering"

        subdivLvl = 1
        doSubDiv = False

        inModelFiles = sorted(glob.glob(join(inFolder, "*." + inModelExt)))

        print("Number of Frames:", len(inModelFiles))

        os.makedirs(outPath, exist_ok=True)

        s.fileId = 0
        while True:
            if s.fileId >= numFrames:
                break
            if s.fileId >= len(inModelFiles):
                print("No more frames to render! Wait for 6 mins.")
                if s.waitForNewFrames:
                    time.sleep(60)
                    inModelFiles = sorted(glob.glob(join(inFolder, "*." + inModelExt)))
                    continue
                else:
                    break
        s.fileId = s.fileId + s.renderStride
        file = inModelFiles[s.fileId]

    def rotSceneCamera(s, camObj, rotAngle):
        camObj.camera.location.x = s.cameraRotation.radius * math.cos(
            math.radians(rotAngle)) + s.cameraRotation.centerX
        camObj.camera.location.y = s.cameraRotation.radius * math.sin(
            math.radians(rotAngle)) + s.cameraRotation.centerY
        camObj.camera.location.z = s.cameraRotation.zCoord

    def selectObjByName(s, name, type="MESH"):
        objects = bpy.context.scene.objects

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            if obj.type == type and obj.name == name:
                print(obj)
                obj.select_set(state=True)

                return obj

    def checkNameByPrefix(s, obj, prefix):
        if len(obj.name) >= len(prefix):
            if obj.name[:len(prefix)] == prefix:
                return True
        return False

    def selectObjByPrefix(s, prefix, type="MESH"):
        objects = bpy.context.scene.objects

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            # print(obj.name)
            if len(obj.name) >= len(prefix):

                if obj.type == type and obj.name[:len(prefix)] == prefix:
                    print(obj)
                    obj.select_set(state=True)

                    return obj
        # print("Didn't find object whose name starts with: ", prefix)


class CameraRotParameters:
    def __init__(s):
        s.centerX = 0  # center of the rotation of the camera
        s.centerY = 0
        s.zCoord = 12.8  # z coordinate. Will not change throughout the rotation

        s.camRotSteps = 180  # how many steps within the rotation
        s.radius = 24  # radius of the camera trajectory

        s.startAngle = 0


class CameraZoomIn:
    def __init__(s):
        s.lenStart = 22
        s.lenEnd = 35


class ObjectTransformation:
    def __init__(s):
        s.lenStart = 22
        s.lenEnd = 35


def renderImages(camNamesSelected, fileName, output_path):
    # output_path = r'/mnt/willow/Users/Anka/Blender/Output/'

    os.makedirs(output_path, exist_ok=True)

    # camSelected = range(0, 16, )

    for cam_idx in camNamesSelected:
        # cam_name = "Cam.{:03d}".format(cam_idx)
        # cam_name_out = camNames[cam_idx]
        # cam_name = "Cam.{:03d}".format(cam_idx)
        cam_name = cam_idx
        bpy.context.scene.camera = bpy.context.scene.objects[cam_name]
        print(cam_name)

        bpy.context.scene.render.filepath = os.path.join(output_path, fileName + '_' + cam_name)
        bpy.ops.render.render(write_still=True)


def renderAllCameras(outPath, camSpecs=None, filePreFix=''):
    for iCam, c in enumerate([obj for obj in bpy.data.objects if obj.type == 'CAMERA']):
        print("Rendering:", c.name)
        bpy.context.scene.camera = c

        if camSpecs is not None:
            camSpec = camSpecs[iCam]
            bpy.context.scene.render.resolution_x = camSpec.resolution[0]
            bpy.context.scene.render.resolution_y = camSpec.resolution[1]

        bpy.context.scene.render.filepath = os.path.join(outPath, filePreFix + c.name)
        bpy.ops.render.render(write_still=True)
