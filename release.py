import os
import zipfile

import importlib  
mainmod = importlib.import_module("promexp.version")
version = mainmod.VERSION


def get_files(root):
    for fname in os.listdir(root):
        fpath = os.path.join(root, fname)
        if os.path.isdir(fpath):
            for f in get_files(fpath):
                yield f
        else:
            yield fpath



def zipdir(path, ziph):
    for f in get_files(path):
        n = f.split(os.path.sep, 1)[1]
        print(f, n)
        ziph.write(f, n)

if __name__ == '__main__':
    release_dir = "nebula-prometheus.release"
    if not os.path.exists(release_dir):
        os.mkdir(release_dir)
    zipname = "nebula-prometheus-{}-win64.zip".format(version)
    zipf = zipfile.ZipFile(os.path.join(release_dir, zipname), 'w', zipfile.ZIP_DEFLATED)
    zipdir('nebula-prometheus.dist', zipf)
    zipf.close()