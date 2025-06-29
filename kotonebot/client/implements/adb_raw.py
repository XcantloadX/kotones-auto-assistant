import os
import time
import subprocess
import struct
from threading import Thread, Lock
from functools import cached_property
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike
from adbutils._utils import adb_path

from .adb import AdbImpl, AdbImplConfig, _create_adb_device_base
from adbutils._device import AdbDevice as AdbUtilsDevice
from ..registration import register_impl
from kotonebot import logging

logger = logging.getLogger(__name__)

WAIT_TIMEOUT = 10
MAX_RETRY_COUNT = 5
SCRIPT: str = """#!/bin/sh
while true; do
    screencap
    sleep 0.3
done
"""

class AdbRawImpl(AdbImpl):
    def __init__(self, adb_connection: AdbUtilsDevice):
        super().__init__(adb_connection)
        self.__worker: Thread | None = None
        self.__process: subprocess.Popen | None = None
        self.__data: MatLike | None = None
        self.__retry_count = 0
        self.__lock = Lock()
        self.__stopping = False

    def __cleanup_worker(self) -> None:
        if self.__process:
            try:
                self.__process.kill()
            except:
                pass
            self.__process = None
        if self.__worker:
            try:
                self.__worker.join()
            except:
                pass
            self.__worker = None
        self.__data = None

    def __start_worker(self) -> None:
        self.__stopping = True
        self.__cleanup_worker()
        self.__stopping = False
        self.__worker = Thread(target=self.__worker_thread_with_retry, daemon=True)
        self.__worker.start()

    def __worker_thread_with_retry(self) -> None:
        try:
            self.__worker_thread()
        except Exception as e:
            logger.error(f"Worker thread failed: {e}")
            with self.__lock:
                self.__retry_count += 1
            raise

    def __worker_thread(self) -> None:
        with open('screenshot.sh', 'w', encoding='utf-8', newline='\n') as f:
            f.write(SCRIPT)
        self.adb.push('screenshot.sh', '/data/local/tmp/screenshot.sh')
        self.adb.shell(f'chmod 755 /data/local/tmp/screenshot.sh')
        os.remove('screenshot.sh')

        cmd = fr'{adb_path()} -s {self.adb.serial} exec-out "sh /data/local/tmp/screenshot.sh"'
        self.__process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        
        while not self.__stopping and self.__process.poll() is None:
            if self.__process.stdout is None:
                logger.error("Failed to get stdout from process")
                continue
            
            # 解析 header  
            # https://stackoverflow.com/questions/22034959/what-format-does-adb-screencap-sdcard-screenshot-raw-produce-without-p-f
            if self.__api_level >= 26:
                metadata = self.__process.stdout.read(16)
                w, h, p, c = struct.unpack('<IIII', metadata)
                # w=width, h=height, p=pixel_format, c=color_space
                # 详见：https://android.googlesource.com/platform/frameworks/base/+/26a2b97dbe48ee45e9ae70110714048f2f360f97/cmds/screencap/screencap.cpp#209
            else:
                metadata = self.__process.stdout.read(12)
                w, h, p = struct.unpack('<III', metadata)
            if p == 1: # PixelFormat.RGBA_8888
                channel = 4
            else:
                raise ValueError(f"Unsupported pixel format: {p}")
            data_size = w * h * channel

            if (data_size < 100 * 100 * 4) or (data_size > 3000 * 3000 * 4):
                raise ValueError(f"Invaild data_size: {w}x{h}.")

            # 读取图像数据
            # logger.verbose(f"receiving image data: {w}x{h} {data_size} bytes")
            image_data = self.__process.stdout.read(data_size)
            if not isinstance(image_data, bytes) or len(image_data) != data_size:
                logger.error(f"Failed to read image data, expected {data_size} bytes but got {len(image_data) if isinstance(image_data, bytes) else 'non-bytes'}")
                raise RuntimeError("Failed to read image data")
                
            np_data = np.frombuffer(image_data, np.uint8)
            np_data = np_data.reshape(h, w, channel)
            self.__data = cv2.cvtColor(np_data, cv2.COLOR_RGBA2BGR)

    @cached_property
    def __api_level(self) -> int:
        try:
            output = self.adb.shell("getprop ro.build.version.sdk")
            assert isinstance(output, str)
            return int(output.strip())
        except Exception as e:
            logger.error(f"Failed to get API level: {e}")
            return 0

    @override
    def screenshot(self) -> MatLike:
        with self.__lock:
            if self.__retry_count >= MAX_RETRY_COUNT:
                raise RuntimeError(f"Maximum retry count ({MAX_RETRY_COUNT}) exceeded")

            if not self.__worker or (self.__worker and not self.__worker.is_alive()):
                self.__start_worker()
        
        start_time = time.time()
        while self.__data is None:
            time.sleep(0.01)
            if time.time() - start_time > WAIT_TIMEOUT:
                logger.warning("Screenshot timeout, cleaning up and restarting worker...")
                with self.__lock:
                    if self.__retry_count < MAX_RETRY_COUNT:
                        self.__start_worker()
                        start_time = time.time()  # 重置超时计时器
                        continue
                    else:
                        raise RuntimeError(f"Maximum retry count ({MAX_RETRY_COUNT}) exceeded")
            
            # 检查 worker 是否还活着
            if self.__worker and not self.__worker.is_alive():
                with self.__lock:
                    if self.__retry_count < MAX_RETRY_COUNT:
                        logger.warning("Worker thread died, restarting...")
                        self.__start_worker()
                    else:
                        raise RuntimeError(f"Maximum retry count ({MAX_RETRY_COUNT}) exceeded")

        logger.verbose(f"adb raw screenshot wait time: {time.time() - start_time:.4f}s")
        data = self.__data
        self.__data = None
        return data


@register_impl('adb_raw', config_model=AdbImplConfig)
def create_adb_raw_device(config: AdbImplConfig):
    """AdbRawImpl 工厂函数"""
    return _create_adb_device_base(config, AdbRawImpl)