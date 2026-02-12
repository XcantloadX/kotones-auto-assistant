from typing import TYPE_CHECKING, Protocol
if TYPE_CHECKING:
    from cv2.typing import MatLike
    from numpy import ndarray


class BaseDescriptor(Protocol):
    def __call__(self, image: 'MatLike') -> 'ndarray':
        ...