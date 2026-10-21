#!/usr/bin/env python3
"""Build reviewed-v2 source data from frozen human/source-pixel reviews only."""
import argparse, collections, copy, datetime, hashlib, json, pathlib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent
V1_SHA='4fc65ec9056d346d805044150fc4631a7f48ba277788ce67b80e16303a5864e2'
EXPECTED_BAD={'calibration':{263644,277197,406570,495054},'heldout':{98497,355677,371677,435880}}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return (json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
def once(path,obj):
 raw=encoded(obj)
 if path.exists():assert path.read_bytes()==raw,f'Refusing to replace {path}'
 else:path.write_bytes(raw)
 path.chmod(0o444);return sha(raw)
def read(path):return json.loads(path.read_bytes())
def review(path,expected,allow_subset=False):
 raw=path.read_bytes();r=json.loads(raw);assert r['modelBlindBeforeInference'] is True
 rows=r.get('images',r.get('reviews',r.get('records')));assert isinstance(rows,list)
 bound={}
 for row in rows:
  image_id=row.get('sourceImageId',row.get('imageId'));assert image_id in expected
  image=expected[image_id];assert row['id']==image['id'] and row['sha256']==image['sha256'] and row['split']==image['split']
  decision=row.get('decision',row.get('label'));assert decision in ('clear_no_human','contains_human','contains_depicted_human','ambiguous')
  assert row['noPerson']==(decision=='clear_no_human');assert image_id not in bound
  bound[image_id]={**row,'decision':decision}
 assert allow_subset or set(bound)==set(expected)
 return r,bound,sha(raw)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--original-review',type=pathlib.Path,required=True);parser.add_argument('--reserve-review',type=pathlib.Path,action='append',required=True);parser.add_argument('--candidate-pool',type=pathlib.Path,default=ROOT/'replacement-candidates.freeze.json');parser.add_argument('--candidate-manifest',type=pathlib.Path,default=ROOT/'replacement-candidates.manifest.json');args=parser.parse_args()
 oldraw=(ROOT/'manifest.json').read_bytes();assert sha(oldraw)==V1_SHA;old=json.loads(oldraw);oldgt=read(ROOT/'humanGT.json');oldselection=read(ROOT/'selection.freeze.json');pool=read(args.candidate_pool);candidates=read(args.candidate_manifest)
 oldbg={i['sourceImageId']:i for i in old['images'] if i['stratum']=='no_person_annotation'};resbg={i['sourceImageId']:i for i in candidates['images']}
 original_report,original,original_sha=review(args.original_review,oldbg)
 reserve_reviews=[review(path,resbg,allow_subset=True) for path in args.reserve_review]
 assert set().union(*(set(rows) for _,rows,_ in reserve_reviews))==set(resbg)
 assert all(len({report['reviewer'] for report,rows,_ in reserve_reviews if i in rows})>=2 for i in resbg)
 for split in ('calibration','heldout'):
  excluded={image_id for image_id,row in original.items() if row['split']==split and row['decision']!='clear_no_human'};assert excluded==EXPECTED_BAD[split]
 oldrank={e['imageId']:e['rankSha256'] for e in oldselection['images']};reserve_rank={e['imageId']:e['globalCandidateRankZeroBased'] for e in pool['images']}
 replacements=[];chosen=[]
 for split in ('calibration','heldout'):
  excluded=sorted(EXPECTED_BAD[split],key=lambda i:oldrank[i])
  clear=sorted([i for i in resbg if resbg[i]['split']==split and all(rows[i]['decision']=='clear_no_human' for _,rows,_ in reserve_reviews if i in rows)],key=lambda i:reserve_rank[i])
  assert len(clear)>=len(excluded),f'Insufficient independently clear {split} reserves: {len(clear)}'
  for old_id,new_id in zip(excluded,clear):
   chosen.append(new_id);replacements.append({'split':split,'excludedImageId':old_id,'excludedId':oldbg[old_id]['id'],'excludedDecision':original[old_id]['decision'],'excludedReason':original[old_id].get('reason',''),'replacementImageId':new_id,'replacementId':resbg[new_id]['id'],'replacementGlobalCandidateRankZeroBased':reserve_rank[new_id],'originalReviewSha256':original_sha,'reserveReviewSha256s':[s for _,rows,s in reserve_reviews if new_id in rows]})
 excluded_all=set().union(*EXPECTED_BAD.values());final_images=[i for i in old['images'] if i['sourceImageId'] not in excluded_all]+[resbg[i] for i in chosen];final_images.sort(key=lambda i:i['id']);assert len(final_images)==128
 assert [i for i in old['images'] if i['stratum']!='no_person_annotation']==[i for i in final_images if i['stratum']!='no_person_annotation']
 for key in ('sourceImageId','sourceAnnotationId','sha256'):
  splitsets=[{i[key] for i in final_images if i['split']==split and i[key] is not None} for split in ('calibration','heldout')];assert splitsets[0].isdisjoint(splitsets[1]),key
 assert collections.Counter(i['split']+':'+i['stratum'] for i in final_images)=={'calibration:primary_visible':47,'heldout:primary_visible':32,'calibration:occluded_v1':6,'heldout:occluded_v1':3,'calibration:no_person_annotation':20,'heldout:no_person_annotation':20}
 source_reviews=[{'path':str(args.original_review.relative_to(ROOT)),'sha256':original_sha,'reviewer':original_report['reviewer']}]+[{'path':str(path.relative_to(ROOT)),'sha256':s,'reviewer':report['reviewer']} for path,(report,rows,s) in zip(args.reserve_review,reserve_reviews)]
 selection_path=ROOT/'selection.reviewed.freeze.json';frozen_at=read(selection_path)['frozenAtUtc'] if selection_path.exists() else datetime.datetime.now(datetime.timezone.utc).isoformat()
 final_review_rows=[]
 for image in final_images:
  if image['stratum']!='no_person_annotation':continue
  image_id=image['sourceImageId']
  if image_id in oldbg:decisions=[original[image_id]];review_shas=[original_sha];reviewers=[original_report['reviewer']]
  else:decisions=[rows[image_id] for _,rows,_ in reserve_reviews if image_id in rows];review_shas=[s for _,rows,s in reserve_reviews if image_id in rows];reviewers=[report['reviewer'] for report,rows,_ in reserve_reviews if image_id in rows]
  assert all(d['decision']=='clear_no_human' for d in decisions)
  final_review_rows.append({'id':image['id'],'sourceImageId':image_id,'sha256':image['sha256'],'split':image['split'],'decision':'clear_no_human','noPerson':True,'reason':' / '.join(d.get('reason','') for d in decisions),'reviewer':reviewers,'sourceReviewSha256s':review_shas})
 envelope={'schemaVersion':1,'frozenAtUtc':frozen_at,'reviewer':[x['reviewer'] for x in source_reviews],'modelBlindBeforeInference':True,'reviewMethod':'Independent source-pixel review of every original. Original background decisions transcribed from the original reviewer; reserve replacement acceptance requires all supplied independent source-pixel reviews to classify clear_no_human. Human depictions and ambiguities excluded. No pose model or prediction inspection.','originalManifestSha256':V1_SHA,'candidatePoolSha256':sha(args.candidate_pool.read_bytes()),'candidateManifestSha256':sha(args.candidate_manifest.read_bytes()),'sourceReviewFiles':source_reviews,'images':final_review_rows,'reviews':final_review_rows}
 envelope_sha=once(ROOT/'background-reviewed.freeze.json',envelope)
 by_oldselection={i['imageId']:i for i in oldselection['images']};by_reserve={i['imageId']:i for i in pool['images']};selection_rows=[]
 for image in final_images:
  image_id=image['sourceImageId']
  if image_id in by_oldselection:selection_rows.append(copy.deepcopy(by_oldselection[image_id]))
  else:
   p=by_reserve[image_id];selection_rows.append({'id':image['id'],'imageId':image_id,'annotationId':None,'split':image['split'],'stratum':image['stratum'],'poseStratum':'unknown','rankSha256':p['rankSha256']})
 selection={'schemaVersion':1,'frozenAtUtc':frozen_at,'selectionBasis':'Human/source annotation criteria and independent source-pixel background review only, before inference. All88 original keypoint images/labels/splits unchanged.','originalManifestSha256':V1_SHA,'originalSelectionFreezeSha256':sha((ROOT/'selection.freeze.json').read_bytes()),'sourceAnnotationsSha256':oldselection['sourceAnnotationsSha256'],'backgroundReviewSha256':envelope_sha,'sourceReviewFiles':source_reviews,'reservePoolSha256':sha(args.candidate_pool.read_bytes()),'policy':oldselection['policy'],'replacementRule':pool['replacementRule'],'replacements':replacements,'images':selection_rows}
 selection_sha=once(selection_path,selection)
 by_gt={i['id']:i for i in oldgt['images']};gt_rows=[]
 for image in final_images:
  if image['id'] in by_gt:gt_rows.append(copy.deepcopy(by_gt[image['id']]))
  else:gt_rows.append({'id':image['id'],'split':image['split'],'stratum':'no_person_annotation','poseStratum':'unknown','imageId':image['sourceImageId'],'annotationId':None,'width':image['width'],'height':image['height'],'bbox':None,'bboxImageAreaFraction':None,'shoulderSpanPixels':None,'kind':'no-person-annotation','numKeypoints':0,'keypoints':[],'joints':{}})
 assert [i for i in oldgt['images'] if i['kind']=='human-keypoints']==[i for i in gt_rows if i['kind']=='human-keypoints']
 gt={**oldgt,'dataset':'COCO2017 val human keypoints with independently reviewed background pilot v2','selectionFreezeSha256':selection_sha,'backgroundReviewSha256':envelope_sha,'backgroundReviewFile':'background-reviewed.freeze.json','images':gt_rows}
 gt_sha=once(ROOT/'humanGT-reviewed.json',gt)
 manifest={**old,'dataset':'COCO2017 val human-keypoint calibration pilot with reviewed backgrounds v2','selectionFreezeSha256':selection_sha,'humanGTSha256':gt_sha,'backgroundReviewSha256':envelope_sha,'backgroundReviewFile':'background-reviewed.freeze.json','originalManifestSha256':V1_SHA,'images':final_images}
 manifest_sha=once(ROOT/'manifest-reviewed.json',manifest)
 positive_old=[i for i in old['images'] if i['stratum']!='no_person_annotation'];positive_new=[i for i in final_images if i['stratum']!='no_person_annotation'];assert positive_old==positive_new and len(positive_new)==88
 assert [i for i in oldgt['images'] if i['kind']=='human-keypoints']==[i for i in gt_rows if i['kind']=='human-keypoints']
 for key in ('sourceImageId','sourceAnnotationId','sha256'):
  sets=[{i[key] for i in final_images if i['split']==split and i[key] is not None} for split in ('calibration','heldout')];assert sets[0].isdisjoint(sets[1]),key
 counts=dict(collections.Counter(i['split']+':'+i['stratum'] for i in final_images));assert counts=={'calibration:primary_visible':47,'heldout:primary_visible':32,'calibration:occluded_v1':6,'heldout:occluded_v1':3,'calibration:no_person_annotation':20,'heldout:no_person_annotation':20}
 for image in final_images:
  p=ROOT/image['asset'];raw=p.read_bytes();assert len(raw)==image['bytes'] and sha(raw)==image['sha256']
  with Image.open(p) as decoded:assert decoded.size==(image['width'],image['height']);decoded.verify()
 source=read(ROOT/'source'/'person_keypoints_val2017.json');sourceimages={i['id']:i for i in source['images']};oldsubset=read(ROOT/'source'/'selected_coco_original.json');subset={**oldsubset,'images':[sourceimages[i['sourceImageId']] for i in final_images]};subset_sha=once(ROOT/'source'/'selected_coco_reviewed_original.json',subset)
 report={'schemaVersion':1,'frozenAtUtc':frozen_at,'manifestReviewedSha256':manifest_sha,'humanGTReviewedSha256':gt_sha,'selectionReviewedFreezeSha256':selection_sha,'backgroundReviewSha256':envelope_sha,'sourceReviewFiles':source_reviews,'originalV1ManifestUnchanged':sha((ROOT/'manifest.json').read_bytes())==V1_SHA,'all88PositiveManifestAndGTRowsIdentical':True,'sourceImagePersonInstanceAndExactJpegShaSplitDisjoint':True,'jpegDimensionsHashesIntegrityVerified':128,'reviewedClearBackgrounds':40,'backgroundCounts':{'calibration':20,'heldout':20},'counts':counts,'selectedSourceOriginalSha256':subset_sha,'replacements':replacements,'noPoseModelOrPredictionsUsed':True}
 once(ROOT/'verification-reviewed.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
