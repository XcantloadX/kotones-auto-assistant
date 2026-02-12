import cv2
from cv2.typing import MatLike

class HogDescriptor:
    def __init__(self, size=(64, 128)):
        self.size = size
        self.hog = cv2.HOGDescriptor(_winSize=size, _blockSize=(16,16), _blockStride=(8,8), _cellSize=(8,8), _nbins=9)

    def __call__(self, image: MatLike):
        img_resized = cv2.resize(image, self.size)
        hist = self.hog.compute(img_resized)
        return hist.flatten() # type: ignore