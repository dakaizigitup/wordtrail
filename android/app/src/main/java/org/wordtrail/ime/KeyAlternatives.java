package org.wordtrail.ime;

import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.PopupWindow;
import java.util.function.Consumer;

/** Non-focusable popup keeps the editor active and supports slide-and-release. */
final class KeyAlternatives {
    private PopupWindow popup;
    private View owner;
    private LinearLayout strip;
    private Button[] buttons;
    private String[] values;
    private Consumer<String> commit;
    private WordtrailStyle palette;
    private int selected,left,top,width,height,ownerBottom;
    private boolean slid;

    boolean show(View anchor,View keyboard,String[] choices,int defaultIndex,WordtrailStyle style,Consumer<String> onSelect){
        dismiss();if(!anchor.isAttachedToWindow() || keyboard.getWindowToken()==null)return false;
        owner=anchor;palette=style;values=choices;commit=onSelect;selected=defaultIndex;slid=false;
        strip=new LinearLayout(anchor.getContext());strip.setOrientation(LinearLayout.HORIZONTAL);strip.setGravity(Gravity.CENTER_VERTICAL);
        strip.setPadding(dp(4),dp(4),dp(4),dp(4));strip.setContentDescription("按键长按选项");
        strip.setBackground(palette.shape(anchor.getContext(),palette.surface,palette.line,10));
        int[] keyLocation=new int[2],keyboardLocation=new int[2];anchor.getLocationOnScreen(keyLocation);keyboard.getLocationOnScreen(keyboardLocation);
        width=Math.min(keyboard.getWidth()-dp(12),dp(choices.length*44+8));height=dp(54);
        left=Math.max(keyboardLocation[0]+dp(6),Math.min(keyLocation[0]+anchor.getWidth()/2-(defaultIndex*2+1)*(width-dp(8))/(choices.length*2)-dp(4),keyboardLocation[0]+keyboard.getWidth()-width-dp(6)));
        top=Math.max(keyboardLocation[1],keyLocation[1]-height-dp(3));ownerBottom=keyLocation[1]+anchor.getHeight();
        buttons=new Button[choices.length];
        for(int i=0;i<choices.length;i++){
            final int index=i;Button b=new Button(anchor.getContext());b.setText(choices[i]);b.setContentDescription("长按选项 "+choices[i]);
            b.setMaxLines(1);b.setAutoSizeTextTypeUniformWithConfiguration(12,22,1,android.util.TypedValue.COMPLEX_UNIT_SP);
            b.setOnClickListener(v->choose(index));buttons[i]=b;strip.addView(b,new LinearLayout.LayoutParams(0,-1,1));
        }
        repaint();popup=new PopupWindow(strip,width,height,false);popup.setInputMethodMode(PopupWindow.INPUT_METHOD_NOT_NEEDED);
        popup.setAttachedInDecor(false);
        if(android.os.Build.VERSION.SDK_INT>=29){popup.setIsLaidOutInScreen(true);popup.setIsClippedToScreen(true);}
        popup.setOutsideTouchable(true);popup.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(android.graphics.Color.TRANSPARENT));popup.setElevation(dp(6));popup.setAnimationStyle(0);
        popup.setOnDismissListener(()->{popup=null;owner=null;});
        try{popup.showAtLocation(keyboard,Gravity.TOP|Gravity.LEFT,left,top);return true;}
        catch(android.view.WindowManager.BadTokenException error){dismiss();return false;}
    }
    boolean isOpen(){return popup!=null&&popup.isShowing();}
    void move(float x,float y){if(!isOpen())return;slid=true;int next=hit(x,y);if(next!=selected){selected=next;repaint();}}
    void finish(float x,float y){if(!isOpen())return;int index=!slid&&onOwner(x,y)?selected:hit(x,y);if(index>=0)choose(index);else dismiss();}
    void cancel(View anchor){if(owner==anchor)dismiss();}
    void dismiss(){PopupWindow current=popup;popup=null;owner=null;if(current!=null)current.dismiss();}
    private int hit(float x,float y){
        int[] position=new int[2];strip.getLocationOnScreen(position);left=position[0];top=position[1];width=strip.getWidth();height=strip.getHeight();
        if(x<left || x>=left+width || y<top-dp(12) || y>ownerBottom+dp(16))return -1;
        // Staying on the original key keeps the highlighted default option.
        if(y>=top+height && owner!=null){View area=ownerArea();int[] point=new int[2];area.getLocationOnScreen(point);if(x>=point[0] && x<=point[0]+area.getWidth())return selected;}
        return Math.min(values.length-1,Math.max(0,(int)((x-left-dp(4))*values.length/(width-dp(8)))));
    }
    private View ownerArea(){return owner!=null && owner.getParent() instanceof KeyHitBox?(View)owner.getParent():owner;}
    private boolean onOwner(float x,float y){View area=ownerArea();if(area==null)return false;int[] point=new int[2];area.getLocationOnScreen(point);return x>=point[0]&&x<=point[0]+area.getWidth()&&y>=point[1]&&y<=point[1]+area.getHeight();}
    private void choose(int index){String value=values[index];Consumer<String> callback=commit;buttons[index].performHapticFeedback(android.view.HapticFeedbackConstants.KEYBOARD_TAP);dismiss();callback.accept(value);}
    private void repaint(){for(int i=0;i<buttons.length;i++)palette.style(buttons[i],i==selected?palette.accent:palette.surface,i==selected?palette.onAccent:palette.ink,7,false);}
    private int dp(float value){return WordtrailStyle.dp(strip.getContext(),value);}
}
