import wx
import cv2
import numpy as np
import time
from typing import Optional, Tuple, Callable
from threading import Thread, Lock
from cv2.typing import MatLike
from queue import Queue

from kotonebot.client.device import Device

class DeviceMirrorPanel(wx.Panel):
    def __init__(self, parent, device: Device, log_callback=None):
        super().__init__(parent)
        self.device = device
        self.screen_bitmap: Optional[wx.Bitmap] = None
        self.fps = 0
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.is_running = True
        self.lock = Lock()
        self.last_mouse_pos = (0, 0)
        self.is_dragging = False
        self.screenshot_interval = 0  # 截图耗时(ms)
        self.log_callback = log_callback
        self.operation_queue = Queue()
        
        # 设置背景色为黑色
        self.SetBackgroundColour(wx.BLACK)
        
        # 双缓冲，减少闪烁
        self.SetDoubleBuffered(True)
        
        # 绑定事件
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        
        # 启动刷新线程
        self.update_thread = Thread(target=self.update_screen, daemon=True)
        self.update_thread.start()
        
        # 启动操作处理线程
        self.operation_thread = Thread(target=self.process_operations, daemon=True)
        self.operation_thread.start()
        
    def process_operations(self):
        """处理设备操作的线程"""
        while self.is_running:
            try:
                operation = self.operation_queue.get()
                if operation is not None:
                    operation()
                self.operation_queue.task_done()
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"操作执行错误: {e}")
                    
    def execute_device_operation(self, operation: Callable):
        """将设备操作添加到队列"""
        self.operation_queue.put(operation)

    def update_screen(self):
        while self.is_running:
            try:
                # 获取设备截图并计时
                start_time = time.time()
                frame = self.device.screenshot()
                end_time = time.time()
                self.screenshot_interval = int((end_time - start_time) * 1000)
                
                if frame is None:
                    continue
                    
                # 计算FPS
                current_time = time.time()
                self.frame_count += 1
                if current_time - self.last_frame_time >= 1.0:
                    self.fps = self.frame_count
                    self.frame_count = 0
                    self.last_frame_time = current_time
                
                # 转换为wx.Bitmap
                height, width = frame.shape[:2]
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                wximage = wx.Bitmap.FromBuffer(width, height, frame)
                
                with self.lock:
                    self.screen_bitmap = wximage
                
                # 请求重绘
                wx.CallAfter(self.Refresh)
                
                # 控制刷新率
                time.sleep(1/60)
                
            except Exception as e:
                print(f"Error updating screen: {e}")
                time.sleep(1)
    
    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
        
        # 清空背景
        dc.SetBackground(wx.Brush(wx.BLACK))
        dc.Clear()
        
        if not self.screen_bitmap:
            return
            
        # 绘制设备画面
        with self.lock:
            # 计算缩放比例，保持宽高比
            panel_width, panel_height = self.GetSize()
            bitmap_width = self.screen_bitmap.GetWidth()
            bitmap_height = self.screen_bitmap.GetHeight()
            
            scale = min(panel_width/bitmap_width, panel_height/bitmap_height)
            scaled_width = int(bitmap_width * scale)
            scaled_height = int(bitmap_height * scale)
            
            # 居中显示
            x = (panel_width - scaled_width) // 2
            y = (panel_height - scaled_height) // 2
            
            if scale != 1:
                img = self.screen_bitmap.ConvertToImage()
                img = img.Scale(scaled_width, scaled_height, wx.IMAGE_QUALITY_HIGH)
                bitmap = wx.Bitmap(img)
            else:
                bitmap = self.screen_bitmap
                
            dc.DrawBitmap(bitmap, x, y)
        
        # 绘制FPS和截图时间
        dc.SetTextForeground(wx.GREEN)
        dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dc.DrawText(f"FPS: {self.fps}", 10, 10)
        dc.DrawText(f"Interval: {self.screenshot_interval}ms", 10, 30)
    
    def on_size(self, event):
        self.Refresh()
        event.Skip()
        
    def get_device_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """将面板坐标转换为设备坐标"""
        if not self.screen_bitmap:
            return (0, 0)
            
        panel_width, panel_height = self.GetSize()
        bitmap_width = self.screen_bitmap.GetWidth()
        bitmap_height = self.screen_bitmap.GetHeight()
        
        scale = min(panel_width/bitmap_width, panel_height/bitmap_height)
        scaled_width = int(bitmap_width * scale)
        scaled_height = int(bitmap_height * scale)
        
        # 计算显示区域的偏移
        x_offset = (panel_width - scaled_width) // 2
        y_offset = (panel_height - scaled_height) // 2
        
        # 转换坐标
        device_x = int((x - x_offset) / scale)
        device_y = int((y - y_offset) / scale)
        
        # 确保坐标在设备范围内
        device_x = max(0, min(device_x, bitmap_width-1))
        device_y = max(0, min(device_y, bitmap_height-1))
        
        return (device_x, device_y)
    
    def on_left_down(self, event):
        self.last_mouse_pos = event.GetPosition()
        self.is_dragging = True
        event.Skip()
        
    def on_left_up(self, event):
        if not self.is_dragging:
            return
            
        self.is_dragging = False
        pos = event.GetPosition()
        
        # 如果鼠标位置没有明显变化，执行点击
        if abs(pos[0] - self.last_mouse_pos[0]) < 5 and abs(pos[1] - self.last_mouse_pos[1]) < 5:
            device_x, device_y = self.get_device_coordinates(*pos)
            self.execute_device_operation(lambda: self.device.click(device_x, device_y))
            if self.log_callback:
                self.log_callback(f"点击: ({device_x}, {device_y})")
        else:
            # 执行滑动
            start_x, start_y = self.get_device_coordinates(*self.last_mouse_pos)
            end_x, end_y = self.get_device_coordinates(*pos)
            self.execute_device_operation(lambda: self.device.swipe(start_x, start_y, end_x, end_y))
            if self.log_callback:
                self.log_callback(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            
        event.Skip()
        
    def on_motion(self, event):
        if not self.is_dragging:
            event.Skip()
            return
            
        event.Skip()

class DeviceMirrorFrame(wx.Frame):
    def __init__(self, device: Device):
        super().__init__(None, title="设备镜像", size=(800, 600))
        
        # 创建分割窗口
        self.splitter = wx.SplitterWindow(self)
        
        # 创建左侧面板（包含控制区域和日志区域）
        self.left_panel = wx.Panel(self.splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 控制区域
        self.control_panel = wx.Panel(self.left_panel)
        self.init_control_panel()
        left_sizer.Add(self.control_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # 日志区域
        self.log_text = wx.TextCtrl(self.left_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.log_text.SetBackgroundColour(wx.BLACK)
        self.log_text.SetForegroundColour(wx.GREEN)
        self.log_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        left_sizer.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        self.left_panel.SetSizer(left_sizer)
        
        # 创建设备画面
        self.device_panel = DeviceMirrorPanel(self.splitter, device, self.log)
        
        # 设置分割
        self.splitter.SplitVertically(self.left_panel, self.device_panel)
        self.splitter.SetMinimumPaneSize(200)
        
        # 保存设备引用
        self.device = device
        
    def log(self, message: str):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        wx.CallAfter(self.log_text.AppendText, f"[{timestamp}] {message}\n")
        
    def init_control_panel(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 添加控制按钮
        btn_get_resolution = wx.Button(self.control_panel, label="获取分辨率")
        btn_get_resolution.Bind(wx.EVT_BUTTON, self.on_get_resolution)
        vbox.Add(btn_get_resolution, 0, wx.EXPAND | wx.ALL, 5)
        
        btn_get_orientation = wx.Button(self.control_panel, label="获取设备方向")
        btn_get_orientation.Bind(wx.EVT_BUTTON, self.on_get_orientation)
        vbox.Add(btn_get_orientation, 0, wx.EXPAND | wx.ALL, 5)
        
        # 启动APP区域
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.package_input = wx.TextCtrl(self.control_panel)
        hbox.Add(self.package_input, 1, wx.EXPAND | wx.RIGHT, 5)
        btn_launch_app = wx.Button(self.control_panel, label="启动APP")
        btn_launch_app.Bind(wx.EVT_BUTTON, self.on_launch_app)
        hbox.Add(btn_launch_app, 0)
        vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 5)
        
        btn_get_current_app = wx.Button(self.control_panel, label="获取前台APP")
        btn_get_current_app.Bind(wx.EVT_BUTTON, self.on_get_current_app)
        vbox.Add(btn_get_current_app, 0, wx.EXPAND | wx.ALL, 5)
        
        self.control_panel.SetSizer(vbox)
        
    def on_get_resolution(self, event):
        """获取分辨率"""
        try:
            width, height = self.device.screen_size
            self.log(f"设备分辨率: {width}x{height}")
        except Exception as e:
            self.log(f"获取分辨率失败: {e}")
            
    def on_get_orientation(self, event):
        """获取设备方向"""
        try:
            orientation = self.device.detect_orientation()
            orientation_text = "横屏" if orientation == "landscape" else "竖屏"
            self.log(f"设备方向: {orientation_text}")
        except Exception as e:
            self.log(f"获取设备方向失败: {e}")
            
    def on_launch_app(self, event):
        """启动APP"""
        package_name = self.package_input.GetValue().strip()
        if not package_name:
            self.log("请输入包名")
            return
        try:
            # 使用新的 API 通过 commands 属性访问平台特定方法
            if hasattr(self.device, 'commands') and hasattr(self.device.commands, 'launch_app'):
                self.device.commands.launch_app(package_name)
                self.log(f"启动APP: {package_name}")
            else:
                self.log("当前设备不支持启动APP功能")
        except Exception as e:
            self.log(f"启动APP失败: {e}")
            
    def on_get_current_app(self, event):
        """获取前台APP"""
        try:
            # 使用新的 API 通过 commands 属性访问平台特定方法
            if hasattr(self.device, 'commands') and hasattr(self.device.commands, 'current_package'):
                package = self.device.commands.current_package()
                if package:
                    self.log(f"前台APP: {package}")
                else:
                    self.log("未获取到前台APP")
            else:
                self.log("当前设备不支持获取前台APP功能")
        except Exception as e:
            self.log(f"获取前台APP失败: {e}")
            
    def on_quit(self, event):
        self.device_panel.is_running = False
        self.Close()

def show_device_mirror(device: Device):
    """显示设备镜像窗口"""
    app = wx.App()
    frame = DeviceMirrorFrame(device)
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    # 测试代码
    from kotonebot.client.device import AndroidDevice
    from kotonebot.client.implements.adb import AdbImpl
    from kotonebot.client.implements.uiautomator2 import UiAutomator2Impl
    from adbutils import adb

    print("server version:", adb.server_version())
    adb.connect("127.0.0.1:5555")
    print("devices:", adb.device_list())
    d = adb.device_list()[-1]

    # 使用新的 API
    dd = AndroidDevice(d)
    adb_imp = AdbImpl(d)  # 直接传入 adb 连接
    dd._touch = adb_imp
    dd._screenshot = UiAutomator2Impl(dd)  # UiAutomator2Impl 可能还需要 device 对象
    dd.commands = adb_imp  # 设置 Android 特定命令

    show_device_mirror(dd)
