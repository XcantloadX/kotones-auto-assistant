from typing import Dict

from pydantic import BaseModel

class FileEntry(BaseModel):
    md5: str
    size: int

class Manifest(BaseModel):
    version: str
    files: Dict[str, FileEntry]

    def get_category_files(self, category: str) -> Dict[str, FileEntry]:
        """返回指定分类的文件列表，key 为文件名（不含前缀）"""
        prefix = category + '/'
        return {
            k[len(prefix):]: v
            for k, v in self.files.items()
            if k.startswith(prefix)
        }

def parse(data: bytes | str) -> Manifest:
    return Manifest.model_validate_json(data)
