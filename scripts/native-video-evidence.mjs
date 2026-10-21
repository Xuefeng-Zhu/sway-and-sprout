// Pure scalar evidence checks; no ADB, browser, SDK, camera or inference imports.
const identityFields='kind source engine engineVersion modelSha256 modelId inputSize verified configAsset api abi threads scalarFrameDiagnostics capture personCount inputTransform decodedFrames acceptedFrames discardedEpochFrames nextFrameIndex fullFileProcessed resourcesClosed cleanupSucceeded nativeRecognizedEvents acknowledgedEvents';
function filteredScalarRows(text,configAsset,kinds,fields){
 const rows=[],keys=new Set(fields.split(' '));
 for(const line of text.split('\n')){
  const start=line.indexOf('{');if(start<0)continue;
  let item;try{item=JSON.parse(line.slice(start));}catch{continue;}
  if(!kinds.includes(item?.kind)||item.configAsset!==configAsset)continue;
  const scalar={};
  for(const [key,value] of Object.entries(item)){
   if(!keys.has(key))continue;
   if(typeof value==='boolean'||(typeof value==='number'&&Number.isFinite(value))||
      (typeof value==='string'&&value.length<=512))scalar[key]=value;
  }
  rows.push(scalar);
 }
 return rows;
}
export function nativeScalarRows(text, configAsset){
 return filteredScalarRows(text,configAsset,['pose-frame','event'],identityFields+
  ' frameIndex fileMs confidence lsX lsY lsScore rsX rsY rsScore lwX lwY lwScore rwX rwY rwScore status armed seq gesture eventFileMs');
}
export function nativeSummaryRows(text,configAsset){
 return filteredScalarRows(text,configAsset,
  ['finished','stopped','paused','suspended','client-replaced','round-replaced','lease-expired'],identityFields+
  ' expectationKnown expectedSequenceEvaluated exactExpectedSequence declaredVideoFrames declaredFps decodeMeanMs preprocessMeanMs inferenceMeanMs inferenceP95Ms frameMeanMs frameP95Ms referenceParityChecks referenceByteDifferences referenceMaxByteDelta referenceOutputMaxDelta referenceMeanMs modelInferencesPerFrame defaultCropFrames processPssKiB');
}

export function nativeFrameCoverage(rows, expected){
 const frames=rows.filter(row=>row.kind==='pose-frame'),seen=new Set(),duplicates=[],invalid=[],badTimes=[];
 for(const row of frames){
  const i=row.frameIndex;
  if(!Number.isInteger(i)||i<0||i>=expected.frames){invalid.push(i??null);continue;}
  if(seen.has(i))duplicates.push(i);seen.add(i);
  if(!Number.isFinite(row.fileMs)||Math.abs(row.fileMs-i*1000/expected.fps)>1e-6)badTimes.push(i);
 }
 const missing=[];for(let i=0;i<expected.frames;i++)if(!seen.has(i))missing.push(i);
 return {expectedFrames:expected.frames,loggedFrames:frames.length,uniqueFrames:seen.size,
  missingIndices:missing,duplicateIndices:duplicates,invalidIndices:invalid,badTimestampIndices:badTimes,
  complete:frames.length===expected.frames&&!missing.length&&!duplicates.length&&!invalid.length&&!badTimes.length};
}

export function nativeUiScoreVerified(ui){
 return ui?.gardenPresent===true&&typeof ui.countText==='string'&&/^[0-6]$/.test(ui.countText)&&
  Number.isInteger(ui.count)&&ui.count===Number(ui.countText)&&ui.countLabel===ui.countText&&
  ui.raySlots===6&&ui.collectedRays===ui.count&&ui.source==='video'&&
  ui.badgeText==='VIDEO REPLAY · NO CAMERA';
}

export function nativeDiagnosticRoundVerified(round){
 return round?.roundSecondsText==='120'&&round.diagnosticReplayText==='true'&&round.timerText==='120s';
}

export function nativeCompletionVerified(completion, count){
 const label=`${count} OF 6 SIMULATED RAYS`;
 return Number.isInteger(count)&&count>=0&&count<=6&&completion?.realTimerElapsed===true&&completion.realWallMs>=119000&&
  completion.celebration?.screen?.split(' ').includes('celebrate')===true&&
  completion.celebration.heading==='Replay result.'&&completion.celebration.rayLabel?.includes(label)===true&&
  completion.celebration.replayLabel===true&&completion.celebration.cameraCalls===0&&
  completion.progressUnchangedAtCelebration===true&&completion.progressUnchangedAfterReload===true&&
  completion.reload?.screen==='app home'&&completion.reload.cameraCalls===0&&
  completion.inactivePacket?.active===false&&completion.inactivePacket.metrics?.acknowledgedEvents===count&&
  (count===6?completion.path==='six-ray-auto-celebration':completion.path==='check-confirmation'&&
   completion.check?.heading==='Replay finished.'&&completion.check.rayLabel?.includes(label)===true&&completion.realCompleteButtonClicked===true);
}

export function assessNativeCase(row, expected, nativeRows){
 row.nativePoseFrameCoverage=nativeFrameCoverage(nativeRows,expected);
 row.nativeFileEvents=nativeRows.filter(item=>item.kind==='event')
  .map(item=>({seq:item.seq,gesture:item.gesture,fileMs:item.eventFileMs}));
 const seqs=new Set();
 row.nativeEventLogValid=row.nativeFileEvents.every((item,index)=>{
  if(!Number.isInteger(item.seq)||item.seq!==index+1||seqs.has(item.seq)||
    !['left-raise','right-raise'].includes(item.gesture)||!Number.isFinite(item.fileMs))return false;
  seqs.add(item.seq);return true;
 });
 const metrics=row.lastPacket?.metrics;
 row.completeFileVerified=metrics?.fullFileProcessed===true&&metrics.videoFrames===expected.frames&&
  metrics.decodedFrames===expected.frames&&metrics.acceptedFrames===expected.frames&&
  metrics.discardedEpochFrames===0&&row.nativePoseFrameCoverage.complete;
 row.nativeDeliveryMatches=row.nativeEventLogValid&&
  JSON.stringify(row.nativeFileEvents.map(item=>item.gesture))===JSON.stringify(row.observedGestures);
 row.uiScoringEvidenceVerified=nativeUiScoreVerified(row.ui);
 row.nativeScoringMatches=row.uiScoringEvidenceVerified&&row.ui.count===row.nativeFileEvents.length&&
  metrics?.nativeRecognizedEvents===row.nativeFileEvents.length&&
  metrics?.acknowledgedEvents===row.nativeFileEvents.length;
 row.executionAcceptance=row.integrationVerified&&row.nativeScalarLog?.available===true&&
  row.completeFileVerified&&row.nativeDeliveryMatches&&row.nativeScoringMatches?'passed':'failed';
 row.expectationKnown=expected.expectationKnown===true;
 row.expectedGestures=row.expectationKnown?expected.expectedGestures:null;
 row.expectationScope='Frozen sequence only when expectationKnown=true; unknown empty arrays are not certified negatives';
 if(row.expectationKnown&&expected.eventWindowsMs!==undefined){
  row.expectedEventWindowsMs=expected.eventWindowsMs;
  row.eventTimingVerified=row.nativeFileEvents.length===expected.eventWindowsMs.length&&
   row.nativeFileEvents.every((item,i)=>item.fileMs>=expected.eventWindowsMs[i][0]&&item.fileMs<=expected.eventWindowsMs[i][1]);
 }
 if(!row.expectationKnown){
  row.recognitionAcceptance=row.executionAcceptance==='passed'?'observed-only':'failed';
  return;
 }
 const count=expected.expectedGestures.length;
 row.recognitionAcceptance=row.executionAcceptance==='passed'&&row.eventTimingVerified!==false&&
  JSON.stringify(row.observedGestures)===JSON.stringify(expected.expectedGestures)&&
  row.ui?.count===count&&metrics?.acknowledgedEvents===count?'passed':'failed';
}
