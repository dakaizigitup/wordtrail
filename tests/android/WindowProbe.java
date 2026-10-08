package org.wordtrail.test;

import android.app.Instrumentation;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.graphics.Rect;
import android.os.Bundle;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import org.json.JSONArray;
import org.json.JSONObject;

// Run in its own test package, preserving the IME and host application process.
public final class WindowProbe extends Instrumentation {
    private boolean stream;
    private Bundle arguments;
    @Override public void onCreate(Bundle args) { super.onCreate(args); arguments=args;stream=args!=null && "true".equals(args.getString("stream"));start(); }
    @Override public void onStart() {
        Bundle result=new Bundle();
        try {
            AccessibilityServiceInfo config=getUiAutomation().getServiceInfo();
            config.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS | AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
            getUiAutomation().setServiceInfo(config);
            if(arguments!=null && arguments.containsKey("hold_key")){
                Thread.sleep(700);JSONArray initial=snapshot();JSONObject key=find(initial,arguments.getString("hold_key"));
                Rect rect=rect(key);float x=rect.exactCenterX(),y=rect.exactCenterY();long down=android.os.SystemClock.uptimeMillis();
                touch(down,android.view.MotionEvent.ACTION_DOWN,x,y);Thread.sleep(Integer.parseInt(arguments.getString("hold_ms","750")));
                JSONArray options=snapshot();String expected=arguments.containsKey("option")?"长按选项 "+arguments.getString("option"):"按键长按选项";
                for(int attempt=0;attempt<8;attempt++){try{find(options,expected);break;}catch(IllegalStateException missing){Thread.sleep(100);options=snapshot();}}
                result.putString("held_nodes",options.toString());
                if(arguments.containsKey("shot")){
                    java.io.File file=new java.io.File(getContext().getExternalFilesDir(null),arguments.getString("shot")+".png");
                    try(java.io.FileOutputStream stream=new java.io.FileOutputStream(file)){android.graphics.Bitmap image=getUiAutomation().takeScreenshot();image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,stream);image.recycle();}
                    result.putString("screenshot",file.getAbsolutePath());
                }
                if(arguments.containsKey("option")){Rect target;try{target=rect(find(options,expected));}catch(IllegalStateException error){touch(down,android.view.MotionEvent.ACTION_CANCEL,x,y);throw error;}x=target.exactCenterX();y=target.exactCenterY();touch(down,android.view.MotionEvent.ACTION_MOVE,x,y);Thread.sleep(120);}
                if("true".equals(arguments.getString("outside"))){x=20;y=20;touch(down,android.view.MotionEvent.ACTION_MOVE,x,y);Thread.sleep(120);}
                if("true".equals(arguments.getString("cancel")))touch(down,android.view.MotionEvent.ACTION_CANCEL,x,y);
                else touch(down,android.view.MotionEvent.ACTION_UP,x,y);
                Thread.sleep(1500);
            }
            if(arguments!=null && arguments.containsKey("burst")){
                Thread.sleep(700);
                String text=arguments.getString("burst");int gap=Integer.parseInt(arguments.getString("gap","60"));
                JSONArray initial=new JSONArray();for(AccessibilityWindowInfo window:getUiAutomation().getWindows())visit(window.getRoot(),initial);
                long started=android.os.SystemClock.uptimeMillis();JSONArray trace=new JSONArray();
                for(int index=0;index<text.length();index++){
                    JSONObject key=null;String label=String.valueOf(text.charAt(index));
                    for(int n=0;n<initial.length();n++){JSONObject candidate=initial.getJSONObject(n);if(candidate.getString("class").equals("android.widget.Button") && candidate.getString("text").equalsIgnoreCase(label)){key=candidate;break;}}
                    if(key==null)throw new IllegalStateException("Missing key "+label);
                    String[] coordinates=key.getString("bounds").replaceAll("[\\[\\]]",",").split(",");java.util.ArrayList<Integer> values=new java.util.ArrayList<>();for(String part:coordinates)if(!part.isEmpty())values.add(Integer.parseInt(part));
                    float x=(values.get(0)+values.get(2))/2f,y=(values.get(1)+values.get(3))/2f;
                    if("true".equals(arguments.getString("trace")) && index<6){JSONArray current=new JSONArray();for(AccessibilityWindowInfo window:getUiAutomation().getWindows())visit(window.getRoot(),current);JSONObject entry=new JSONObject().put("index",index).put("key",label).put("tap_x",x).put("tap_y",y);for(int n=0;n<current.length();n++){JSONObject candidate=current.getJSONObject(n);if(candidate.getString("class").equals("android.widget.Button") && candidate.getString("text").equalsIgnoreCase(label)){entry.put("current_bounds",candidate.getString("bounds"));break;}}trace.put(entry);}
                    long down=android.os.SystemClock.uptimeMillis();
                    android.view.MotionEvent event=android.view.MotionEvent.obtain(down,down,android.view.MotionEvent.ACTION_DOWN,x,y,0);event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN);getUiAutomation().injectInputEvent(event,false);event.recycle();
                    android.os.SystemClock.sleep(Math.max(2,gap/3));
                    event=android.view.MotionEvent.obtain(down,android.os.SystemClock.uptimeMillis(),android.view.MotionEvent.ACTION_UP,x,y,0);event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN);getUiAutomation().injectInputEvent(event,false);event.recycle();
                    android.os.SystemClock.sleep(Math.max(0,started+(index+1)*gap-android.os.SystemClock.uptimeMillis()));
                }
                result.putLong("burst_ms",android.os.SystemClock.uptimeMillis()-started);Thread.sleep(2000);
                result.putString("trace",trace.toString());
            }
            if(stream){
                // Keep the accessibility connection stable during dictation;
                // reconnecting it can make Android restart the input view.
                while(true){
                    JSONArray current=new JSONArray();
                    for(AccessibilityWindowInfo window:getUiAutomation().getWindows())visit(window.getRoot(),current);
                    Bundle update=new Bundle();update.putString("nodes",current.toString());sendStatus(0,update);Thread.sleep(250);
                }
            }
            JSONArray nodes=new JSONArray();
            for(int attempt=0;attempt<10 && nodes.length()==0;attempt++){
                Thread.sleep(100);
                for(AccessibilityWindowInfo window:getUiAutomation().getWindows()) visit(window.getRoot(),nodes);
            }
            result.putString("nodes",nodes.toString());
            finish(0,result);
        } catch(Exception error) { result.putString("error",error.toString()); finish(1,result); }
    }
    private JSONArray snapshot() throws Exception {JSONArray nodes=new JSONArray();for(AccessibilityWindowInfo window:getUiAutomation().getWindows())visit(window.getRoot(),nodes);return nodes;}
    private JSONObject find(JSONArray nodes,String label) throws Exception {for(int i=0;i<nodes.length();i++){JSONObject n=nodes.getJSONObject(i);if(n.optString("description").equals(label) || n.optString("text").equals(label))return n;}throw new IllegalStateException("Missing control "+label);}
    private Rect rect(JSONObject node){java.util.regex.Matcher m=java.util.regex.Pattern.compile("-?\\d+").matcher(node.optString("bounds"));int[] p=new int[4];for(int i=0;i<4;i++){m.find();p[i]=Integer.parseInt(m.group());}return new Rect(p[0],p[1],p[2],p[3]);}
    private void touch(long down,int action,float x,float y){android.view.MotionEvent event=android.view.MotionEvent.obtain(down,android.os.SystemClock.uptimeMillis(),action,x,y,0);event.setSource(android.view.InputDevice.SOURCE_TOUCHSCREEN);getUiAutomation().injectInputEvent(event,true);event.recycle();}
    private void visit(AccessibilityNodeInfo node,JSONArray output) throws Exception {
        if(node==null) return;
        Rect bounds=new Rect(); node.getBoundsInScreen(bounds);
        JSONObject item=new JSONObject().put("text",node.getText()==null?"":node.getText().toString())
            .put("description",node.getContentDescription()==null?"":node.getContentDescription().toString())
            .put("class",String.valueOf(node.getClassName()))
            .put("enabled",node.isEnabled())
            .put("checked",node.isChecked())
            .put("bounds","["+bounds.left+","+bounds.top+"]["+bounds.right+","+bounds.bottom+"]");
        output.put(item);
        for(int index=0;index<node.getChildCount();index++) visit(node.getChild(index),output);
    }
}
