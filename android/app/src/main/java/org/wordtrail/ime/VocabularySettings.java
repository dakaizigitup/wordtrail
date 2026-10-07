package org.wordtrail.ime;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;

/** Stable IDs shared with Rust. Empty selection means all translations, original order. */
final class VocabularySettings {
    static final int EXAM_COUNT=6;
    static final String[] IDS={"cet4","cet6","tem4","tem8","toefl","ielts","computer","business","medical","administration","education"};
    static final String[] LABELS={"四级","六级","专四","专八","托福","雅思","计算机","商务","医学","行政学","教育"};
    private VocabularySettings(){}
    static JSONArray targets(Context context){
        int mask=context.getSharedPreferences("settings",Context.MODE_PRIVATE).getInt("vocabulary_targets",0);
        JSONArray ids=new JSONArray();for(int i=0;i<IDS.length;i++)if((mask&(1<<i))!=0)ids.put(IDS[i]);return ids;
    }
    static String shortLabel(String id){
        switch(id){case "cet4":return "四";case "cet6":return "六";case "tem4":return "专4";case "tem8":return "专8";case "toefl":return "托";case "ielts":return "雅";case "computer":return "计";case "business":return "商";case "medical":return "医";case "administration":return "行";case "education":return "教";default:return "";}
    }
}
