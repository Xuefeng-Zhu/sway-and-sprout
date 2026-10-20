"""Build preselected public held-pose and contiguous mirror comparisons; no inference."""
from pathlib import Path
import hashlib,json,subprocess,sys,os
ROOT=Path(__file__).resolve().parent.parent
MEDIA=ROOT/'sidecar/fixtures/frontal'
OUT=MEDIA/'bounded-frontal'
OUT.mkdir(exist_ok=True)
annotation=Path(sys.argv[1]).resolve(strict=True)
annotation_hash=hashlib.sha256(annotation.read_bytes()).hexdigest()
annotations=json.loads(annotation.read_text())
for item in annotations['poses']:
 image_path=MEDIA/item['file']
 assert hashlib.sha256(image_path.read_bytes()).hexdigest()==item['sha256'],item['file']
right=MEDIA/'public-frontal-candidate-frame035.png'
neutral=MEDIA/'chosen-neutral-source-frame225.png'
source=Path(os.environ.get('TM_PUBLIC_SOURCE',str(ROOT/'sidecar/fixtures/.cache/pexels-artem-podrez-6003772.mp4'))).resolve(strict=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='d891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51'
# RGB decode only, never a media device.
def image_bytes(path):
 return subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
n=image_bytes(neutral); r=image_bytes(right)
assert len(n)==len(r)==640*360*3
# Exact pixel reflection, x'=639-x. No model or geometric retuning.
def mirror(pixels):
 return b''.join(b''.join(pixels[y*1920+x*3:y*1920+x*3+3] for x in range(639,-1,-1)) for y in range(360))
l=mirror(r)
assert image_bytes(MEDIA/'frontal-left-reflected-frame035.png')==l
assert image_bytes(MEDIA/'frontal-neutral-reflected-frame225.png')==mirror(n)
image_data={'N':n,'L':l,'R':r}
schedule=[('N',20)]+[('L',10),('N',12),('R',10),('N',12)]*3
video=OUT/'frontal-held-source035.mp4'
cmd=['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','640x360','-r','10','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2','-frames:v','152','-movflags','+faststart',str(video)]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
segments=[];index=0
for label,count in schedule:
 segments.append({'label':label,'startFrame':index,'endFrameExclusive':index+count,'sourceFrame':225 if label=='N' else 35,'reflected':label=='L'})
 for _ in range(count):proc.stdin.write(image_data[label])
 index+=count
proc.stdin.close();errors=proc.stderr.read();status=proc.wait(timeout=60)
if status:raise RuntimeError(errors.decode())
manifest={'fixture':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'fps':10,'frames':152,'durationSeconds':15.2,'naturalContinuousMovement':False,'kind':'hard-cut repeated public frames; frontal source-right and derived reflected-left','sourceFrameRight':35,'sourceFrameNeutral':225,'leftIsReflection':True,'expectedGestures':['left-raise','right-raise']*3,'annotationFile':str(annotation),'annotationSha256':annotation_hash,'annotationFrozenBeforeInference':True,'segments':segments,'provenance':{'creator':'Artem Podrez','page':'https://www.pexels.com/video/a-woman-dancing-at-home-6003772/','license':'https://www.pexels.com/license/'},'limits':['One actor and one actual raised anatomical side, with reflected opposite side.','No natural movement in held fixture.','Frame35 choice frozen before this fixture inference; older source165/170 results known.']}
video.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Preserve all319 frames in order, original30fps; only resize/reencode/reflect.
for name,filter_value in [('continuous-source-original640.mp4','scale=640:360'),('continuous-source-mirrored640.mp4','scale=640:360,hflip')]:
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(source),'-vf',filter_value,'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2','-fps_mode','passthrough','-movflags','+faststart',str(OUT/name)],check=True,timeout=60)
print(json.dumps({'output':str(OUT),'annotationSha256':annotation_hash,'held':manifest['sha256'],'normalSpeedOriginalAndMirror':'319 frames at30fps; no segment cuts or time changes'}))
