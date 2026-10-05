package org.wordtrail.ime;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.content.res.ColorStateList;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.widget.Button;

final class WordtrailStyle {
    final String id;
    final int background, surface, key, function, accent, ink, muted, line, soft, fresh, onAccent;
    WordtrailStyle(String name) {
        id=name.equals("lavender") || name.equals("night") ? name : "jade";
        if(id.equals("night")) {
            background=c("#18231F");surface=c("#22312A");key=c("#2C3B33");function=c("#394A40");accent=c("#A9D4B5");ink=c("#ECF3ED");muted=c("#AFBFB3");line=c("#3C4C42");soft=c("#304A39");fresh=c("#EDB883");onAccent=c("#193724");
        } else if(id.equals("lavender")) {
            background=c("#F4EFF7");surface=c("#FFFCFF");key=c("#FFFCFF");function=c("#E7DEF0");accent=c("#78568F");ink=c("#382C43");muted=c("#80738C");line=c("#E3D9EA");soft=c("#EDE2F4");fresh=c("#AD652E");onAccent=Color.WHITE;
        } else {
            background=c("#EEF4EF");surface=c("#FBFEFB");key=c("#FEFFFD");function=c("#DDE9E0");accent=c("#2C684D");ink=c("#24392D");muted=c("#738577");line=c("#D7E4DA");soft=c("#E0EFE3");fresh=c("#B46528");onAccent=Color.WHITE;
        }
    }
    static int c(String hex){return Color.parseColor(hex);}
    static WordtrailStyle load(Context c){return new WordtrailStyle(c.getSharedPreferences("settings",Context.MODE_PRIVATE).getString("theme","jade"));}
    static int dp(Context c,float value){return Math.round(value*c.getResources().getDisplayMetrics().density);}
    GradientDrawable shape(Context c,int fill,int stroke,float radius){GradientDrawable shape=new GradientDrawable();shape.setColor(fill);shape.setCornerRadius(dp(c,radius));if(stroke!=0)shape.setStroke(dp(c,1),stroke);return shape;}
    void style(Button button,int fill,int text,float radius,boolean raised){Context c=button.getContext();button.setAllCaps(false);button.setMinWidth(0);button.setMinimumWidth(0);button.setMinHeight(0);button.setMinimumHeight(0);button.setPadding(0,0,0,0);button.setTextColor(text);button.setTypeface(Typeface.create("sans-serif",Typeface.NORMAL));button.setStateListAnimator(null);button.setElevation(raised?dp(c,1):0);button.setBackground(new RippleDrawable(ColorStateList.valueOf(id.equals("night")?0x28ffffff:0x18366148),shape(c,fill,0,radius),null));}
    void feedback(Button button){button.setOnTouchListener((view,event)->{if(event.getAction()==MotionEvent.ACTION_DOWN){view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);if(!(button instanceof TypingKey))view.animate().scaleX(.96f).scaleY(.96f).setDuration(70).start();}else if(event.getAction()==MotionEvent.ACTION_UP || event.getAction()==MotionEvent.ACTION_CANCEL){if(!(button instanceof TypingKey))view.animate().scaleX(1).scaleY(1).setDuration(100).start();}return false;});}
}
