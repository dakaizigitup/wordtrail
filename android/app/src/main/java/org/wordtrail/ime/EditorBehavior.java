package org.wordtrail.ime;

import android.icu.text.BreakIterator;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.util.Locale;

/** Editor actions and deletion are shared by Chinese, Latin and number pages. */
final class EditorBehavior {
    private EditorBehavior(){}
    static boolean hasAction(EditorInfo info){
        if(info==null || (info.imeOptions&EditorInfo.IME_FLAG_NO_ENTER_ACTION)!=0)return false;
        int action=info.imeOptions&EditorInfo.IME_MASK_ACTION;
        return info.actionLabel!=null&&info.actionLabel.length()>0 || action!=EditorInfo.IME_ACTION_NONE&&action!=EditorInfo.IME_ACTION_UNSPECIFIED;
    }
    static int actionId(EditorInfo info){return info.actionLabel!=null&&info.actionLabel.length()>0?info.actionId:info.imeOptions&EditorInfo.IME_MASK_ACTION;}
    static String label(EditorInfo info){
        if(!hasAction(info))return "";
        if(info.actionLabel!=null&&info.actionLabel.length()>0)return info.actionLabel.toString();
        switch(actionId(info)){
            case EditorInfo.IME_ACTION_SEARCH:return "搜索";
            case EditorInfo.IME_ACTION_SEND:return "发送";
            case EditorInfo.IME_ACTION_NEXT:return "下一项";
            case EditorInfo.IME_ACTION_PREVIOUS:return "上一项";
            case EditorInfo.IME_ACTION_GO:return "前往";
            case EditorInfo.IME_ACTION_DONE:return "完成";
            default:return "确认";
        }
    }
    static void enter(InputConnection connection,EditorInfo info){
        if(connection==null)return;
        if(hasAction(info))connection.performEditorAction(actionId(info));
        else connection.commitText("\n",1);
    }
    static void delete(InputConnection connection){
        if(connection==null)return;
        CharSequence selected=connection.getSelectedText(0);
        if(selected!=null&&selected.length()>0){connection.commitText("",1);return;}
        CharSequence before=connection.getTextBeforeCursor(128,0);
        if(before==null){
            connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_DEL));
            connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP,KeyEvent.KEYCODE_DEL));return;
        }
        if(before.length()==0)return;
        // A visible character can contain several Unicode code points (e.g. a family emoji).
        String text=before.toString();BreakIterator iterator=BreakIterator.getCharacterInstance(Locale.ROOT);iterator.setText(text);
        int boundary=iterator.preceding(text.length());
        if(boundary==BreakIterator.DONE)boundary=0;
        connection.deleteSurroundingText(text.length()-boundary,0);
    }
}
