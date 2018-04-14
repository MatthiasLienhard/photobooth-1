#!/usr/bin/env python
# Created by br _at_ re-web _dot_ eu, 2015
#from photobooth import Photobooth
import tkinter as tk
from PIL import Image
import pygame
import time
import threading
import scipy.ndimage
import numpy as np
import random
#import pygame.event as EventModule
import pygame.event
import events

GPIOEVENT=pygame.USEREVENT+1
TIMEREVENT=pygame.USEREVENT+2


class GuiException(Exception):
    """Custom exception class to handle GUI class errors"""


class GUI_PyGame:
    """A GUI class using PyGame"""

    def __init__(self, name, size, hide_mouse=True, fullscreen=True):
        # Call init routines
        pygame.init()
        #if hasattr(pygame.event, 'init'):
        #pygame.event.init()

        # Window name
        pygame.display.set_caption(name)

        # Hide mouse cursor
        if hide_mouse:
            pygame.mouse.set_cursor(*pygame.cursors.load_xbm('transparent.xbm', 'transparent.msk'))

        # Store screen and size
        self.size = size
        if fullscreen:
            mode=pygame.FULLSCREEN
        else:
            mode=pygame.NOFRAME

        self.screen = pygame.display.set_mode(size, mode)
        self.gpio   = events.Rpi_GPIO(self.trigger_gpio_event)

        # Clear screen
        self.clear()
        self.apply()

    def clear(self, color=(0, 0, 0)):
        self.screen.fill(color)
        self.surface_list = []

    def apply(self):
        for surface in self.surface_list:
            self.screen.blit(surface[0], surface[1])
        pygame.display.update()

    def get_size(self):
        return self.size

    @staticmethod
    def trigger_gpio_event( event_channel):#trigger_GPIO event
        pygame.event.post(pygame.event.Event(GPIOEVENT, channel=event_channel))

    @staticmethod
    def trigger_timer_event():
        pygame.event.post(pygame.event.Event(TIMEREVENT))

    def show_picture(self, image = None, size=(0, 0), offset=(0, 0), flip=False):

        # Use window size if none given
        if size == (0, 0):
            size = self.size
        if type(image) is str:
            filename=image
            try:
                # Load image from file
                image = pygame.image.load(filename)
            except pygame.error as msg:
                raise GuiException("ERROR: Can't open image '" + filename + "': " + str(msg))
        else:
            try:
                mode = image.mode
                if mode is 'L':
                    rgbimg = Image.new("RGBA", image.size)
                    rgbimg.paste(image)
                    image=rgbimg
                    mode=image.mode
                size = image.size
                data = image.tobytes()


                image = pygame.image.fromstring(data, size, mode)
                #image = pygame.image.frombuffer(image_buf, size, format="RGB")
            except pygame.error as msg:
                raise GuiException("ERROR: Can't read image from buffer: " + msg)


        # Extract image size and determine scaling
        image_size = image.get_rect().size
        image_scale = min([min(a, b) / b for a, b in zip(size, image_size)])
        # New image size
        new_size = [int(a * image_scale) for a in image_size]
        # Update offset
        offset = tuple(a + int((b - c) / 2) for a, b, c in zip(offset, size, new_size))
        # Apply scaling and display picture
        image = pygame.transform.scale(image, new_size).convert()
        # Create surface and blit the image to it
        surface = pygame.Surface(new_size)
        surface.blit(image, (0, 0))
        if flip:
            surface = pygame.transform.flip(surface, True, False)
        self.surface_list.append((surface, offset))

    def show_message(self, msg, color=(0, 0, 0), bg=(230, 230, 230), transparency=True, outline=(245, 245, 245)):
        # Choose font
        font = pygame.font.Font(None, 144)
        # Wrap and render text
        wrapped_text, text_height = self.wrap_text(msg, font, self.size)
        rendered_text = self.render_text(wrapped_text, text_height, 1, 1, font, color, bg, transparency, outline)

        self.surface_list.append((rendered_text, (0, 0)))

    def show_button(self, text, pos, size=(0, 0), color=(230, 230, 230), bg=(0, 0, 0), transparency=True,
                    outline=(230, 230, 230)):
        # Choose font
        font = pygame.font.Font(None, 72)
        text_size = font.size(text)
        if size == (0, 0):
            size = (text_size[0] + 4, text_size[1] + 4)
        offset = ((size[0] - text_size[0]) // 2, (size[1] - text_size[1]) // 2)

        # Create Surface object and fill it with the given background
        surface = pygame.Surface(self.size)
        surface.fill(bg)

        # Render text
        rendered_text = font.render(text, 1, color)
        surface.blit(rendered_text, pos)

        # Render outline
        pygame.draw.rect(surface, outline, (pos[0] - offset[0], pos[1] - offset[0], size[0], size[1]), 1)

        # Make background color transparent
        if transparency:
            surface.set_colorkey(bg)

        self.surface_list.append((surface, (0, 0)))

    def wrap_text(self, msg, font, size):
        final_lines = []  # resulting wrapped text
        requested_lines = msg.splitlines()  # wrap input along line breaks
        accumulated_height = 0  # accumulated height

        # Form a series of lines
        for requested_line in requested_lines:
            # Handle too long lines
            if font.size(requested_line)[0] > size[0]:
                # Split at white spaces
                words = requested_line.split(' ')
                # if any of our words are too long to fit, trim them
                for word in words:
                    while font.size(word)[0] >= size[0]:
                        word = word[:-1]
                # Start a new line
                accumulated_line = ""
                # Put words on the line as long as they fit
                for word in words:
                    test_line = accumulated_line + word + " "
                    # Build the line while the words fit.   
                    if font.size(test_line)[0] < size[0]:
                        accumulated_line = test_line
                    else:
                        # Start a new line
                        line_height = font.size(accumulated_line)[1]
                        if accumulated_height + line_height > size[1]:
                            break
                        else:
                            accumulated_height += line_height
                            final_lines.append(accumulated_line)
                            accumulated_line = word + " "
                            # Finish requested_line
                line_height = font.size(accumulated_line)[1]
                if accumulated_height + line_height > size[1]:
                    break
                else:
                    accumulated_height += line_height
                    final_lines.append(accumulated_line)
            # Line fits as it is
            else:
                accumulated_height += font.size(requested_line)[1]
                final_lines.append(requested_line)

        # Check height of wrapped text
        if accumulated_height >= size[1]:
            raise GuiException("Wrapped text is too high to fit.")

        return final_lines, accumulated_height

    def render_text(self, text, text_height, valign, halign, font, color, bg, transparency, outline):
        # Determine vertical position
        if valign == 0:  # top aligned
            voffset = 0
        elif valign == 1:  # centered
            voffset = int((self.size[1] - text_height) / 2)
        elif valign == 2:  # bottom aligned
            voffset = self.size[1] - text_height
        else:
            raise GuiException("Invalid valign argument: " + str(valign))

        # Create Surface object and fill it with the given background
        surface = pygame.Surface(self.size)
        surface.fill(bg)

        # Blit one line after another
        accumulated_height = 0
        for line in text:
            maintext = font.render(line, 1, color)
            shadow = font.render(line, 1, outline)
            if halign == 0:  # left aligned
                hoffset = 0
            elif halign == 1:  # centered
                hoffset = (self.size[0] - maintext.get_width()) / 2
            elif halign == 2:  # right aligned
                hoffset = self.size[0] - maintext.get_width()
            else:
                raise GuiException("Invalid halign argument: " + str(halign))
            pos = (hoffset, voffset + accumulated_height)
            # Outline
            surface.blit(shadow, (pos[0] - 1, pos[1] - 1))
            surface.blit(shadow, (pos[0] - 1, pos[1] + 1))
            surface.blit(shadow, (pos[0] + 1, pos[1] - 1))
            surface.blit(shadow, (pos[0] + 1, pos[1] + 1))
            # Text
            surface.blit(maintext, pos)
            accumulated_height += font.size(line)[1]

        # Make background color transparent
        if transparency:
            surface.set_colorkey(bg)

        # Return the rendered surface
        return surface

    def convert_event(self, event):
        if event.type == pygame.QUIT:
            return True, events.Event(0, 0)
        elif event.type == pygame.KEYDOWN:
            return True, events.Event(1, event.key)
        elif event.type == pygame.MOUSEBUTTONUP:
            return True, events.Event(2, (event.button, event.pos))
        elif event.type == GPIOEVENT: #GPIO event
            return True, events.Event(3, event.channel)
        elif event.type == TIMEREVENT: #timer event
            return True, events.Event(4)
        else:
            return False, ''

    def check_for_event(self):
        for event in pygame.event.get():
            r, e = self.convert_event(event)
            if r:
                return r, e
        return False, ''

    def wait_for_event(self, time=None):
        # Repeat until a relevant event happened

        if time is not None:
            t = threading.Timer(time, self.trigger_timer_event)
            t.start()
        while True:
            # Discard all input that happened before entering the loop
            pygame.event.get()

            # Wait for event
            event = pygame.event.wait()
            # Return Event-Object
            r, e = self.convert_event(event)
            if r:
                if time is not None and t.is_alive():
                    t.cancel()
                return e
            else:
                pass
                # print("discarded pygames event of type {}".format(event.type))

    def set_timer(self, sec):
        #triggers timer event every [sec] seconds
        pygame.time.set_timer(TIMEREVENT, sec * 1000)


    def teardown(self):
        self.gpio.teardown()
        pygame.quit()

"""
class TkGUI(tk.Tk):
    def __init__(self,photobooth):
        super.__init__(photobooth)
        pad=3
        self.display_size=(self.winfo_screenwidth()-pad, self.winfo_screenheight())
        self.geometry("{0}x{1}+0+0".format(self.winfo_screenwidth()-pad, self.winfo_screenheight()-pad))
        self.photobooth=photobooth
        self.display_page=StartDisplay(self.photobooth)
        self.bind('<Return>', self.display_page.options[0])
        self.bind('<Left>', self.display_page.options[1])
        self.bind('<Right>', self.display_page.options[2])
    def teardown(self):
        #todo: cleanup
        exit(0)
    def add_overlay_text(self, text, col=(0,0,0), size=None, pos=(1,1), font="arial"):
        if size is None:
            size=self.resolution
        ol_mask=self.text_overlay(text, size, font )
        self.bg[ol_mask]=col

    def text_overlay(text, size, font):
        # modified from
        # https://stackoverflow.com/questions/45947608/rendering-a-unicode-ascii-character-to-a-numpy-array
        # Availability is platform dependent
        # Create font
        pil_font = PIL.ImageFont.truetype(font + ".ttf", size=size // len(text),
                                      encoding="unic")
        text_width, text_height = pil_font.getsize(text)

        # create a blank canvas with extra space between lines
        canvas = PIL.Image.new('RGB', [size, size], (255, 255, 255))

        # draw the text onto the canvas
        draw = PIL.ImageDraw.Draw(canvas)
        offset = ((size - text_width) // 2,
                  (size - text_height) // 2)
        white = "#000000"
        draw.text(offset, text, font=pil_font, fill=white)

        # Convert the canvas into an array with values in [0, 1]
        return np.asarray(canvas).astype(bool)
"""

if __name__ == "__main__":
    gui=TkGUI(Photobooth())
    gui.mainloop()

