package org.wordtrail.ime;

import android.content.Context;
import android.view.MotionEvent;
import android.widget.Button;

/** Keyboard keys respond on press; release/cancel never duplicates a character. */
final class TypingKey extends Button {
    TypingKey(Context context){super(context);}
    @Override public boolean onTouchEvent(MotionEvent event){
        if(!isEnabled())return super.onTouchEvent(event);
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                setPressed(true);drawableHotspotChanged(event.getX(),event.getY());
                getParent().requestDisallowInterceptTouchEvent(true);
                performClick();return true;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                setPressed(false);if(getParent()!=null)getParent().requestDisallowInterceptTouchEvent(false);return true;
            default:return true;
        }
    }
    @Override public boolean performClick(){return super.performClick();}
}
