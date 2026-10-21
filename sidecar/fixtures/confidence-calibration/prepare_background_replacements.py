#!/usr/bin/env python3
"""Freeze source-label-only reserves and optionally retrieve originals. No pose model."""
import argparse, concurrent.futures, datetime, hashlib, io, json, pathlib
from PIL import Image, ImageDraw, ImageOps
from fetch_selected import fetch
ROOT = pathlib.Path(__file__).resolve().parent
V1_SHA = '4fc65ec9056d346d805044150fc4631a7f48ba277788ce67b80e16303a5864e2'
SOURCE_SHA = '788e2dae83c86bd547be7fab269d6399df5671063d29a61360cdb2cc370d2b14'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(obj): return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode()
def once(path,obj):
 raw=encoded(obj)
 if path.exists(): assert path.read_bytes()==raw, f'Refusing to replace {path}'
 else: path.write_bytes(raw)
 path.chmod(0o444)
 return sha(raw)
def download(entry):
 record_path=ROOT/'source'/'replacement-fetch-records'/f"{entry['id']}.json"
 if record_path.exists():
  record=json.loads(record_path.read_bytes()); assert sha((ROOT/record['manifestImage']['asset']).read_bytes())==record['manifestImage']['sha256']; return record
 image=entry['sourceImage']; url='https://s3.amazonaws.com/images.cocodataset.org/val2017/'+image['file_name']
 raw,final_url,headers=fetch(url)
 with Image.open(io.BytesIO(raw)) as decoded:
  assert decoded.format=='JPEG' and decoded.size==(image['width'],image['height']); decoded.verify()
 digest=sha(raw); asset='calibration/'+digest+'.jpg'; path=ROOT/asset
 if path.exists(): assert path.read_bytes()==raw
 else: path.write_bytes(raw)
 path.chmod(0o444)
 item={'id':entry['id'],'asset':asset,'sha256':digest,'bytes':len(raw),'width':image['width'],'height':image['height'],'split':entry['split'],'kind':'no-person-annotation','stratum':'no_person_annotation','poseStratum':'unknown','sourceImageId':image['id'],'sourceAnnotationId':None,'licenseId':image['license'],'cocoUrl':image['coco_url'],'flickrUrl':image['flickr_url']}
 record={'manifestImage':item,'sourceImage':image,'download':{'requestedUrl':url,'resolvedUrl':final_url,'retrievedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'etag':headers.get('ETag'),'lastModified':headers.get('Last-Modified')},'attributionNote':'No additional Flickr calls; historical COCO license/source metadata retained for local evaluation.'}
 once(record_path,record); print('downloaded',entry['id'],flush=True); return record

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--download',action='store_true');parser.add_argument('--batch-index',type=int,choices=(1,2),default=1);args=parser.parse_args()
 old_raw=(ROOT/'manifest.json').read_bytes(); assert sha(old_raw)==V1_SHA; old=json.loads(old_raw)
 source_raw=(ROOT/'source'/'person_keypoints_val2017.json').read_bytes();assert sha(source_raw)==SOURCE_SHA;source=json.loads(source_raw)
 policy=json.loads((ROOT/'selection-policy.json').read_bytes());annotated={a['image_id'] for a in source['annotations']}; candidates=[]
 for image in source['images']:
  if image['license'] not in policy['allowedLicenseIds'] or image['id'] in annotated:continue
  rank=sha(f"{policy['seed']}:no-person-annotation:{image['id']}".encode())
  candidates.append({'id':f"coco2017_{image['id']:012d}_no_person_annotation",'imageId':image['id'],'rankSha256':rank,'sourceImage':image})
 candidates.sort(key=lambda e:e['rankSha256']);assert len(candidates)==583
 assert {e['imageId'] for e in candidates[:40]}=={i['sourceImageId'] for i in old['images'] if i['stratum']=='no_person_annotation'}
 start=40+12*(args.batch_index-1);fresh=candidates[start:start+12];reserve=fresh
 for index,entry in enumerate(fresh):entry.update({'globalCandidateRankZeroBased':start+index,'split':'calibration' if index<6 else 'heldout'})
 suffix='' if args.batch_index==1 else '-extended'
 if args.batch_index==2:reserve=json.loads((ROOT/'replacement-candidates.freeze.json').read_bytes())['images']+fresh
 p=ROOT/f'replacement-candidates{suffix}.freeze.json';frozen_at=json.loads(p.read_bytes())['frozenAtUtc'] if p.exists() else datetime.datetime.now(datetime.timezone.utc).isoformat()
 pool={'schemaVersion':1,'frozenAtUtc':frozen_at,'originalManifestSha256':V1_SHA,'sourceAnnotationsSha256':SOURCE_SHA,'seed':policy['seed'],'recipe':'Same original 583 eligible zero-person-annotation images and same hash rank. Reserve global zero-based ranks40..51; ranks40..45 calibration and46..51 heldout. Source/license/annotation-only selection before pixel review; no pose model, predictions or scores.','replacementRule':'Within each split retain original clear-no-human images. Match excluded originals in original rank order to first independently clear-no-human reserve images in reserve rank order. Freeze review hashes and complete mapping before inference.','images':reserve}
 if args.batch_index==2:
  pool['recipe']='Original12 reserves remain unchanged. Supplemental global zero-based ranks52..63 fixed before supplemental pixel review: ranks52..57 calibration,58..63 heldout. Same original583 eligible source/license/annotation-only pool, same hashseed, no models or scores.'
  pool['priorCandidatePoolSha256']=sha((ROOT/'replacement-candidates.freeze.json').read_bytes())
  pool['supplementalFrozenBeforePixelReview']=True
 pool_sha=once(p,pool);print(json.dumps({'candidatePoolSha256':pool_sha,'frozenAtUtc':frozen_at,'candidates':[{'imageId':e['imageId'],'split':e['split'],'rank':e['globalCandidateRankZeroBased']} for e in reserve]},indent=2),flush=True)
 if not args.download:return
 (ROOT/'source'/'replacement-fetch-records').mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:records=list(executor.map(download,reserve))
 records.sort(key=lambda r:r['manifestImage']['id']);manifest={'schemaVersion':1,'dataset':'COCO2017 human-review replacement candidates','candidatePoolSha256':pool_sha,'images':[r['manifestImage'] for r in records]}
 old_shas={i['sha256'] for i in old['images']};assert not old_shas.intersection(i['sha256'] for i in manifest['images'])
 assert len({i['sha256'] for i in manifest['images']})==len(reserve)
 manifest_sha=once(ROOT/f'replacement-candidates{suffix}.manifest.json',manifest)
 for split in ('calibration','heldout'):
  fresh_ids={e['id'] for e in fresh};images=[i for i in manifest['images'] if i['split']==split and i['id'] in fresh_ids];sheet=Image.new('RGB',(1200,660),'white');draw=ImageDraw.Draw(sheet)
  for index,image in enumerate(images):
   with Image.open(ROOT/image['asset']) as original:tile=ImageOps.contain(original.convert('RGB'),(392,290))
   x,y=(index%3)*400,(index//3)*330;sheet.paste(tile,(x+(400-tile.width)//2,y+(290-tile.height)//2));draw.text((x+5,y+295),f"{image['sourceImageId']:012d} / {split}",fill='black')
  sheet.save(ROOT/f'replacement-contactsheet{suffix}-{split}.png')
 print(json.dumps({'replacementManifestSha256':manifest_sha,'images':len(records),'imageBytes':sum(r['manifestImage']['bytes'] for r in records)},indent=2),flush=True)
if __name__=='__main__':main()
