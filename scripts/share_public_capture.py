"""Return captured PUBLIC MET/OSM data through GitHub blobs when local sockets fail.

No provider credentials, marine data, config directories, commits or refs are sent.
Only public capture files from this case may be included. The runner token is
used only for its own repository's blob API and is never printed or persisted.
"""
import argparse,base64,io,json,os,tarfile
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,urlopen


def bundle(directory):
    directory=Path(directory);paths=[]
    for name in ('request.json','status.json','met','land'):
        p=directory/name
        paths.extend([p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file()))
    if any(p.is_symlink() or p.suffix=='.log' for p in paths):raise ValueError('Unexpected public capture resource')
    result=io.BytesIO()
    with tarfile.open(fileobj=result,mode='w:gz') as archive:
        for p in paths:archive.add(p,arcname=p.relative_to(directory).as_posix(),recursive=False)
    return result.getvalue()


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();data=bundle(a.directory)
    if os.environ.get('GITHUB_REPOSITORY')!='axiertech/seaparser':raise ValueError('SeaParser repository required')
    encoded=base64.b64encode(data).decode();pieces=[]
    for i in range(0,len(encoded),400000):
        request=Request('https://api.github.com/repos/axiertech/seaparser/git/blobs',data=json.dumps({'content':encoded[i:i+400000],'encoding':'utf-8'}).encode(),headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'})
        with urlopen(request,timeout=60) as response:sha=json.load(response)['sha']
        pieces.append(sha)
    print('PUBLIC_CAPTURE_BLOBS '+json.dumps(dict(archive_sha256=sha256(data).hexdigest(),archive_bytes=len(data),pieces=pieces)),flush=True)


if __name__=='__main__':main()
