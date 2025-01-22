import cv2
import time
import hashlib
import numpy as np

def test_image_hash_time(iterations):
    # 创建一个1920x1080的随机图像
    img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
    
    total_time = 0
    for i in range(iterations):
        start_time = time.time()
        
        # 计算图像的MD5
        md5_hash = hashlib.md5(img.tobytes()).hexdigest()
        
        end_time = time.time()
        total_time += (end_time - start_time)
    
    avg_time = total_time / iterations
    print(f"平均计算时间: {avg_time:.6f} 秒")
    print(f"最后一次计算的MD5值: {md5_hash}")

def test_uuid_time(iterations):
    import uuid
    
    total_time = 0
    for i in range(iterations):
        start_time = time.time()
        
        # 生成 UUID
        uuid_str = str(uuid.uuid4())
        
        end_time = time.time()
        total_time += (end_time - start_time)
    
    avg_time = total_time / iterations
    print(f"平均生成UUID时间: {avg_time:.6f} 秒")
    print(f"最后一次生成的UUID: {uuid_str}")


if __name__ == "__main__":
    test_image_hash_time(1000)
    test_uuid_time(1000)
