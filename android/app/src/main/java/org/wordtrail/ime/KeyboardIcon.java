package org.wordtrail.ime;

import android.graphics.*;
import android.graphics.drawable.Drawable;

/** Original, font-independent keyboard symbols on a consistent 24-unit grid. */
final class KeyboardIcon extends Drawable {
    static final int SHIFT=0, BACKSPACE=1, ENTER=2, MICROPHONE=3, HIDE=4;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final int kind;
    private final boolean locked;
    KeyboardIcon(int kind,int color,boolean locked){this.kind=kind;this.locked=locked;paint.setColor(color);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.7f);paint.setStrokeJoin(Paint.Join.ROUND);paint.setStrokeCap(Paint.Cap.ROUND);}
    @Override public void draw(Canvas canvas){
        Rect bounds=getBounds();canvas.save();canvas.translate(bounds.left,bounds.top);canvas.scale(bounds.width()/24f,bounds.height()/24f);
        Path path=new Path();
        if(kind==SHIFT){
            path.moveTo(12,3);path.lineTo(3,12);path.lineTo(8,12);path.lineTo(8,20);path.lineTo(16,20);path.lineTo(16,12);path.lineTo(21,12);path.close();
            canvas.drawPath(path,paint);
            if(locked)canvas.drawLine(8,23,16,23,paint);
        }else if(kind==BACKSPACE){
            path.moveTo(8,5);path.lineTo(21,5);path.lineTo(21,19);path.lineTo(8,19);path.lineTo(2,12);path.close();canvas.drawPath(path,paint);
            canvas.drawLine(11,9,17,15,paint);canvas.drawLine(17,9,11,15,paint);
        }else if(kind==MICROPHONE){
            canvas.drawRoundRect(9,3,15,15,3,3,paint);
            path.moveTo(5,11);path.lineTo(5,13);path.cubicTo(5,22,19,22,19,13);path.lineTo(19,11);canvas.drawPath(path,paint);
            canvas.drawLine(12,20,12,23,paint);canvas.drawLine(8,23,16,23,paint);
        }else if(kind==HIDE){
            path.moveTo(5,9);path.lineTo(12,15);path.lineTo(19,9);canvas.drawPath(path,paint);
        }else{
            path.moveTo(20,5);path.lineTo(20,13);path.lineTo(5,13);path.moveTo(10,8);path.lineTo(5,13);path.lineTo(10,18);canvas.drawPath(path,paint);
        }
        canvas.restore();
    }
    @Override public void setAlpha(int alpha){paint.setAlpha(alpha);invalidateSelf();}
    @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);invalidateSelf();}
    @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
}
