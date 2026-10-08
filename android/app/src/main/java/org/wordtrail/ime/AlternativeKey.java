package org.wordtrail.ime;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.ViewConfiguration;
import android.widget.Button;

/** A tap inputs the primary key; a hold exclusively selects an alternative. */
final class AlternativeKey extends Button {
    interface Listener {
        boolean open(AlternativeKey key);
        void move(float screenX,float screenY);
        void finish(float screenX,float screenY);
        void cancel(AlternativeKey key);
    }
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Listener listener;
    private final String hint;
    private final Paint hintPaint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private boolean tracking,opened,sliding;
    private float downX,downY;
    private final Runnable hold=()->{if(tracking && isPressed() && isEnabled())performLongClick();};

    AlternativeKey(Context context,String hint,int hintColor,Listener listener){
        super(context);this.hint=hint;this.listener=listener;
        hintPaint.setColor(hintColor);hintPaint.setTextAlign(Paint.Align.CENTER);
        hintPaint.setTextSize(9*getResources().getDisplayMetrics().scaledDensity);
        setLongClickable(true);
    }
    @Override public boolean onTouchEvent(MotionEvent event){
        if(!isEnabled())return false;
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                tracking=true;opened=false;sliding=false;downX=event.getRawX();downY=event.getRawY();setPressed(true);drawableHotspotChanged(event.getX(),event.getY());
                if(getParent()!=null)getParent().requestDisallowInterceptTouchEvent(true);
                handler.postDelayed(hold,ViewConfiguration.getLongPressTimeout());return true;
            case MotionEvent.ACTION_MOVE:
                if(opened){
                    if(Math.hypot(event.getRawX()-downX,event.getRawY()-downY)>WordtrailStyle.dp(getContext(),2))sliding=true;
                    if(sliding)listener.move(event.getRawX(),event.getRawY());
                }
                else if(event.getX()<0 || event.getX()>getWidth() || event.getY()<0 || event.getY()>getHeight()){
                    handler.removeCallbacks(hold);tracking=false;setPressed(false);
                }
                return true;
            case MotionEvent.ACTION_UP:
                handler.removeCallbacks(hold);boolean tap=tracking&&!opened;
                tracking=false;setPressed(false);
                if(getParent()!=null)getParent().requestDisallowInterceptTouchEvent(false);
                if(opened){opened=false;listener.finish(event.getRawX(),event.getRawY());}
                else if(tap)performClick();
                return true;
            case MotionEvent.ACTION_CANCEL:
                cancelGesture();return true;
            default:return true;
        }
    }
    @Override public boolean performLongClick(){
        handler.removeCallbacks(hold);opened=listener.open(this);
        if(opened)performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
        return opened;
    }
    private void cancelGesture(){
        handler.removeCallbacks(hold);tracking=false;opened=false;setPressed(false);listener.cancel(this);
        if(getParent()!=null)getParent().requestDisallowInterceptTouchEvent(false);
    }
    @Override protected void onDetachedFromWindow(){cancelGesture();super.onDetachedFromWindow();}
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);
        if(!hint.isEmpty())canvas.drawText(hint,getWidth()-WordtrailStyle.dp(getContext(),9),WordtrailStyle.dp(getContext(),11),hintPaint);
    }
    @Override public boolean performClick(){return super.performClick();}
}
