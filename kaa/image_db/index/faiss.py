import ctypes
import importlib.util
import logging
import sys
from pathlib import Path

import numpy as np

from ..descriptors.base import MetricType

logger = logging.getLogger(__name__)


def _preload_faiss_msvc_runtime_for_bootstrap() -> None:
    """kaa-bootstrap / WinPython 专用 workaround。

    WinPython 会在 python.exe 同目录放置较旧的 VCOMP140.DLL / MSVCP140.DLL。
    Windows DLL 搜索优先命中该目录，导致 faiss-cpu 自带的 OpenMP 运行时被劫持，
    随后 HNSW 的 add / add_with_ids 以 0xC0000005 原生崩溃。

    仅在检测到解释器旁存在 VCOMP140 时，预先加载 faiss_cpu.libs 中的配套 DLL。
    普通 venv（Scripts 下无这些 DLL）不受影响。
    """
    if sys.platform != 'win32':
        return

    python_dir = Path(sys.executable).resolve().parent
    if not any((python_dir / name).exists() for name in ('VCOMP140.DLL', 'vcomp140.dll')):
        return

    try:
        spec = importlib.util.find_spec('faiss')
        if spec is None or not spec.origin:
            return
        libs_dir = Path(spec.origin).resolve().parent.parent / 'faiss_cpu.libs'
        if not libs_dir.is_dir():
            return

        loaded: list[str] = []
        for name in ('vcomp140.dll', 'msvcp140.dll'):
            dll_path = libs_dir / name
            if dll_path.is_file():
                ctypes.WinDLL(str(dll_path))
                loaded.append(name)
        if loaded:
            logger.debug(
                'Bootstrap faiss runtime workaround: preloaded %s from %s',
                ', '.join(loaded),
                libs_dir,
            )
    except OSError as e:
        logger.warning('Bootstrap faiss runtime workaround failed: %s', e)


_preload_faiss_msvc_runtime_for_bootstrap()

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class FaissIndex:
    """FAISS 索引。

    支持两种后端：
    - IVFFlat（默认）：聚类 + 近似搜索，需训练，适合大规模数据
    - HNSWFlat：图搜索，无需训练，召回率更高，适合中等规模数据
    支持 L2 和余弦（归一化后内积）距离，不支持 CHI2。
    """

    def __init__(self, dimension: int, metric: MetricType, nlist: int = 100,
                 hnsw: bool = False, hnsw_M: int = 16, hnsw_efSearch: int = 128):
        """
        :param dimension: 向量维度
        :param metric: 距离度量类型（仅支持 L2 和 COSINE）
        :param nlist: IVF 聚类中心数量（仅 IVF 模式使用）
        :param hnsw: 是否使用 HNSW 代替 IVF
        :param hnsw_M: HNSW 每个节点的连接数
        :param hnsw_efSearch: HNSW 查询时搜索深度
        """
        if not FAISS_AVAILABLE:
            raise ImportError('faiss is not installed. Install it with: pip install faiss-cpu')
        self.dimension = dimension
        self.metric = metric
        self._nlist = nlist
        self.hnsw = hnsw
        self._hnsw_M = hnsw_M
        self._hnsw_efSearch = hnsw_efSearch
        self._index = None

    @property
    def is_trained(self):
        return self._index is not None and self._index.is_trained

    @property
    def ntotal(self) -> int:
        return self._index.ntotal if self._index is not None else 0

    def _build_index(self):
        if self.metric == MetricType.L2:
            faiss_metric = faiss.METRIC_L2
        elif self.metric == MetricType.COSINE:
            faiss_metric = faiss.METRIC_INNER_PRODUCT
        else:
            raise ValueError(f'FaissIndex does not support metric: {self.metric}')

        if self.hnsw:
            index = faiss.IndexHNSWFlat(self.dimension, self._hnsw_M, faiss_metric)
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = self._hnsw_efSearch
            index = faiss.IndexIDMap(index)
            return index
        else:
            quantizer = faiss.IndexFlat(self.dimension, faiss_metric)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, self._nlist, faiss_metric)
            index.nprobe = min(self._nlist, 256)
            return index

    def train(self, vectors: np.ndarray):
        """训练索引（HNSW 模式为空操作）。

        :param vectors: 训练向量，shape (N, d)
        """
        self._index = self._build_index()
        if len(vectors) == 0:
            return
        if not self.hnsw:
            self._index.train(vectors)
            logger.debug('FaissIndex (IVF) trained: nlist=%d, nprobe=%d, ntotal=%d',
                         self._index.nlist, self._index.nprobe, len(vectors))  # type: ignore[union-attr]
        else:
            logger.debug('FaissIndex (HNSW) ready: M=%d, efSearch=%d, ntotal=%d',
                         self._hnsw_M, self._hnsw_efSearch, len(vectors))

    def add(self, vectors: np.ndarray, ids: np.ndarray):
        """添加向量到索引。

        :param vectors: 向量，shape (M, d)
        :param ids: 向量对应的整数标签，shape (M,)
        """
        if self._index is None:
            raise RuntimeError('Index not trained. Call train() first.')
        self._index.add_with_ids(vectors, ids)

    def search(self, queries: np.ndarray, k: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """近似最近邻搜索。

        :param queries: 查询向量，shape (Q, d)
        :param k: 返回的 top-k 数量
        :return: (distances, labels)，均为 shape (Q, k)
        """
        if self._index is None or self._index.ntotal == 0:
            return np.full((len(queries), k), np.inf), np.full((len(queries), k), -1, dtype=np.int64)
        distances, labels = self._index.search(queries.astype(np.float32), k)
        return distances.astype(np.float64), labels.astype(np.int64)

    def save(self, path: str):
        """将索引保存到文件（FAISS 二进制格式）。

        :param path: 保存路径
        """
        if self._index is None:
            raise RuntimeError('No index to save.')
        faiss.write_index(self._index, path)

    @classmethod
    def load(cls, path: str, dimension: int = 0, metric: MetricType = MetricType.L2,
             hnsw: bool = False):
        """从文件加载 FAISS 索引。

        :param path: 索引文件路径
        :param dimension: 向量维度（被索引文件中的值覆盖）
        :param metric: 距离度量类型（被索引文件中的值覆盖）
        :param hnsw: 是否为 HNSW 索引
        :return: 加载后的 FaissIndex
        """
        if not FAISS_AVAILABLE:
            raise ImportError('faiss is not installed.')
        raw = faiss.read_index(path)
        inner_dim = raw.d
        if hnsw:
            obj = cls(dimension=inner_dim, metric=metric, hnsw=True)
        else:
            obj = cls(dimension=inner_dim, metric=metric, nlist=100)
        obj._index = raw
        obj.dimension = inner_dim
        return obj
