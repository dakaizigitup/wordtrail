package org.wordtrail.ime;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.widget.Button;

/** Draw the icon at the button's center, independently of text/compound drawable layout. */
final class IconButton extends Button {
    private Drawable icon;
    IconButton(Context context,Drawable icon,String description){super(context);this.icon=icon;setContentDescription(description);}
    void setIcon(Drawable value){icon=value;invalidate();}
    @Override protected void onDraw(Canvas canvas){
        int size=Math.round(22*getResources().getDisplayMetrics().density);
        size=Math.min(size,Math.min(getWidth(),getHeight())-8);
        int x=(getWidth()-size)/2,y=(getHeight()-size)/2;
        icon.setBounds(x,y,x+size,y+size);icon.draw(canvas);
    }
}
