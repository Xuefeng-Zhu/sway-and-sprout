package com.togethermove.tv;
import android.content.Context;
import android.content.Intent;
final class NativeVideoFactory {
 private NativeVideoFactory() {}
 static MotionSource create(Context context,Intent intent) {
  if(!intent.getBooleanExtra("nativeVideo",false))return null;
  String name=intent.getStringExtra("nativeVideoCase");
  if(name==null)name="clear";
  String model=intent.getStringExtra("nativeModel");
  if(model==null)model="int8";
  String config=NativeVideoCase.configAsset(name,model);
  String refinement=intent.getStringExtra("nativeRefinement");
  if(refinement==null)refinement="image";
  if(!refinement.equals("image")&&!refinement.equals("tracked"))throw new IllegalArgumentException("Unknown native refinement profile");
  ReplayReferenceProfile reference = ReplayReferenceProfile.parse(intent.getStringExtra("nativeReferenceChecks"));
  return new NativeVideoReplay(context,config,refinement.equals("image"),reference);
 }
}
