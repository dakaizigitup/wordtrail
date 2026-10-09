package org.wordtrail.ime;

import android.content.Context;
import android.graphics.Canvas;
import android.widget.Button;

/** Updates the action label without replacing a key during fast input. */
final class EnterKey extends Button {
    private final KeyboardIcon arrow;
    EnterKey(Context context,int color){
        super(context);arrow=new KeyboardIcon(KeyboardIcon.ENTER,color,false);
        setMaxLines(1);setHorizontallyScrolling(false);
        setAutoSizeTextTypeUniformWithConfiguration(9,15,1,android.util.TypedValue.COMPLEX_UNIT_SP);
    }
    void actionLabel(String label){setText(label);setContentDescription(label.isEmpty()?"回车":label);invalidate();}
    @Override protected void onDraw(Canvas canvas){
        if(getText().length()>0){super.onDraw(canvas);return;}
        int size=Math.min(WordtrailStyle.dp(getContext(),22),Math.min(getWidth(),getHeight())-8);
        int x=(getWidth()-size)/2,y=(getHeight()-size)/2;arrow.setBounds(x,y,x+size,y+size);arrow.draw(canvas);
    }
}
