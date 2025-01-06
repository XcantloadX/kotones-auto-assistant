import cv2
from kotonebot.client.device.fast_screenshot import AdbFastScreenshots

with AdbFastScreenshots(
    adb_path=r"D:\SDK\Android\platform-tools\adb.exe",
    device_serial="127.0.0.1:16384",
    time_interval=179,
    width=720,
    height=1280,
    bitrate="5M",
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