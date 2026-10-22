// Illustrations reflect counted or confirmed progress only. No timers or input
// APIs belong here; this module does not mutate the supplied progress.
const MOMENTS=[['wake','Wake'],['sun','Sunshine'],['rain','Rain']];
const STAGES=['A seed, ready to grow','A little sprout','A stem takes shape',
  'Leaves open','A bud appears','Almost in bloom','Your flower is in bloom'];
const escape=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
function bounded(value,min,max,fallback){return Number.isFinite(value)?Math.min(max,Math.max(min,Math.floor(value))):fallback;}

export function gardenStage(count=0,total=6){
  const target=bounded(total,1,100,6),earned=bounded(count,0,target,0);
  const stage=earned===0?0:Math.min(6,Math.max(1,Math.floor(earned/target*6)));
  return {count:earned,total:target,stage,label:STAGES[stage]};
}

function plant(stage,{x=300,ground=286,scale=1,petal='#f4ae8d',seed=true}={}){
  if(stage===0)return seed?`<g class="garden-seed" transform="translate(${x} ${ground})"><path d="M-14 0q14-7 28 0" fill="none" stroke="#bc9570" stroke-width="3" stroke-linecap="round"/><ellipse cx="0" cy="9" rx="6" ry="3" fill="#e6c798"/></g>`:'';
  const top=[0,252,225,196,161,139,117][stage];
  const leaves=`<path d="M300 251C265 250 247 235 245 218c29-5 49 7 55 33Z" fill="#a6c779"/>
    <path d="M300 237c32 1 53-13 58-33-29-8-51 9-58 33Z" fill="#d1e397"/>`;
  const upperLeaves=stage>=3?`<path d="M300 208c-31 0-47-14-47-31 25-5 43 8 47 31Z" fill="#b5d584"/>
    <path d="M300 189c27 0 43-12 46-27-25-5-40 7-46 27Z" fill="#c9df91"/>`:'';
  const bud=stage>=4&&stage<6?`<g transform="translate(300 ${top})"><path d="M0 15C-27 4-24-20 0-30 24-20 27 4 0 15Z" fill="${petal}"/><path d="M0 19c-18-3-23-16-20-24L0 7 20-5c3 8-2 21-20 24Z" fill="#99bd70"/>${stage===5?'<path d="M-19-9Q0-24 19-9" fill="none" stroke="#fff0d1" stroke-width="3"/>':''}</g>`:'';
  const bloom=stage===6?`<g class="garden-bloom" transform="translate(300 ${top})">
    ${[-90,-30,30,90,150,210].map(angle=>`<ellipse cy="-29" rx="18" ry="29" transform="rotate(${angle})" fill="${petal}"/>`).join('')}
    <circle r="23" fill="#e8c46e"/><circle r="13" fill="#765735"/>
    <path d="M-5-4h1M5 3h1M-2 7h1M6-7h1" stroke="#d7b67c" stroke-width="3" stroke-linecap="round"/>
  </g>`:'';
  return `<g class="garden-plant" data-plant-stage="${stage}" transform="translate(${x} ${ground}) scale(${scale}) translate(-300 -286)">
    <path d="M300 286Q293 240 300 ${top}" fill="none" stroke="#b2ce81" stroke-width="7" stroke-linecap="round"/>
    ${stage===1?'<path d="M300 263c-23 0-34-11-34-23 18-3 31 6 34 23Zm0-1c21 0 31-11 33-22-19-4-29 6-33 22Z" fill="#c9df91"/>':leaves}
    ${upperLeaves}${bud}${bloom}
  </g>`;
}

function soil(){return `<g class="garden-soil"><path d="M48 292Q300 259 552 292L536 323Q300 349 64 323Z" fill="#674c35"/>
  <path d="M48 292Q300 324 552 292" fill="none" stroke="#9f7950" stroke-width="4" stroke-linecap="round"/>
  <path d="m101 310 20 2m89 10 17 1m108 0 19-1m93-9 21-2" fill="none" stroke="#bc9570" stroke-width="3" stroke-linecap="round"/></g>`;}

function harvest(ready){
  if(!ready)return '';
  return `<g class="garden-harvest">
    <path d="M204 260c-3-77 16-112 96-112s99 35 96 112" fill="none" stroke="#c2a478" stroke-width="13"/>
    <path d="M189 240h222l-25 94q-86 25-172 0Z" fill="#c7a477"/>
    <path d="m214 251 13 81m27-81 6 87m35-87v90m35-90-6 87m34-87-13 81M201 277h198m-192 27h186" fill="none" stroke="#8d6a45" stroke-width="4"/>
    ${plant(6,{x:254,ground:259,scale:.49,petal:'#f4ae8d'})}
    ${plant(6,{x:310,ground:260,scale:.58,petal:'#f0d576'})}
    ${plant(6,{x:357,ground:260,scale:.45,petal:'#d8e5ae'})}
    <path d="M190 240q110 27 220 0" fill="none" stroke="#dfc59e" stroke-width="10" stroke-linecap="round"/>
  </g>`;
}

export function gardenMarkup({completed=[],count=0,total=6,label='',kind='round',showCaption=true}={}){
  const type=['round','garden','harvest'].includes(kind)?kind:'round';
  const grown=new Set(Array.isArray(completed)?completed.filter(id=>MOMENTS.some(([key])=>key===id)):[]);
  const growth=gardenStage(count,total),ready=grown.size===3;
  const description=type==='round'?growth.label:type==='harvest'&&ready?'Three blooms, gathered together':
    grown.size===0?'Three seeds, waiting for your first moment':`${grown.size} of 3 garden moments grown`;
  const image=type==='round'?soil()+plant(growth.stage):type==='harvest'&&ready?harvest(true):
    soil()+MOMENTS.map(([id],index)=>plant(grown.has(id)?6:0,{x:148+index*152,ground:288,
      scale:.63,petal:['#f4ae8d','#f0d576','#d8e5ae'][index]})).join('');
  const caption=label?escape(label):type==='round'?`${growth.count} of ${growth.total} movements counted`:
    type==='harvest'&&ready?'Your garden, gathered.':'Your garden';
  return `<figure class="garden-view garden-view--${type}" data-garden-kind="${type}" data-growth="${growth.stage}" data-grown="${grown.size}">
    <svg class="garden-illustration" viewBox="0 0 600 370" role="img" aria-label="${escape(description)}" xmlns="http://www.w3.org/2000/svg">
      <path d="M62 337q238 31 476 0" fill="none" stroke="#315542" stroke-width="2"/>${image}
    </svg>
    ${showCaption?`<figcaption class="garden-caption"><b>${caption}</b><span class="garden-stage">${escape(description)}</span></figcaption>`:''}
    ${type==='garden'?`<div class="garden-labels" aria-hidden="true">${MOMENTS.map(([id,name])=>`<span class="${grown.has(id)?'grown':'waiting'}">${escape(name)}<small>${grown.has(id)?'Grown':'A seed for now'}</small></span>`).join('')}</div>`:''}
  </figure>`;
}
