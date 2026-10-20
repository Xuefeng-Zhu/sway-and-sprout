package com.togethermove.tv;
import android.content.Context;
import android.content.Intent;
final class NativeVideoFactory {
 private NativeVideoFactory() {}
 static MotionSource create(Context context,Intent intent) {
  if(!intent.getBooleanExtra("nativeVideo",false))return null;
  String name=intent.getStringExtra("nativeVideoCase");
  if(name==null)name="clear";
  java.util.Set<String> allowed=new java.util.HashSet<>(java.util.Arrays.asList("clear","frontal","nearface","right-negative","both-up-negative","natural-original","natural-mirror"));
  if(!allowed.contains(name))throw new IllegalArgumentException("Unknown native verification fixture");
  String model=intent.getStringExtra("nativeModel");
  if(model==null)model="int8";
  if(!model.equals("int8")&&!model.equals("float16")&&!model.equals("thunder"))throw new IllegalArgumentException("Unknown native verification model");
  String refinement=intent.getStringExtra("nativeRefinement");
  if(refinement==null)refinement="image";
  if(!refinement.equals("image")&&!refinement.equals("tracked"))throw new IllegalArgumentException("Unknown native refinement profile");
  return new NativeVideoReplay(context,"verification/"+name+(model.equals("int8")?"":"."+model)+".json",refinement.equals("image"));
 }
}
