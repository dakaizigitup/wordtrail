package org.wordtrail.speechtest;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.WindowInsets;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Separate synthetic host: records IME actions locally, never sends messages. */
public final class BehaviorEditorActivity extends Activity {
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        String kind=getIntent().getStringExtra("kind");if(kind==null)kind="text";
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);
        TextView result=new TextView(this);result.setText("action:none");result.setContentDescription("动作记录");body.addView(result);
        EditText field=new EditText(this);field.setId(View.generateViewId());field.setContentDescription("测试输入");field.setTextSize(20);
        int type=InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE,action=EditorInfo.IME_ACTION_NONE;
        if(kind.equals("search")){type=InputType.TYPE_CLASS_TEXT;action=EditorInfo.IME_ACTION_SEARCH;}
        if(kind.equals("send")){type=InputType.TYPE_CLASS_TEXT;action=EditorInfo.IME_ACTION_SEND;}
        if(kind.equals("url")){type=InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI;action=EditorInfo.IME_ACTION_GO;}
        if(kind.equals("next")){type=InputType.TYPE_CLASS_TEXT;action=EditorInfo.IME_ACTION_NEXT;}
        if(kind.equals("custom")){type=InputType.TYPE_CLASS_TEXT;action=EditorInfo.IME_ACTION_GO;}
        if(kind.equals("number")){type=InputType.TYPE_CLASS_NUMBER;action=EditorInfo.IME_ACTION_DONE;}
        if(kind.equals("decimal")){type=InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL|InputType.TYPE_NUMBER_FLAG_SIGNED;action=EditorInfo.IME_ACTION_DONE;}
        if(kind.equals("phone")){type=InputType.TYPE_CLASS_PHONE;action=EditorInfo.IME_ACTION_NEXT;}
        if(kind.equals("password")){type=InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD;action=EditorInfo.IME_ACTION_DONE;}
        field.setInputType(type);if((type&InputType.TYPE_TEXT_FLAG_MULTI_LINE)==0)field.setSingleLine(true);field.setImeOptions(action);
        if(kind.equals("no_enter"))field.setImeOptions(EditorInfo.IME_ACTION_SEND|EditorInfo.IME_FLAG_NO_ENTER_ACTION);
        if(kind.equals("private"))field.setImeOptions(EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING|EditorInfo.IME_ACTION_NONE);
        if(kind.equals("custom"))field.setImeActionLabel("确认订单",77);
        body.addView(field,new LinearLayout.LayoutParams(-1,150));
        EditText next=new EditText(this);next.setId(View.generateViewId());next.setContentDescription("第二输入框");next.setInputType(InputType.TYPE_CLASS_TEXT);next.setImeOptions(EditorInfo.IME_ACTION_DONE);body.addView(next,new LinearLayout.LayoutParams(-1,120));
        field.setNextFocusForwardId(next.getId());
        field.setOnEditorActionListener((v,id,event)->{result.setText("action:"+id);if(id==EditorInfo.IME_ACTION_NEXT)next.requestFocus();return true;});
        String seed=getIntent().getStringExtra("seed");if(seed!=null)field.setText(seed);
        if(getIntent().hasExtra("start"))field.setSelection(getIntent().getIntExtra("start",0),getIntent().getIntExtra("end",0));else field.setSelection(field.length());
        setContentView(body);field.requestFocus();
        if(android.os.Build.VERSION.SDK_INT>=30){body.setOnApplyWindowInsetsListener((v,insets)->{android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars());v.setPadding(24,bars.top+24,24,bars.bottom+24);return insets;});body.requestApplyInsets();}
    }
}
