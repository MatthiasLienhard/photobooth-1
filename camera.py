#!/usr/bin/env python
# Created by br@re-web.eu, 2015

import subprocess

from PIL import Image, ImageDraw
import io
import cv2
import warnings
from time import sleep
import filter

try:
    import gphoto2cffi as gp
    import gphoto2cffi.errors as gpErrors
    gphoto_enabled = True
except ImportError:
    gphoto_enabled=False
    warnings.warn("gphoto module not installed. To use DSLR/digicams install gphoto2cffi module.")


try:
    import picamera
    picam_enabled=True
except ImportError:
    picam_enabled=False
    warnings.warn("raspberry pi module not installed. To use PiCam install picamera module.")

class CameraException(Exception):
    """Custom exception class to handle camera class errors"""
    def __init__(self, message, recoverable=False):
        self.message = message
        self.recoverable = recoverable

class Camera:
    def __init__(self, picture_size,preview_size, focal_length=30):
        self.picture_size = picture_size
        self.focal_length = focal_length
        self.preview_size=preview_size
    def get_test_image(self, size):
        img = Image.new('RGB', size, color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Testimage", fill=(255, 255, 0))
        return(img)

    def get_preview_frame(self, filename=None):
        img=self.get_test_image(self.preview_size)
        if filename is not None:
            img.save(filename)
        else:
            return img
    def take_picture(self, filename="/tmp/picture.jpg"):
        img=self.get_test_image(self.picture_size)
        if filename is not None:
            img.save(filename)
        else:
            return img

    def set_idle(self):
        pass
    def start_preview_stream(self):
        pass
    def stop_preview_stream(self):
        pass
    def focus(self):
        pass
    def get_zoom(self):
        return self.focal_length

    def set_zoom(self, focal_length):
        self.focal_length=focal_length
        return self.focal_length




class Camera_cv(Camera):
    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self,picture_size, preview_size, zoom)
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            raise CameraException("No webcam found!")
        fps=10

        self.cam.set(3, picture_size[0])
        self.cam.set(4, picture_size[1])
        self.cam.set(4, fps)

    def get_preview_frame(self, filename=None, filter=None):
        return(self._take_picture(filename, filter, size=self.preview_size))

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        return (self._take_picture(filename, filter, size=self.picture_size))

    def _take_picture(self, filename, filter, size):
        frame = cv2.resize( self.cam.read()[1], size)
        if filename is not None and filter is None:
            cv2.imwrite(filename, frame)
        else:
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            if filter is not None:
                img=filter.apply(img)
            return(img)

class Camera_pi(Camera):

    def __init__(self, picture_size,preview_size, zoom =30):
        Camera.__init__(self,picture_size, preview_size, zoom)
        if not picam_enabled:
            raise CameraException("No PiCam module")
        try:
            self.cam = picamera.PiCamera( framerate=10)
            self.cam.rotation = 0
            self.cam.start_preview(alpha=0) # invisible preview
        except picamera.PiCameraError:
            raise CameraException("Cannot initialize PiCam")
        self.preview_stream=None
        self.preview_active=False

    def start_preview_stream(self):
        self.preview_stream = picamera.PiCameraCircularIO(self.cam, seconds=1) # 17 MB
        self.cam.start_recording(self.preview_stream, format='mjpeg',resize=self.preview_size)
        self.preview_acitve = True

    def stop_preview_stream(self):
        self.cam.stop_recording()
        self.preview_acitve=False


    def get_preview_frame(self, filename=None, filter=None):
        if not self.preview_active:
            raise CameraException("preview inactive")
        data = self.preview_stream.read1()
        data = io.BytesIO(data)
        img = Image.open(data)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)

    def take_picture(self, filename=None, filter=None):
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', resize=self.picture_size)
        img=Image.open(stream)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)
        # self.cam.capture(filename)



class Camera_gPhoto(Camera):
    """Camera class providing functionality to take pictures using gPhoto 2"""

    def __init__(self, picture_size, preview_size, zoom=30):
        Camera.__init__(self,picture_size, preview_size, zoom)
        # Print the capabilities of the connected camera
        try:
            self.cam = gp.Camera()
        except gpErrors.UnsupportedDevice as e:
            raise CameraException("Can not initialize gphoto camera: "+str(e))

    def start_preview_stream(self):
        if 'viewfinder' in self.cam._get_config()['actions']:
            self.cam._get_config()['actions']['viewfinder'].set(True)
        else:
            self.cam.get_preview()

    def stop_preview_stream(self):
        if 'viewfinder' in self.cam._get_config()['actions']:
            self.cam._get_config()['actions']['viewfinder'].set(False)


    def get_preview_frame(self, filename=None, filter=None):
        data=self.cam.get_preview()
        preview = Image.open(io.BytesIO(data))
        if filename is None:
            return(preview)
        else:
            preview.save(filename)
        # raise CameraException("No preview supported!")

    def take_picture(self, filename="/tmp/picture.jpg", filter=None):
        img=self.cam.capture()
        img=Image.open(img)
        if filter is not None:
            img = filter.apply(img)
        if filename is None:
            return(img)
        else:
            img.save(filename)



    def press_half(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            print("press half")
            self.cam._get_config()['actions']['eosremoterelease'].set('Press Half')#

    def release_full(self):
        if 'eosremoterelease' in self.cam._get_config()['actions']:
            print("release full")
            self.cam._get_config()['actions']['eosremoterelease'].set('Release Full')#

    def focus(self):
        pass
        # todo:define function