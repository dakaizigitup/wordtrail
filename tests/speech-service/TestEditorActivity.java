package org.wordtrail.speechtest;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.WindowInsets;
import android.widget.*;

public final class TestEditorActivity extends Activity {
    @Override public void onCreate(Bundle state){
        super.onCreate(state);LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(20,20,20,20);
        for(String name:new String[]{"普通输入","密码输入","数字输入"}){
            EditText field=new EditText(this);field.setHint(name);field.setContentDescription(name);
            field.setInputType(name.equals("密码输入")?InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD:name.equals("数字输入")?InputType.TYPE_CLASS_NUMBER:InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
            field.setTextSize(16);body.addView(field,new LinearLayout.LayoutParams(-1,110));
        }
        body.setFocusableInTouchMode(true);setContentView(body);body.requestFocus();
        if(android.os.Build.VERSION.SDK_INT>=30){body.setOnApplyWindowInsetsListener((view,insets)->{android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars());view.setPadding(20,bars.top+20,20,bars.bottom+20);return insets;});body.requestApplyInsets();}
    }
}
