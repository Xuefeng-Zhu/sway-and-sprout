import test from 'node:test';
import assert from 'node:assert/strict';
import {gardenMarkup,gardenStage} from '../src/garden-view.js';

test('six counted movements visibly progress from a seed to one completed bloom',()=>{
  const descriptions=new Set();
  for(let count=0;count<=6;count++){
    const growth=gardenStage(count);
    assert.equal(growth.count,count);
    assert.equal(growth.stage,count);
    descriptions.add(growth.label);
    const markup=gardenMarkup({count});
    assert.match(markup,new RegExp(`data-growth="${count}"`));
    if(count===0){
      assert.match(markup,/class="garden-seed"/);
      assert.doesNotMatch(markup,/class="garden-plant"|class="garden-bloom"/);
    }else{
      assert.match(markup,/class="garden-plant"/);
      if(count<6)assert.doesNotMatch(markup,/class="garden-bloom"/);
      else assert.match(markup,/class="garden-bloom"/);
    }
  }
  assert.equal(descriptions.size,7,'Every counted stage has distinct accessible feedback');
});

test('invalid or absent count cannot fabricate growth and all numeric inputs stay bounded',()=>{
  for(const count of [-10,NaN,Infinity,-Infinity,undefined,'6']){
    assert.equal(gardenStage(count).stage,0);
    assert.doesNotMatch(gardenMarkup({count}),/class="garden-bloom"/);
  }
  assert.equal(gardenStage(99).count,6);
  assert.equal(gardenStage(99).stage,6);
  assert.equal(gardenStage(1.9).count,1);
  for(const total of [NaN,Infinity,undefined])assert.equal(gardenStage(0,total).total,6);
  assert.equal(gardenStage(2,-4).total,1);
  assert.equal(gardenStage(200,1000).total,100);
});

test('the garden illustration is static and deterministic without new counted progress',()=>{
  const first=gardenMarkup({count:0});
  assert.equal(gardenMarkup({count:0}),first);
  assert.doesNotMatch(first,/<animate\b|<animateTransform\b|class="garden-bloom"/);
  const grown=gardenMarkup({count:3});
  assert.equal(gardenMarkup({count:3}),grown);
  assert.notEqual(grown,first);
});

test('harvest illustration requires all three distinct earned moments',()=>{
  for(const completed of [[],['wake'],['wake','sun'],['wake','wake','sun'],['wake','sun','unknown']]){
    assert.doesNotMatch(gardenMarkup({kind:'harvest',completed}),/class="garden-harvest"/);
  }
  const harvested=gardenMarkup({kind:'harvest',completed:['rain','sun','wake','wake','unknown']});
  assert.match(harvested,/class="garden-harvest"/);
  assert.match(harvested,/data-grown="3"/);
  assert.equal((harvested.match(/class="garden-bloom"/g)||[]).length,3);
});

test('labels are escaped and rendering never mutates supplied progress',()=>{
  const completed=Object.freeze(['wake','unknown','wake']);
  const label='<img src=x onerror="boom"> & \'flowers\'';
  const markup=gardenMarkup({completed,label,kind:'garden'});
  assert.match(markup,/&lt;img src=x onerror=&quot;boom&quot;&gt; &amp; &#39;flowers&#39;/);
  assert.doesNotMatch(markup,/<img\b/);
  assert.match(markup,/data-grown="1"/);
  assert.deepEqual(completed,['wake','unknown','wake']);
  assert.match(gardenMarkup({kind:'<script>'}),/data-garden-kind="round"/);
});
