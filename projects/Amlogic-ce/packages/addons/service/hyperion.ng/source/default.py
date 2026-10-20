# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2018-present Team CoreELEC (https://coreelec.org)

import os
import select
import socket
import sys
import time

import xbmc
import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))

import flatbuffers
from hyperionnet import Image, RawImage, Register, Request
from hyperionnet.Command import Command
from hyperionnet.ImageType import ImageType
from hyperionnet.Reply import Reply

HYPERIOND_ADDRESS = ('127.0.0.1', 19400)
ORIGIN = 'Kodi'
# the lowest priority the flatbuffer server accepts
PRIORITY = 199
# endless, hyperiond clears our priority when the connection closes
IMAGE_DURATION = -1
FEED_OFF = 0
FEED_PLAYBACK = 1
FEED_ALL = 2
CAPTURE_WIDTH = 128
CAPTURE_HEIGHT = 72
# about 20 images per second
FRAME_INTERVAL = 0.05
MIN_WAIT = 0.001
FRAME_TIMEOUT_MS = 200
# hyperiond drops a client that sends nothing for its timeout, 1 s at the least, and would keep
# the last image until then
IMAGE_TIMEOUT = 1
RECONNECT_INTERVAL = 1


def log(message, level=xbmc.LOGINFO):
    xbmc.log('service.hyperion.ng: {}'.format(message), level)


class Feeder(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.player = xbmc.Player()
        self.screensaver = xbmc.getCondVisibility('System.ScreenSaverActive')
        self.feed = xbmcaddon.Addon().getSettingInt('KODI_FEED')
        self.capture = None
        self.builder = flatbuffers.Builder(CAPTURE_WIDTH * CAPTURE_HEIGHT * 4)
        self.sock = None
        self.received = bytearray()
        self.registered = False
        self.error = None
        self.fed_at = 0
        self.connect_at = 0
        self.connect_failed = False

    def onSettingsChanged(self):
        self.feed = xbmcaddon.Addon().getSettingInt('KODI_FEED')

    def onScreensaverActivated(self):
        self.screensaver = True

    def onScreensaverDeactivated(self):
        self.screensaver = False

    def feeding(self):
        if self.feed == FEED_OFF or self.screensaver:
            return False
        if self.feed == FEED_PLAYBACK:
            return self.player.isPlayingVideo()
        return True

    def grab(self):
        if self.capture is None:
            self.capture = xbmc.RenderCapture()
        self.capture.capture(CAPTURE_WIDTH, CAPTURE_HEIGHT, composite=True)
        image = self.capture.getImage(FRAME_TIMEOUT_MS)
        width = self.capture.getWidth()
        height = self.capture.getHeight()
        if len(image) != width * height * 4:
            return None
        rgb = bytearray(width * height * 3)
        rgb[0::3] = image[2::4]
        rgb[1::3] = image[1::4]
        rgb[2::3] = image[0::4]
        return rgb, width, height

    def connect(self):
        if self.sock is not None:
            return True
        if time.monotonic() < self.connect_at:
            return False
        try:
            self.sock = socket.create_connection(HYPERIOND_ADDRESS, timeout=1)
        except OSError:
            if not self.connect_failed:
                log('cannot connect to hyperiond at {}:{}'.format(*HYPERIOND_ADDRESS), xbmc.LOGWARNING)
                self.connect_failed = True
            self.connect_at = time.monotonic() + RECONNECT_INTERVAL
            return False
        self.connect_failed = False
        self.registered = False
        self.error = None
        self.fed_at = time.monotonic()
        return True

    def disconnect(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        self.received.clear()

    def lost(self):
        self.disconnect()
        self.connect_at = time.monotonic() + RECONNECT_INTERVAL

    def receive(self):
        # every request gets a reply, and hyperiond also sends one unasked when our priority left
        # its muxer
        while select.select([self.sock], [], [], 0)[0]:
            data = self.sock.recv(4096)
            if not data:
                return False
            self.received += data
        while len(self.received) >= 4:
            size = int.from_bytes(self.received[:4], 'big')
            if len(self.received) < size + 4:
                break
            try:
                reply = Reply.GetRootAs(bytes(self.received[4:size + 4]))
                error = reply.Error()
                registered = reply.Registered()
            except Exception:
                log('invalid reply from hyperiond', xbmc.LOGWARNING)
                return False
            del self.received[:size + 4]
            if error is not None and error != self.error:
                log('hyperiond refused a request: {}'.format(error.decode(errors='replace')),
                    xbmc.LOGWARNING)
                self.error = error
            if error is not None or registered == -1:
                self.registered = False
        return True

    def send(self, command_type, command):
        builder = self.builder
        Request.Start(builder)
        Request.AddCommandType(builder, command_type)
        Request.AddCommand(builder, command)
        builder.Finish(Request.End(builder))
        data = builder.Output()
        try:
            self.sock.sendall(len(data).to_bytes(4, 'big') + data)
            if self.receive():
                return True
        except OSError:
            pass
        self.lost()
        return False

    def register(self):
        builder = self.builder
        builder.Clear()
        origin = builder.CreateString(ORIGIN)
        Register.Start(builder)
        Register.AddOrigin(builder, origin)
        Register.AddPriority(builder, PRIORITY)
        self.registered = True
        return self.send(Command.Register, Register.End(builder))

    def image(self, rgb, width, height):
        builder = self.builder
        builder.Clear()
        data = builder.CreateByteVector(rgb)
        RawImage.Start(builder)
        RawImage.AddData(builder, data)
        RawImage.AddWidth(builder, width)
        RawImage.AddHeight(builder, height)
        raw = RawImage.End(builder)
        Image.Start(builder)
        Image.AddDataType(builder, ImageType.RawImage)
        Image.AddData(builder, raw)
        Image.AddDuration(builder, IMAGE_DURATION)
        return self.send(Command.Image, Image.End(builder))

    def run(self):
        while not self.abortRequested():
            started = time.monotonic()
            if not self.feeding():
                self.capture = None
                self.disconnect()
            elif not self.connect():
                self.capture = None
            else:
                image = self.grab()
                now = time.monotonic()
                if image is not None:
                    if not self.registered:
                        self.register()
                    if self.sock is not None and self.image(*image):
                        self.fed_at = now
                elif now - self.fed_at >= IMAGE_TIMEOUT:
                    self.lost()
            # a timeout of 0 waits forever
            if self.waitForAbort(max(MIN_WAIT, FRAME_INTERVAL - (time.monotonic() - started))):
                break
        self.disconnect()


if __name__ == '__main__':
    Feeder().run()
