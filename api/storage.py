import os, json, shutil
from abc import ABC, abstractmethod
class Storage(ABC):
    def save_json(self, key, data): pass
    def get_json(self, key): pass
    def save_file(self, key, file_obj): pass

class LocalStorage(Storage):
    def __init__(self, base="/app/data"):
        os.makedirs(base, exist_ok=True)
        self.base = base
    def save_json(self, key, data):
        tmp = f"{self.base}/{key}.tmp"
        final = f"{self.base}/{key}"
        os.makedirs(os.path.dirname(final), exist_ok=True)
        with open(tmp, 'w') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, final)
    def get_json(self, key):
        with open(f"{self.base}/{key}") as f:
            return json.load(f)
    def save_file(self, key, file_obj):
        path = f"{self.base}/{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as out:
            shutil.copyfileobj(file_obj, out)
        return path

def get_storage():
    return LocalStorage()