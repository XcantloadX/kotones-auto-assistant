# type: ignore
# source: https://github.com/hansalemaos/adbnativeblitz
# license: MIT
# requires: av

import base64
import ctypes
import os
import platform
import signal
import subprocess
import sys
import threading
from collections import deque
from functools import cache
import av
from time import sleep as sleep_
from math import floor


def sleep(secs):
    try:
        if secs == 0:
            return
        maxrange = 50 * secs
        if isinstance(maxrange, float):
            sleeplittle = floor(maxrange)
            sleep_((maxrange - sleeplittle) / 50)
            maxrange = int(sleeplittle)
        if maxrange > 0:
            for _ in range(maxrange):
                sleep_(0.016)
    except KeyboardInterrupt:
        return

iswindows = "win" in platform.platform().lower()
if iswindows:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    creationflags = subprocess.CREATE_NO_WINDOW
    invisibledict = {
        "startupinfo": startupinfo,
        "creationflags": creationflags,
        "start_new_session": True,
    }
    from ctypes import wintypes

    windll = ctypes.LibraryLoader(ctypes.WinDLL)
    kernel32 = windll.kernel32
    _GetShortPathNameW = kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD
else:
    invisibledict = {}


@cache
def get_short_path_name(long_name):
    try:
        if not iswindows:
            return long_name
        output_buf_size = 4096
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        _ = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        return output_buf.value
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        return long_name


def killthread(threadobject):
    # based on https://pypi.org/project/kthread/
    if not threadobject.is_alive():
        return True
    tid = -1
    for tid1, tobj in threading._active.items():
        if tobj is threadobject:
            tid = tid1
            break
    if tid == -1:
        sys.stderr.write(f"{threadobject} not found")
        return False
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid), ctypes.py_object(SystemExit)
    )
    if res == 0:
        return False
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        return False
    return True


def send_ctrl_commands(pid, command=0):
    if iswindows:
        commandstring = r"""import ctypes, sys; CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT = 0, 1, 2, 3, 4; kernel32 = ctypes.WinDLL("kernel32", use_last_error=True); (lambda pid, cmdtosend=CTRL_C_EVENT: [kernel32.FreeConsole(), kernel32.AttachConsole(pid), kernel32.SetConsoleCtrlHandler(None, 1), kernel32.GenerateConsoleCtrlEvent(cmdtosend, 0), sys.exit(0) if isinstance(pid, int) else None])(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else None) if __name__ == '__main__' else None"""
        subprocess.Popen(
            [sys.executable, "-c", commandstring, str(pid), str(command)],
            **invisibledict,
        )
    else:
        os.kill(pid, signal.SIGINT)


class StopDescriptor:
    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not value:
            instance.__dict__[self.name] = False
        else:
            instance.__dict__[self.name] = True
            instance.stop_capture()

    def __delete__(self, instance):
        sys.stderr.write("Cannot be deleted!")

    def __set_name__(self, owner, name):
        self.name = name


class AdbFastScreenshots:
    stop_recording = StopDescriptor()

    def __init__(
        self,
        adb_path,
        device_serial,
        time_interval=179,
        width=1600,
        height=900,
        bitrate="20M",
        use_busybox=False,
        connect_to_device=True,
        screenshotbuffer=10,
        go_idle=0,
    ):
        r"""Capture Android device screen using ADB's screenrecord with high frame rate.

            This class allows capturing the screen of an Android device using ADB's screenrecord
            command with an improved frame rate. It continuously captures frames from the device
            and provides them as NumPy arrays to the caller.

            Args:
                adb_path (str): The path to the ADB executable.
                device_serial (str): The serial number of the target Android device.
                time_interval (int): The maximum duration, in seconds, for each screen recording session (up to a maximum of 180 seconds). After reaching this time limit, a new recording session automatically starts without causing interruptions to the user experience.
                width (int): The width of the captured screen.
                height (int): The height of the captured screen.
                bitrate (str): The bitrate for screen recording (e.g., "20M" for 20Mbps).
                use_busybox (bool): Whether to use BusyBox for base64 encoding.
                connect_to_device (bool): Whether to connect to the device using ADB.
                screenshotbuffer (int): The size of the frame buffer to store the last captured frames.
                go_idle (float): The idle time (in seconds) when no new frames are available. # higher value -> less fps, but also less CPU usage.

            Attributes:
                stop_recording (bool): Control attribute to stop the screen capture.

            Methods:
                stop_capture(): Stops the screen capture.

            Usage:
                import cv2
                from adbnativeblitz import AdbFastScreenshots

                with AdbFastScreenshots(
                    adb_path=r"C:\Android\android-sdk\platform-tools\adb.exe",
                    device_serial="127.0.0.1:5555",
                    time_interval=179,
                    width=1600,
                    height=900,
                    bitrate="20M",
                    use_busybox=False,
                    connect_to_device=True,
                    screenshotbuffer=10,
                    go_idle=0,
                ) as adbscreen:
                    for image in adbscreen:
                        cv2.imshow("CV2 WINDOW", image)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                cv2.destroyAllWindows()


            Note:
            - The `AdbFastScreenshots` class should be used in a context manager (`with` statement).
            - The `stop_capture()` method can be called to stop the screen capture.
            - The frames are continuously captured and provided in the form of NumPy arrays.
            - The class aims to achieve a higher frame rate by avoiding slow subprocess creation
              for each screen capture session.
            """

        self.stop_recording = False
        self.size = f"{width}x{height}"
        self.width = width
        self.height = height
        self.timelimit = time_interval
        self.bitrate = bitrate
        self.use_busybox = use_busybox
        self.adb_path = get_short_path_name(adb_path)
        self.device_serial = device_serial
        if connect_to_device:
            subprocess.run(
                [self.adb_path, "connect", self.device_serial], **invisibledict
            )
        self.threadlock = threading.Lock()
        self.codec = av.codec.CodecContext.create("h264", "r")
        self.lastframes = deque([], screenshotbuffer)
        self.command_to_execute = (
            f"""#!/bin/bash
startscreenrecord() {{

    screenrecord --output-format=h264 --time-limit "$1" --size "$2" --bit-rate "$3" -
}}

time_interval={self.timelimit}
size="{self.size}"
bitrate="{self.bitrate}"
#screenrecord --output-format=h264 --time-limit 1 --size "$size" --bit-rate "$bitrate" -
while true; do
    startscreenrecord $time_interval "$size" "$bitrate" 
done"""
            + "\n"
        )
        self.base64cmd = self.format_adb_command(
            self.command_to_execute,
            su=False,
            exitcommand="",
            errors="strict",
        )
        self.p = None
        self.threadstdout = None
        self.framecounter = 0
        self.go_idle = go_idle

    def format_adb_command(
        self,
        cmd,
        su=False,
        exitcommand="DONE",
        errors="strict",
    ):
        if su:
            cmd = f"su -- {cmd}"
        if exitcommand:
            cmd = cmd.rstrip() + f"\necho {exitcommand}\n"
        nolimitcommand = []
        base64_command = base64.standard_b64encode(cmd.encode("utf-8", errors)).decode(
            "utf-8", errors
        )
        nolimitcommand.extend(["echo", base64_command, "|"])
        if self.use_busybox:
            nolimitcommand.extend(["busybox"])
        nolimitcommand.extend(["base64", "-d", "|", "sh"])

        return " ".join(nolimitcommand) + "\n"

    def _start_capturing(self):
        def _execute_stdout_read():
            try:
                for q in iter(self.p.stdout.readline, b""):
                    if iswindows:
                        q = q.replace(b"\r\n", b"\n")
                    if q:
                        alldata.append(q)
                    if alldata:
                        joineddata = b"".join(alldata)
                        try:
                            packets = self.codec.parse(joineddata)
                            if packets:
                                for pack in packets:
                                    frames = self.codec.decode(pack)
                                    for frame in frames:
                                        nparray = (
                                            frame.to_rgb()
                                            .reformat(
                                                width=self.width,
                                                height=self.height,
                                                format="bgr24",
                                            )
                                            .to_ndarray()
                                        )
                                        try:
                                            self.threadlock.acquire()
                                            self.lastframes.append(nparray)
                                            self.framecounter += 1

                                        finally:
                                            try:
                                                self.threadlock.release()
                                            except Exception as e:
                                                sys.stderr.write(f"{e}\n")
                            alldata.clear()
                        except Exception as e:
                            sys.stderr.write(f"{e}\n")
            except Exception as e:
                sys.stderr.write(f"{e}\n")

        self.p = subprocess.Popen(
            [self.adb_path, "-s", self.device_serial, "shell", self.base64cmd],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=0,
            **invisibledict,
        )
        alldata = []
        self.threadstdout = threading.Thread(target=_execute_stdout_read)
        self.threadstdout.daemon = True
        self.threadstdout.start()

    def _stop_capture(self):
        try:
            if iswindows:
                subprocess.Popen(f"taskkill /F /PID {self.p.pid} /T", **invisibledict)
        except:
            pass
        try:
            self.p.stdout.close()
        except:
            pass
        try:
            killthread(self.threadstdout)
        except:
            pass

    def stop_capture(self):
        send_ctrl_commands(self.p.pid, command=0)
        try:
            sleep(1)
        except KeyboardInterrupt:
            pass
        self._stop_capture()

    def __iter__(self):
        oldframecounter = 0

        self._start_capturing()
        sleep(0.05)
        while not self.stop_recording:
            if not self.lastframes:
                sleep(0.005)
                continue
            yield self.lastframes[-1].copy()
            if oldframecounter == self.framecounter:
                if self.go_idle:
                    sleep(self.go_idle)
            oldframecounter = self.framecounter

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop_recording = True
       
        
if __name__ == "__main__":
    import cv2

    with AdbFastScreenshots(
        adb_path=r"D:\SDK\Android\platform-tools\adb.exe",
        device_serial="127.0.0.1:16384",
        time_interval=179,
        width=720,
        height=1280,
        bitrate="20M",
        use_busybox=False,
        connect_to_device=True,
        screenshotbuffer=10,
        go_idle=0,
    ) as adbscreen:
        for image in adbscreen:
            cv2.imshow("CV2 WINDOW", image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cv2.destroyAllWindows()