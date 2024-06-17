# pip install Flask llmsherpa spire.pdf spire.doc textract

# sudo apt-get install antiword abiword unrtf poppler-utils libjpeg-dev \ pstotext

import importlib.util

def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
