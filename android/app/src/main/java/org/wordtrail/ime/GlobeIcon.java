package org.wordtrail.ime;

import android.graphics.*;
import android.graphics.drawable.Drawable;

/** Original line icon, tinted with the current keyboard palette. */
final class GlobeIcon extends Drawable {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    GlobeIcon(int color){paint.setColor(color);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.5f);}
    @Override public void draw(Canvas canvas){Rect bounds=getBounds();canvas.save();canvas.translate(bounds.left,bounds.top);canvas.scale(bounds.width()/24f,bounds.height()/24f);canvas.drawCircle(12,12,9,paint);canvas.drawOval(new RectF(8,3,16,21),paint);canvas.drawLine(3,12,21,12,paint);canvas.restore();}
    @Override public void setAlpha(int alpha){paint.setAlpha(alpha);invalidateSelf();}
    @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);invalidateSelf();}
    @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
}
