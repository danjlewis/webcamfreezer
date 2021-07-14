import cv2
import pyvirtualcam
import keyboard
import sys
import numpy as np
import time
import multiprocessing as mp

VERSION = '1.1.2'

DEFAULTS = {'freeze_hotkey': 'f13', 'loop_hotkey': 'f14', 'preview_hotkey': 'f15', 'fps': 30, 'width': 1280, 'height': 720, 'cam_index': 0}

ID_INSTRUCTIONS_PATH = 'id_instructions.png'
ID_INSTRUCTIONS_IMAGE = cv2.imread(ID_INSTRUCTIONS_PATH)

HOTKEY_STATUS = {'freeze': False, 'loop': False, 'preview': False}

def verify(value, parsing_func, fail_callback = None):
    try:
        return parsing_func(value)
    except Exception:
        if fail_callback != None:
            fail_callback()
        return None

def verify_fail_int():
    print("That's not a number! Exiting...")
    sys.exit(1)

def update_img():
    global img
    status, _img = camera.read()

    if not status:
        print("Camera capture failed! Exiting...")
        sys.exit(1)

    if channels == 3:
        r, g, b = cv2.split(_img)
        a = np.ones(r.shape, dtype = r.dtype)

    img = cv2.merge((b, g, r, a))
    return img

frozen = False
def toggle_freeze():
    global frozen
    frozen = not frozen
    if frozen:
        update_img()

looping = False
clip = []
clip_progress = 0
def toggle_loop():
    global looping, clip, clip_progress
    looping = not looping
    if not looping:
        clip = []
        clip_progress = 0

previewing = False
preview_process = None
preview_queue = mp.Queue()
def toggle_preview():
    global previewing, preview_process
    previewing = not previewing
    if previewing:
        preview_process = mp.Process(target = show_preview, args = (preview_queue, timeDelta))
        preview_process.start()
    else:
        preview_process.terminate()
        cv2.destroyWindow("Camera Preview")

def show_preview(queue, timeDelta):
    while True:
        cv2.imshow("Camera Preview", queue.get())
        cv2.waitKey(int(timeDelta * 1000))

if __name__ == '__main__':
    print(f"WebcamFreezer v{VERSION}")
    print("If you don't type anything for an option, a suitable default value will be chosen for you. If you don't know what to put, these are usually a good bet!", end = '\n\n')

    freeze_hotkey = input("What key should trigger a freeze? ")
    if freeze_hotkey == '':
        freeze_hotkey = DEFAULTS['freeze_hotkey']

    loop_hotkey = input("What key should trigger a loop? ")
    if loop_hotkey == '':
        loop_hotkey = DEFAULTS['loop_hotkey']

    preview_hotkey = input("What key should trigger a preview? ")
    if preview_hotkey == '':
        preview_hotkey = DEFAULTS['preview_hotkey']
    
    fps = input("What FPS should the virtual camera run at (30 FPS recommended)? ")
    if fps == '':
        fps = DEFAULTS['fps']
    else:
        fps = verify(fps, int, fail_callback = verify_fail_int)
        if fps <= 0:
            print("Invalid value! Exiting...")
            sys.exit(1)

    if fps > 30:
        choice = input("You selected an FPS above 30! This will usually have no effect on the quality of the video feed, and will slow down your PC. Do you still want to continue (0/1)? ")
        choice = verify(choice, int, fail_callback = verify_fail_int)

        if choice not in [0, 1]:
            print("That's not a 0 or a 1! Exiting...")
            sys.exit(1)
        elif not choice:
            sys.exit(0)

    timeDelta = 1 / fps

    resolution = input("What is the resolution of your camera (WIDTHxHEIGHT)? ").split('x')
    if resolution == ['']:
        width = DEFAULTS['width']
        height = DEFAULTS['height']
    else:
        if len(resolution) != 2:
            print("Invalid input! Exiting...")
            sys.exit(1)
        width, height = [verify(dimension, int, fail_callback = verify_fail_int) for dimension in resolution]

    while True:
        cam_index = input("Which camera do you want to use (type -1 for instructions on how to find your camera's ID)? ")
        if cam_index == '':
            cam_index = 0
            break
        else:
            cam_index = verify(cam_index, int, fail_callback = verify_fail_int)
            if cam_index == -1:
                cv2.imshow("Camera ID Instructions (press ESC to close)", ID_INSTRUCTIONS_IMAGE)
                while True:
                    if cv2.waitKey(0) == 27: # If ESC is pressed...
                        cv2.destroyAllWindows()
                        break
            else:
                break

    camera = cv2.VideoCapture(cam_index)
    camera.set(3, width)
    camera.set(4, height)

    try:
        _, _, channels = camera.read()[1].shape
    except AttributeError:
        print("Camera capture failed! Either the camera ID or resolution is incorrect! Exiting...")
        sys.exit(1)

    print("Ready!")

    with pyvirtualcam.Camera(width = width, height = height, fps = fps) as virtualcam:
        update_img()
        while True:
            if not HOTKEY_STATUS['freeze'] and keyboard.is_pressed(freeze_hotkey):
                toggle_freeze()
            if not HOTKEY_STATUS['loop'] and keyboard.is_pressed(loop_hotkey):
                toggle_loop()
            if not HOTKEY_STATUS['preview'] and keyboard.is_pressed(preview_hotkey):
                toggle_preview()

            HOTKEY_STATUS = {'freeze': keyboard.is_pressed(freeze_hotkey),
                                'loop': keyboard.is_pressed(loop_hotkey),
                                'preview': keyboard.is_pressed(preview_hotkey)}

            if not frozen:
                update_img()
            
            if looping:
                if HOTKEY_STATUS['loop']:
                    clip.append(img)
                else:
                    if clip != []:
                        try:
                            img = clip[clip_progress]
                        except IndexError:
                            clip_progress = 0
                            img = clip[clip_progress]
                        clip_progress += 1
                    else:
                        toggle_looping()

            if previewing:
                preview_queue.put(camera.read()[1])

            virtualcam.send(img)
            time.sleep(timeDelta)
