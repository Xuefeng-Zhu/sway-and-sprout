// Optional summary backup. No capture, model, automatic requests or AWS credentials.
const IDS=['wake','sun','rain'];
export const CLOUD_STORAGE_PREFIX='togethermove.cloud.v1:';
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const CAPABILITY=/^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$/;
const MAX_BYTES=2048;
const messages={
  disabled:'Garden backup is not configured. Your garden stays on this device.',
  blocked:'Return to your garden before using backup. Test activity cannot be backed up.',
  busy:'A garden request is already in progress.',
  storage:'The backup key could not be saved on this device. No backup request was sent.',
  'storage-after-request':'The request finished, but its backup key could not be updated on this device. Restore before trying another backup.',
  missing:'No cloud copy was found for this browser. Your local garden is unchanged.',
  conflict:'The cloud copy changed. Restore it before backing up again.',
  retired:'This cloud copy was deleted. Choose Back up garden to make a new copy.',
  invalid:'The backup service returned an unexpected response. Your local garden is unchanged.',
  unavailable:'Garden backup is unavailable. Your local garden is unchanged.',
  timeout:'The backup request timed out. It may have reached the service. Restore before trying again.',
  cancelled:'The request was cancelled. It may have reached the service. Your local garden is unchanged.',
  'restore-first':'Restore the cloud copy before trying to delete it.',
  'delete-local-key':'The cloud copy was deleted, but its key could not be removed from this browser.',
};
class CloudGardenError extends Error {
  constructor(code){super(messages[code]||messages.unavailable);this.name='CloudGardenError';this.code=code;}
}
export const cloudGardenErrorMessage=error=>messages[error?.code]||messages.unavailable;
const fail=code=>{throw new CloudGardenError(code);};
const exactKeys=(value,keys)=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&
  Object.keys(value).sort().join(',')===[...keys].sort().join(',');

export function cloudBackupLocationAllowed(value){
  if(!value||!['http:','https:'].includes(value.protocol)||!value.hostname||
    ['app.togethermove.local','togethermove.local'].includes(value.hostname))return false;
  const query=new URLSearchParams(value.search||'');
  return !['video-verification','video','synthetic'].includes(query.get('input'))&&
    !['video','synthetic'].includes(query.get('source'))&&query.get('policy')!=='strict';
}

export function normalizeCloudEndpoint(value,{allowLocalHttp=false}={}){
  if(typeof value!=='string'||!value.trim())return '';
  try{
    const url=new URL(value.trim());
    const local=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
    if(url.protocol!=='https:'&&!(allowLocalHttp&&local&&url.protocol==='http:'))return '';
    if(url.username||url.password||url.search||url.hash||url.pathname.includes('//'))return '';
    return url.href.replace(/\/$/,'');
  }catch{return '';}
}

export function cleanGardenProgress(value){
  if(!exactKeys(value,['completed','sessions'])||!Array.isArray(value.completed)||value.completed.length>3||
    !Number.isSafeInteger(value.sessions)||value.sessions<0||
    value.completed.some(id=>!IDS.includes(id))||new Set(value.completed).size!==value.completed.length)fail('invalid');
  return {completed:IDS.filter(id=>value.completed.includes(id)),sessions:value.sessions};
}

export function mergeGardenProgress(local,remote){
  const a=cleanGardenProgress(local),b=cleanGardenProgress(remote);
  return {completed:IDS.filter(id=>a.completed.includes(id)||b.completed.includes(id)),sessions:Math.max(a.sessions,b.sessions)};
}

function validateRecord(value){
  if(!exactKeys(value,['schemaVersion','generation','version','progress','updatedAt','expiresAt'])||value.schemaVersion!==1||!UUID.test(value.generation)||
    !Number.isSafeInteger(value.version)||value.version<1||!Number.isSafeInteger(value.expiresAt)||value.expiresAt<1||
    typeof value.updatedAt!=='string'||value.updatedAt.length>40||!/^\d{4}-\d{2}-\d{2}T/.test(value.updatedAt)||
    !/(?:Z|\+00:00)$/.test(value.updatedAt)||!Number.isFinite(Date.parse(value.updatedAt)))fail('invalid');
  return {...value,progress:cleanGardenProgress(value.progress)};
}

function encodeCapability(bytes){
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  let bits=0,buffer=0,result='';
  for(const byte of bytes){buffer=(buffer<<8)|byte;bits+=8;while(bits>=6){bits-=6;result+=alphabet[(buffer>>>bits)&63];}}
  if(bits)result+=alphabet[(buffer<<(6-bits))&63];
  return result;
}

async function readRecord(response){
  if(response.headers?.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json')fail('invalid');
  const length=Number(response.headers.get('content-length'));
  if(Number.isFinite(length)&&length>MAX_BYTES)fail('invalid');
  let text;
  if(response.body?.getReader){
    const reader=response.body.getReader(),chunks=[];let size=0;
    try{
      while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BYTES){await reader.cancel();fail('invalid');}chunks.push(value);}
      const bytes=new Uint8Array(size);let offset=0;
      for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
      text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
    }finally{reader.releaseLock();}
  }else{
    text=await response.text();if(new TextEncoder().encode(text).length>MAX_BYTES)fail('invalid');
  }
  try{return validateRecord(JSON.parse(text));}catch(error){if(error instanceof CloudGardenError)throw error;fail('invalid');}
}

export function createCloudGardenClient({endpoint,storage,fetchImpl=globalThis.fetch,
  cryptoImpl=globalThis.crypto,timeoutMs=5000,allowLocalHttp=false}={}){
  const base=normalizeCloudEndpoint(endpoint,{allowLocalHttp});
  const key=CLOUD_STORAGE_PREFIX+base;
  let identity=null,activeRequest=null;
  if(base){
    try{
      const value=JSON.parse(storage?.getItem(key)||'null');
      if(exactKeys(value,['schemaVersion','gardenId','token','generation','version','retired'])&&value.schemaVersion===1&&
        UUID.test(value.gardenId)&&CAPABILITY.test(value.token)&&Number.isSafeInteger(value.version)&&value.version>=0&&
        (value.version===0?value.generation===null:UUID.test(value.generation))&&typeof value.retired==='boolean')identity=value;
    }catch{}
  }
  const snapshot=()=>({configured:!!base,hasIdentity:!!identity&&!identity.retired,version:identity&&!identity.retired?identity.version:0,busy:!!activeRequest});
  function persist(value,code){
    const text=JSON.stringify(value);
    try{storage.setItem(key,text);if(storage.getItem(key)!==text)fail(code);}catch{fail(code);}
    identity=value;
  }
  function permitted(context){
    if(!base)fail('disabled');
    if(context?.active!==false||context?.source!=='confirmed')fail('blocked');
    if(activeRequest)fail('busy');
  }
  function ensureIdentity(){
    if(identity&&!identity.retired)return;
    try{
      const value={schemaVersion:1,gardenId:cryptoImpl.randomUUID(),token:encodeCapability(cryptoImpl.getRandomValues(new Uint8Array(32))),generation:null,version:0,retired:false};
      if(!UUID.test(value.gardenId)||!CAPABILITY.test(value.token))fail('storage');
      // A recoverable capability must exist before sending a create request.
      persist(value,'storage');
    }catch{fail('storage');}
  }
  async function request(method,body,version){
    if(typeof fetchImpl!=='function')fail('unavailable');
    const controller=new AbortController();
    let timer,rejectWait;
    const stopped=new Promise((_,reject)=>{rejectWait=reject;});
    const current={cancel(){controller.abort();rejectWait(new CloudGardenError('cancelled'));}};
    activeRequest=current;
    timer=setTimeout(()=>{controller.abort();rejectWait(new CloudGardenError('timeout'));},
      Number.isFinite(timeoutMs)?Math.max(100,Math.min(30000,timeoutMs)):5000);
    const headers={Accept:'application/json',Authorization:`Bearer ${identity.token}`};
    if(body!==undefined)headers['Content-Type']='application/json';
    if(version!==undefined)headers['If-Match']=`"${version}"`;
    const work=(async()=>{
      const response=await fetchImpl(`${base}/gardens/${identity.gardenId}`,{
        method,headers,...(body!==undefined?{body:JSON.stringify(body)}:{}),
        signal:controller.signal,credentials:'omit',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',mode:'cors',
      });
      if(response.status===404)fail('missing');
      if(response.status===409)fail('conflict');
      if(response.status===410)fail('retired');
      if(method==='DELETE'){if(response.status!==204)fail('unavailable');return null;}
      if(method==='GET'?response.status!==200:![200,201].includes(response.status))fail('unavailable');
      return readRecord(response);
    })();
    try{return await Promise.race([work,stopped]);}
    catch(error){if(error instanceof CloudGardenError)throw error;fail('unavailable');}
    finally{clearTimeout(timer);if(activeRequest===current)activeRequest=null;}
  }
  async function perform(...args){
    try{return await request(...args);}
    catch(error){
      // No retry: a separate user action must create a fresh resource/key after
      // an authoritative not-found or owner-validated revocation response.
      if(identity&&['missing','retired'].includes(error.code))persist({...identity,retired:true},'storage-after-request');
      throw error;
    }
  }
  return {
    snapshot,
    cancel(){activeRequest?.cancel();},
    async backup(progress,context){
      permitted(context);const clean=cleanGardenProgress(progress);ensureIdentity();
      const expectedVersion=identity.version;
      const record=await perform('PUT',{schemaVersion:1,expectedVersion,
        ...(expectedVersion?{expectedGeneration:identity.generation}:{}),progress:clean});
      if(record.version!==expectedVersion+1||(expectedVersion&&record.generation!==identity.generation)||
        JSON.stringify(record.progress)!==JSON.stringify(clean))fail('invalid');
      persist({...identity,generation:record.generation,version:record.version},'storage-after-request');return record;
    },
    async restore(context){
      permitted(context);if(!identity||identity.retired)fail('missing');
      const record=await perform('GET');
      if(identity.generation&&record.generation!==identity.generation)fail('conflict');
      if(record.version<identity.version)fail('invalid');
      persist({...identity,generation:record.generation,version:record.version},'storage-after-request');return record;
    },
    async remove(context){
      permitted(context);if(!identity||identity.retired)fail('missing');if(identity.version<1)fail('restore-first');
      await perform('DELETE',undefined,`${identity.generation}:${identity.version}`);identity=null;
      try{storage.removeItem(key);if(storage.getItem(key)!==null)fail('delete-local-key');}catch{fail('delete-local-key');}
    },
  };
}
