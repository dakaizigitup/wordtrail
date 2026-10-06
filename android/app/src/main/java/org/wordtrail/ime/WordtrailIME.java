package org.wordtrail.ime;

import android.inputmethodservice.InputMethodService;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;
import org.json.*;
import java.io.File;
import java.util.concurrent.*;

public final class WordtrailIME extends InputMethodService {
    private final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private long handle;
    private volatile int epoch;
    private LinearLayout root, content, candidates, keys;
    private TextView status;
    private Button mode, language;
    private boolean numbers, upper, capsLock, forceLatin, privateInput, layoutEnglish;
    private boolean wide, compact;
    private int keyHeight=46, layoutWidth=-1;
    private long lastShiftTap;
    private String editorPackage;
    private int editorField, editorType, editorOptions;
    private JSONObject displayed;
    private String lastComposition = "";
    private boolean applying;
    private Runnable repeating;
    private WordtrailStyle palette;
    private HorizontalScrollView candidateScroll;
    private Button previousPage, nextPage;
    private Button themeButton;
    private TextView brand;
    private boolean themeChoicesOpen;
    private LinearLayout pronunciationPanel;
    private SpeechInput speech;
    private LocalSpeechInput localSpeech;
    private Button microphone, speechStop;
    private Button hideKeyboardButton;
    private LinearLayout speechPanel;
    private TextView speechTitle, speechPreview;
    private boolean speechShowing;
    private String speechLocale="zh-CN";
    private int speechToken;

    @Override public void onCreate() {
        super.onCreate();
        speech=new SpeechInput(this);
        localSpeech=new LocalSpeechInput(this);
        worker.execute(() -> {
            try {
                File data = DataFiles.prepare(this);
                JSONObject request = new JSONObject().put("op","create").put("data_dir",data.getAbsolutePath())
                    .put("user_dir",new File(getFilesDir(),"learning").getAbsolutePath())
                    .put("language",getSharedPreferences("settings",MODE_PRIVATE).getString("language","en"))
                    .put("vocabulary_targets",VocabularySettings.targets(this));
                JSONObject response = new JSONObject(NativeBridge.request(request.toString()));
                if (!response.isNull("error")) throw new Exception(response.getString("error"));
                handle = response.getLong("handle");
                int generation = epoch; JSONObject state = response.getJSONObject("state");
                main.post(() -> { if (generation == epoch) render(state); });
            } catch (Throwable error) { main.post(() -> { if(status!=null) status.setText("词库加载失败，请重新打开词伴"); }); }
        });
        worker.scheduleWithFixedDelay(() -> { if(handle!=0) call(new JSONObject(),"flush",epoch); },5,5,TimeUnit.SECONDS);
    }

    @Override public View onCreateInputView() {
        closeSpeech(false);
        palette=WordtrailStyle.load(this);
        layoutWidth=-1;
        root = new LinearLayout(this){
            @Override protected void onMeasure(int widthSpec,int heightSpec){
                int available=View.MeasureSpec.getSize(widthSpec)-getPaddingLeft()-getPaddingRight();
                if(available>0 && available!=layoutWidth){
                    layoutWidth=available;wide=available>=dp(600);compact=getResources().getConfiguration().screenHeightDp<500;
                    keyHeight=compact?38:wide?52:46;
                    content.getLayoutParams().width=Math.min(available,dp(1000));
                    if(keys!=null)buildKeys();
                    if(displayed!=null)render(displayed,false);
                }
                super.onMeasure(widthSpec,heightSpec);
            }
        };
        root.setOrientation(LinearLayout.VERTICAL);root.setGravity(Gravity.CENTER_HORIZONTAL);root.setContentDescription("词伴键盘");root.setBackground(palette.shape(this,palette.background,0,18));root.setPadding(dp(6),dp(6),dp(6),dp(6));
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);root.addView(content,new LinearLayout.LayoutParams(-1,-2));
        if(getWindow()!=null && getWindow().getWindow()!=null){getWindow().getWindow().setNavigationBarColor(palette.background);getWindow().getWindow().getDecorView().setSystemUiVisibility(palette.id.equals("night")?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);}
        if(android.os.Build.VERSION.SDK_INT>=30) {
            root.setOnApplyWindowInsetsListener((view,insets) -> {
                int bottom=insets.getInsets(WindowInsets.Type.navigationBars()).bottom;
                view.setPadding(dp(6),dp(6),dp(6),dp(6)+bottom);
                return insets;
            });
            root.requestApplyInsets();
        }
        LinearLayout toolbar = row();
        brand=new TextView(this);brand.setText("词伴");brand.setTextSize(13);brand.setTextColor(palette.accent);brand.setGravity(Gravity.CENTER);brand.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));toolbar.addView(brand,new LinearLayout.LayoutParams(dp(44),dp(34)));
        status=new TextView(this);status.setText("正在准备词库…");status.setTextSize(11);status.setSingleLine(true);status.setEllipsize(android.text.TextUtils.TruncateAt.END);status.setTextColor(palette.muted);status.setGravity(Gravity.CENTER_VERTICAL);status.setPadding(dp(8),0,dp(4),0);toolbar.addView(status,new LinearLayout.LayoutParams(0,dp(34),1));
        language = control("EN 译词", v -> cycleLanguage()); toolbar.addView(language,toolbarSize(84));
        microphone=iconButton(new KeyboardIcon(KeyboardIcon.MICROPHONE,palette.accent,false),"语音输入",v -> {if(speechShowing)closeSpeech(true);else requestSpeech();});palette.style(microphone,palette.background,palette.accent,10,false);toolbar.addView(microphone,toolbarSize(34));
        themeButton=control("◐",v->chooseTheme(v));themeButton.setContentDescription("切换主题");toolbar.addView(themeButton,toolbarSize(38));
        previousPage=control("‹", v -> action("previous_page",null));toolbar.addView(previousPage,toolbarSize(32));
        nextPage=control("›", v -> action("next_page",null));toolbar.addView(nextPage,toolbarSize(32));
        hideKeyboardButton=iconButton(new KeyboardIcon(KeyboardIcon.HIDE,palette.ink,false),"收起键盘",v -> {closeSpeech(true);requestHideSelf(0);});palette.style(hideKeyboardButton,palette.background,palette.ink,10,false);toolbar.addView(hideKeyboardButton,toolbarSize(28));
        content.addView(toolbar);
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setFillViewport(true);candidateScroll.setHorizontalScrollBarEnabled(false);candidateScroll.setClipToPadding(false);candidateScroll.setPadding(dp(2),0,dp(2),dp(4));
        candidates = row(); candidateScroll.addView(candidates); candidateScroll.setVisibility(View.GONE);content.addView(candidateScroll,new LinearLayout.LayoutParams(-1,dp(46)));
        speechPanel=new LinearLayout(this);speechPanel.setOrientation(LinearLayout.VERTICAL);speechPanel.setPadding(dp(8),0,dp(8),dp(4));speechPanel.setVisibility(View.GONE);content.addView(speechPanel,new LinearLayout.LayoutParams(-1,dp(72)));
        pronunciationPanel=new LinearLayout(this);pronunciationPanel.setOrientation(LinearLayout.VERTICAL);pronunciationPanel.setVisibility(View.GONE);content.addView(pronunciationPanel,new LinearLayout.LayoutParams(-1,-2));
        keys = new LinearLayout(this); keys.setOrientation(LinearLayout.VERTICAL); content.addView(keys); buildKeys();
        if(displayed!=null) render(displayed,false); else action("state",null);
        return root;
    }

    @Override public void onStartInput(EditorInfo info, boolean restarting) {
        super.onStartInput(info,restarting);
        boolean sameEditor=restarting && displayed!=null && java.util.Objects.equals(editorPackage,info.packageName) && editorField==info.fieldId && editorType==info.inputType && editorOptions==info.imeOptions;
        if(sameEditor){if(keys!=null)buildKeys();action("state",null);return;}
        closeSpeech(false);
        editorPackage=info.packageName;editorField=info.fieldId;editorType=info.inputType;editorOptions=info.imeOptions;
        epoch++; lastComposition=""; displayed=null; upper=false;capsLock=false;
        int variation = info.inputType & InputType.TYPE_MASK_VARIATION;
        int klass = info.inputType & InputType.TYPE_MASK_CLASS;
        privateInput = (klass == InputType.TYPE_CLASS_TEXT && (variation==InputType.TYPE_TEXT_VARIATION_PASSWORD || variation==InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD || variation==InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD))
            || (klass==InputType.TYPE_CLASS_NUMBER && variation==InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        numbers = klass==InputType.TYPE_CLASS_NUMBER || klass==InputType.TYPE_CLASS_PHONE || klass==InputType.TYPE_CLASS_DATETIME;
        forceLatin = privateInput || numbers || (klass==InputType.TYPE_CLASS_TEXT && (variation==InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS || variation==InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS || variation==InputType.TYPE_TEXT_VARIATION_URI));
        try { JSONObject reset=new JSONObject().put("private",privateInput || (info.imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING)!=0); action("reset",reset);
            action("language",new JSONObject().put("language",getSharedPreferences("settings",MODE_PRIVATE).getString("language","en")));
        } catch(JSONException ignored) {}
        if(keys!=null) buildKeys();
    }
    @Override public void onStartInputView(EditorInfo info,boolean restarting){super.onStartInputView(info,restarting);if(palette!=null && !palette.id.equals(WordtrailStyle.load(this).id))applyTheme();else if(displayed!=null && !speechShowing)render(displayed,false);try{action("vocabulary",new JSONObject().put("vocabulary_targets",VocabularySettings.targets(this)));}catch(JSONException ignored){}}

    @Override public void onFinishInput() {
        closeSpeech(false);
        epoch++; lastComposition=""; stopRepeat(); action("flush",null); action("reset",null); super.onFinishInput();
    }
    @Override public void onFinishInputView(boolean finishingInput){closeSpeech(false);super.onFinishInputView(finishingInput);}
    @Override public void onUpdateSelection(int oldStart,int oldEnd,int newStart,int newEnd,int candidatesStart,int candidatesEnd) {
        super.onUpdateSelection(oldStart,oldEnd,newStart,newEnd,candidatesStart,candidatesEnd);
        if(!applying && speechShowing && (newStart!=oldStart || newEnd!=oldEnd))closeSpeech(true);
        if (!applying && !lastComposition.isEmpty() && (newStart!=candidatesEnd || newEnd!=candidatesEnd)) {
            epoch++; lastComposition=""; action("reset",null);
            InputConnection connection=getCurrentInputConnection(); if(connection!=null) connection.finishComposingText();
        }
    }
    @Override public void onDestroy() {
        closeSpeech(false);
        if(localSpeech!=null)localSpeech.destroy();
        epoch++; stopRepeat();
        worker.execute(() -> { if(handle!=0) { call(new JSONObject(),"destroy",epoch); handle=0; }});
        worker.shutdown(); super.onDestroy();
    }
    @Override public boolean onEvaluateFullscreenMode() { return false; }
    @Override public void onConfigureWindow(Window window,boolean fullscreen,boolean candidatesOnly){
        super.onConfigureWindow(window,fullscreen,candidatesOnly);
        if(!fullscreen){
            // Keep the input surface stable when candidates/details appear.
            // A WRAP_CONTENT window resize can interrupt a rapid touch sequence.
            window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT);
            window.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        }
    }
    @Override public void onComputeInsets(Insets out){
        super.onComputeInsets(out);
        if(root==null || !isInputViewShown())return;
        int[] location=new int[2];root.getLocationInWindow(location);
        out.contentTopInsets=location[1];out.visibleTopInsets=location[1];
        out.touchableInsets=Insets.TOUCHABLE_INSETS_REGION;
        // The transparent area above the keyboard belongs to the host app.
        out.touchableRegion.set(location[0],location[1],location[0]+root.getWidth(),location[1]+root.getHeight());
    }
    @Override public void setInputView(View view){
        super.setInputView(view);
        if(view.getLayoutParams() instanceof FrameLayout.LayoutParams){
            FrameLayout.LayoutParams params=(FrameLayout.LayoutParams)view.getLayoutParams();
            params.gravity=Gravity.BOTTOM;view.setLayoutParams(params);
        }
        // The framework inputArea is inside its vertical parentPanel. Anchor
        // that panel to the bottom of the stable, transparent window as well.
        if(view.getParent() instanceof View && ((View)view.getParent()).getParent() instanceof LinearLayout){
            LinearLayout panel=(LinearLayout)((View)view.getParent()).getParent();
            ViewGroup.LayoutParams params=panel.getLayoutParams();params.height=ViewGroup.LayoutParams.MATCH_PARENT;
            panel.setLayoutParams(params);panel.setGravity(Gravity.BOTTOM);
        }
    }

    private void action(String op,JSONObject fields) {
        int generation=epoch; JSONObject request=fields==null ? new JSONObject() : fields;
        worker.execute(() -> call(request,op,generation));
    }
    private void call(JSONObject request,String op,int generation) {
        if(handle==0) return;
        try {
            request.put("op",op).put("handle",handle);
            JSONObject response=new JSONObject(NativeBridge.request(request.toString()));
            if(!response.isNull("error")) { if(!op.equals("flush")) main.post(() -> { if(generation==epoch && status!=null) status.setText("候选已更新，请重新选择"); }); return; }
            JSONObject state=response.optJSONObject("state");
            if(state!=null && !op.equals("flush")) main.post(() -> { if(generation==epoch) render(state); });
        } catch(Exception error) { main.post(() -> { if(generation==epoch && status!=null) status.setText("暂时无法生成候选，请切换键盘后重试"); }); }
    }

    private void render(JSONObject state) {
        render(state,true);
    }
    private void render(JSONObject state,boolean applyDocumentChange) {
        if(root==null) return;
        themeChoicesOpen=false;
        pronunciationPanel.setVisibility(View.GONE);pronunciationPanel.removeAllViews();
        displayed=state;
        InputConnection connection=getCurrentInputConnection();
        String commit=state.optString("commit",""); if(state.isNull("commit")) commit="";
        String input=state.optString("input","");
        applying=true;
        try {
            if(connection!=null && applyDocumentChange) {
                connection.beginBatchEdit();
                if(!commit.isEmpty()) {
                    EditorInfo info=getCurrentInputEditorInfo();
                    int editorAction=info==null ? EditorInfo.IME_ACTION_NONE : info.imeOptions & EditorInfo.IME_MASK_ACTION;
                    if(commit.equals("\n") && info!=null && (info.imeOptions & EditorInfo.IME_FLAG_NO_ENTER_ACTION)==0 && editorAction!=EditorInfo.IME_ACTION_NONE && editorAction!=EditorInfo.IME_ACTION_UNSPECIFIED) connection.performEditorAction(editorAction);
                    else connection.commitText(commit,1);
                }
                if(state.optBoolean("delete_backward")) connection.deleteSurroundingTextInCodePoints(1,0);
                if(!input.isEmpty() && !forceLatin) connection.setComposingText(input,1);
                else if(!lastComposition.isEmpty() && commit.isEmpty()) connection.setComposingText("",1);
                if(input.isEmpty()) connection.finishComposingText();
                connection.endBatchEdit();
            }
        } finally { applying=false; }
        if(applyDocumentChange) lastComposition=input;
        if(layoutEnglish!=isEnglish())buildKeys();
        updateMode();
        updateMicrophone();
        language.setText(state.optString("language","en").toUpperCase()+" 译词");
        String preedit=state.optString("preedit","");
        status.setText(forceLatin ? privateInput ? "私密输入 · 不学习" : "直接输入 · EN" : preedit.isEmpty() ? isEnglish()?"英文输入":"拼音输入" : preedit+"    "+(state.optInt("page")+1)+"/"+state.optInt("page_count",1));
        status.setVisibility(View.VISIBLE);
        previousPage.setEnabled(state.optInt("page")>0);nextPage.setEnabled(state.optInt("page")+1<state.optInt("page_count"));previousPage.setAlpha(previousPage.isEnabled()?1:.3f);nextPage.setAlpha(nextPage.isEnabled()?1:.3f);
        if(speechShowing){setSpeechControls(true);return;}
        candidates.removeAllViews(); JSONArray list=state.optJSONArray("candidates");
        boolean hasCandidates=list!=null && list.length()>0 && !forceLatin;
        candidateScroll.setVisibility(hasCandidates?View.VISIBLE:View.GONE);
        candidates.setGravity(Gravity.CENTER_VERTICAL);
        if(!hasCandidates)return;
        int cellWidth=candidateWidth();
        long revision=state.optLong("revision");
        for(int i=0;i<list.length();i++) {
            JSONObject candidate=list.optJSONObject(i); if(candidate==null) continue;
            int index=candidate.optInt("id");
            LinearLayout cell=new LinearLayout(this); cell.setOrientation(LinearLayout.VERTICAL); cell.setGravity(Gravity.CENTER); cell.setPadding(dp(4),dp(2),dp(4),dp(2));cell.setBackground(palette.shape(this,i==0?palette.soft:palette.background,0,10));
            LinearLayout heading=row();heading.setGravity(Gravity.CENTER_VERTICAL);
            TextView word=new TextView(this); word.setText(candidate.optString("text"));word.setIncludeFontPadding(false);word.setTextSize(compact?16:wide?18:17);word.setSingleLine(true);word.setEllipsize(android.text.TextUtils.TruncateAt.END);word.setTextColor(i==0?palette.accent:palette.ink);word.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));word.setGravity(Gravity.CENTER);heading.addView(word,new LinearLayout.LayoutParams(0,dp(26),1));
            LinearLayout detailSlot=new LinearLayout(this);detailSlot.setOrientation(LinearLayout.VERTICAL);detailSlot.setGravity(Gravity.CENTER);detailSlot.setContentDescription("查看"+candidate.optString("text")+"的音标和释义");detailSlot.setOnClickListener(v->showPronunciation(candidate));
            TextView detail=new TextView(this);detail.setText("▾");detail.setIncludeFontPadding(false);detail.setTextSize(10);detail.setTextColor(palette.muted);detail.setGravity(Gravity.CENTER);detailSlot.addView(detail,new LinearLayout.LayoutParams(dp(16),dp(26)));heading.addView(detailSlot,new LinearLayout.LayoutParams(dp(16),dp(26)));cell.addView(heading,new LinearLayout.LayoutParams(-1,dp(26)));
            LinearLayout translationRow=row();translationRow.setGravity(Gravity.CENTER_VERTICAL);
            JSONArray senses=candidate.optJSONArray("translation_senses");JSONObject firstSense=senses==null?null:senses.optJSONObject(0);
            TextView gloss=new TextView(this);gloss.setText(firstSense==null || !state.optString("language").equals("en")?candidate.optString("annotation"):firstSense.optString("text"));gloss.setIncludeFontPadding(false);gloss.setTextSize(10);gloss.setSingleLine(true);gloss.setEllipsize(android.text.TextUtils.TruncateAt.END);gloss.setGravity(Gravity.CENTER);gloss.setTextColor((firstSense==null?candidate.optBoolean("fresh"):firstSense.optBoolean("fresh"))?palette.fresh:palette.muted);translationRow.addView(gloss,new LinearLayout.LayoutParams(0,-2,1));
            JSONArray tags=firstSense==null?null:firstSense.optJSONArray("tags");
            if(tags!=null && tags.length()>0 && getSharedPreferences("settings",MODE_PRIVATE).getBoolean("show_vocabulary_tags",true)){
                TextView tagBadge=new TextView(this);int count=cellWidth>=dp(105)?Math.min(2,tags.length()):1;StringBuilder title=new StringBuilder();boolean preferred=false;
                for(int t=0;t<count;t++){JSONObject tag=tags.optJSONObject(t);if(tag==null)continue;if(t>0)title.append("/");title.append(VocabularySettings.shortLabel(tag.optString("id")));preferred|=tag.optBoolean("selected");}
                if(tags.length()>count)title.append("+").append(tags.length()-count);
                tagBadge.setText(title);tagBadge.setTextSize(7.5f);tagBadge.setIncludeFontPadding(false);tagBadge.setSingleLine(true);tagBadge.setPadding(dp(2),0,dp(2),0);tagBadge.setGravity(Gravity.CENTER);tagBadge.setTextColor(preferred?palette.accent:palette.muted);tagBadge.setBackground(palette.shape(this,palette.soft,0,4));
                tagBadge.setContentDescription(firstSense.optString("text")+" · 考试标签 "+tagLabels(tags));tagBadge.setOnClickListener(v->showPronunciation(candidate));LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-2,dp(13));bp.leftMargin=dp(2);translationRow.addView(tagBadge,bp);
            }
            String level=firstLevel(candidate);
            boolean showLevel=!level.isEmpty() && getSharedPreferences("settings",MODE_PRIVATE).getBoolean("show_word_levels",true);
            if(showLevel){
                TextView badge=new TextView(this);badge.setText(level);badge.setIncludeFontPadding(false);badge.setTextSize(9);badge.setGravity(Gravity.CENTER);badge.setTextColor(palette.accent);badge.setBackground(palette.shape(this,palette.soft,0,4));
                JSONArray entries=candidate.optJSONArray("vocabulary_levels");String translated=entries.optJSONObject(0).optString("word");badge.setContentDescription(translated+" · CEFR "+level);badge.setTextSize(8);detailSlot.removeAllViews();detailSlot.addView(badge,new LinearLayout.LayoutParams(dp(16),dp(12)));detailSlot.addView(detail,new LinearLayout.LayoutParams(dp(16),dp(11)));
            }
            cell.addView(translationRow,new LinearLayout.LayoutParams(-1,dp(14)));
            cell.setContentDescription(candidate.optString("text")+" "+candidate.optString("annotation")+(showLevel?" · CEFR "+level:""));
            cell.setOnClickListener(v -> select("select",index,revision));
            cell.setOnLongClickListener(v -> { if(candidate.optString("annotation").isEmpty()) return false; select("translation",index,revision); return true; });
            cell.setOnTouchListener(new View.OnTouchListener(){float startX,startY;boolean dragged;
                @Override public boolean onTouch(View view,MotionEvent event){
                    if(event.getAction()==MotionEvent.ACTION_DOWN){startX=event.getX();startY=event.getY();dragged=false;return false;}
                    if(event.getAction()==MotionEvent.ACTION_MOVE && event.getY()-startY>dp(16) && event.getY()-startY>Math.abs(event.getX()-startX)*1.2f){dragged=true;view.cancelLongPress();view.setPressed(false);view.getParent().requestDisallowInterceptTouchEvent(true);return true;}
                    if(event.getAction()==MotionEvent.ACTION_UP && dragged){showPronunciation(candidate);return true;}
                    return dragged;
                }
            });
            LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(cellWidth,-1);cp.setMargins(dp(2),0,dp(2),0);candidates.addView(cell,cp);
        }
    }
    private int candidateWidth(){
        // Size from the measured keyboard, including split-screen and capped tablet widths.
        int available=Math.min(layoutWidth>0?layoutWidth:getResources().getDisplayMetrics().widthPixels-dp(12),dp(1000))-dp(4);
        int visible=Math.min(9,Math.max(3,available/dp(70)));
        return Math.max(dp(48),available/visible-dp(4));
    }
    private void select(String op,int index,long revision) { try {action(op,new JSONObject().put("index",index).put("revision",revision));} catch(JSONException ignored) {} }
    private String firstLevel(JSONObject candidate){
        JSONArray entries=candidate.optJSONArray("vocabulary_levels");JSONObject entry=entries==null?null:entries.optJSONObject(0);
        String level=entry==null || entry.isNull("level")?"":entry.optString("level","");
        return level.matches("[ABC][12]")?level:"";
    }
    private String levelMeaning(String level){
        switch(level){case "A1":return "入门";case "A2":return "基础";case "B1":return "中级";case "B2":return "中高级";case "C1":return "高级";case "C2":return "高阶";default:return "未收录（不代表难度）";}
    }
    private String tagLabels(JSONArray tags){StringBuilder labels=new StringBuilder();if(tags!=null)for(int i=0;i<tags.length();i++){JSONObject tag=tags.optJSONObject(i);if(tag!=null){if(labels.length()>0)labels.append(" · ");labels.append(tag.optString("label"));}}return labels.toString();}
    private void showPronunciation(JSONObject candidate){
        pronunciationPanel.removeAllViews();pronunciationPanel.setBackground(palette.shape(this,palette.surface,palette.line,12));
        LinearLayout header=row();header.setGravity(Gravity.CENTER_VERTICAL);header.setPadding(dp(12),0,dp(4),0);
        JSONObject pronunciation=candidate.optJSONObject("pronunciation");String word=pronunciation==null?candidate.optString("text"):pronunciation.optString("word");
        TextView title=new TextView(this);title.setText(word+" · "+(pronunciation==null?"释义":"音标"));title.setTextColor(palette.accent);title.setTextSize(12);title.setSingleLine(true);title.setEllipsize(android.text.TextUtils.TruncateAt.END);header.addView(title,new LinearLayout.LayoutParams(0,dp(28),1));
        Button close=control("收起",v -> {pronunciationPanel.setVisibility(View.GONE);pronunciationPanel.removeAllViews();});close.setContentDescription("收起音标详情");header.addView(close,new LinearLayout.LayoutParams(dp(54),dp(28)));pronunciationPanel.addView(header);
        ScrollView scroll=new ScrollView(this);scroll.setFocusable(false);scroll.setVerticalScrollBarEnabled(true);scroll.setFillViewport(false);
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(12),0,dp(12),dp(10));
        TextView gloss=detailLine(candidate.optString("annotation"));body.addView(gloss);
        JSONArray senses=candidate.optJSONArray("translation_senses");
        if(senses!=null)for(int i=0;i<senses.length();i++){
            JSONObject sense=senses.optJSONObject(i);if(sense==null)continue;JSONArray tags=sense.optJSONArray("tags");
            String tagDescription=displayed.optString("language").equals("en")?" · "+(tags==null || tags.length()==0?"暂无考试标签":tagLabels(tags)):"";
            TextView entry=detailLine(sense.optString("text")+tagDescription);entry.setTextColor(palette.accent);body.addView(entry);
            java.util.LinkedHashSet<String> sources=new java.util.LinkedHashSet<>();if(tags!=null)for(int t=0;t<tags.length();t++){JSONArray names=tags.optJSONObject(t).optJSONArray("sources");if(names!=null)for(int n=0;n<names.length();n++)sources.add(names.optString(n));}
            if(!sources.isEmpty()){TextView source=detailLine("词表来源："+String.join(" / ",sources));source.setTextSize(10);source.setTextColor(palette.muted);body.addView(source);}
            JSONObject ipa=sense.optJSONObject("pronunciation");if(ipa!=null){if(!ipa.isNull("uk"))body.addView(detailLine("英式  "+ipa.optString("uk")));if(!ipa.isNull("us"))body.addView(detailLine("美式  "+ipa.optString("us")));}
            final int senseIndex=sense.optInt("index",i);Button insert=control("输入译词 "+sense.optString("text"),v->{try{action("translation",new JSONObject().put("index",candidate.optInt("id")).put("sense_index",senseIndex).put("revision",displayed.optLong("revision")));}catch(JSONException ignored){}});insert.setTextSize(12);body.addView(insert,new LinearLayout.LayoutParams(-1,dp(40)));
        }
        JSONArray entries=candidate.optJSONArray("vocabulary_levels");
        if(entries!=null && entries.length()>0){
            TextView heading=detailLine("词汇参考等级 · CEFR");heading.setTextColor(palette.accent);body.addView(heading);
            for(int i=0;i<entries.length();i++){JSONObject entry=entries.optJSONObject(i);if(entry==null)continue;String level=entry.isNull("level")?"":entry.optString("level","");body.addView(detailLine(entry.optString("word")+" · "+(level.isEmpty()?levelMeaning(""):level+" "+levelMeaning(level))));}
            TextView note=detailLine("按英文译词标注；不是个人水平或六级、雅思等级。");note.setTextSize(11);note.setTextColor(palette.muted);body.addView(note);
        }
        if(pronunciation!=null && (senses==null || senses.length()==0)){
            String uk=pronunciation.isNull("uk")?"":pronunciation.optString("uk","");String us=pronunciation.isNull("us")?"":pronunciation.optString("us","");
            if(!uk.isEmpty())body.addView(detailLine("英式  "+uk));
            if(!us.isEmpty())body.addView(detailLine("美式  "+us));
        }
        scroll.addView(body);pronunciationPanel.addView(scroll,new LinearLayout.LayoutParams(-1,dp(compact?64:80)));pronunciationPanel.setVisibility(View.VISIBLE);
    }
    private TextView detailLine(String text){TextView label=new TextView(this);label.setText(text);label.setTextSize(13);label.setTextColor(palette.ink);label.setPadding(0,dp(3),0,dp(3));label.setLineSpacing(dp(2),1);return label;}
    private void cycleLanguage() {
        closeSpeech(true);
        String current=getSharedPreferences("settings",MODE_PRIVATE).getString("language","en"); String next=current.equals("en")?"ja":current.equals("ja")?"es":"en";
        getSharedPreferences("settings",MODE_PRIVATE).edit().putString("language",next).apply();
        try {action("language",new JSONObject().put("language",next));} catch(JSONException ignored) {}
    }
    private void key(String value) {
        if(speechShowing)return;
        if(forceLatin) { InputConnection connection=getCurrentInputConnection(); if(connection!=null) connection.commitText(value,1); return; }
        try {action("key",new JSONObject().put("text",value));} catch(JSONException ignored) {}
    }
    private boolean isEnglish(){return forceLatin || displayed!=null && displayed.optBoolean("english");}
    private void toggleMode(){if(forceLatin)return;upper=false;capsLock=false;action("toggle",null);}
    private void updateMode(){
        if(mode==null)return;
        boolean english=isEnglish();
        android.text.SpannableString label=new android.text.SpannableString("中/英");
        label.setSpan(new android.text.style.ForegroundColorSpan(english?palette.muted:palette.accent),0,1,0);
        label.setSpan(new android.text.style.ForegroundColorSpan(english?palette.accent:palette.muted),2,3,0);
        mode.setText(label);mode.setContentDescription("切换中英文，当前"+(english?"英文":"中文"));mode.setEnabled(!forceLatin);mode.setAlpha(forceLatin?.45f:1f);
    }
    private void shift(){
        long now=android.os.SystemClock.uptimeMillis();
        if(upper && now-lastShiftTap<350){capsLock=true;upper=true;}
        else{upper=!upper;capsLock=false;}
        lastShiftTap=now;
        if(upper && !isEnglish())action("toggle",null);
        buildKeys();
    }
    private void buildKeys() {
        stopRepeat();layoutEnglish=isEnglish();
        keys.removeAllViews(); String[] rows=numbers ? new String[]{"1234567890","-/:;()&@\"",".,?!'"} : new String[]{"qwertyuiop","asdfghjkl","zxcvbnm"};
        for(int i=0;i<rows.length;i++) { LinearLayout row=row();if(i==1 && !numbers)row.setPadding(dp(wide?46:16),0,dp(wide?46:16),0); if(i==2){Button shift=iconButton(new KeyboardIcon(KeyboardIcon.SHIFT,upper?palette.onAccent:palette.ink,capsLock),capsLock?"大写锁定":upper?"大写已开启":"大写",v -> shift());if(upper)palette.style(shift,palette.accent,palette.onAccent,10,false);row.addView(shift,weight(1.3f));}
            for(char letter:rows[i].toCharArray()) { String value=String.valueOf(letter); Button button=typingButton(numbers?value:layoutEnglish && !upper?value:value.toUpperCase(),v -> {
                key(upper && isEnglish()?value.toUpperCase():value);
                if(upper && !capsLock && Character.isLetter(letter)){upper=false;buildKeys();}
            }); row.addView(button,weight(1)); }
            if(i==2) { Button back=iconButton(new KeyboardIcon(KeyboardIcon.BACKSPACE,palette.ink,false),"删除",v -> backspace()); back.setOnTouchListener((v,event) -> { if(event.getAction()==MotionEvent.ACTION_DOWN) {v.setPressed(true);v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP); backspace(); repeating=new Runnable(){public void run(){backspace();main.postDelayed(repeating,65);}}; main.postDelayed(repeating,400); } else if(event.getAction()==MotionEvent.ACTION_UP || event.getAction()==MotionEvent.ACTION_CANCEL){v.setPressed(false);stopRepeat();} return true; }); row.addView(back,weight(1.3f)); }
            keys.addView(row);
        }
        LinearLayout bottom=row(); Button symbols=button(numbers?"ABC":"123",v -> { numbers=!numbers; buildKeys(); });symbols.setTextSize(14);bottom.addView(symbols,weight(1.25f));
        mode=button("中/英",v -> toggleMode());mode.setTextSize(12);bottom.addView(mode,weight(1.4f));updateMode();
        bottom.addView(typingButton(layoutEnglish?",":"，",v -> key(",")),weight(1));
        Button globe=iconButton(new GlobeIcon(palette.ink),"切换键盘",v -> ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());bottom.addView(globe,weight(.7f));
        Button space=typingButton("空格",v -> {if(forceLatin) key(" ");else action("space",null);});palette.style(space,palette.key,palette.muted,10,true);space.setTextSize(14);bottom.addView(space,weight(3.5f));
        bottom.addView(typingButton(layoutEnglish?".":"。",v -> key(".")),weight(.7f));
        Button enter=iconButton(new KeyboardIcon(KeyboardIcon.ENTER,palette.onAccent,false),"回车",v -> {if(forceLatin) key("\n");else action("enter",null);});palette.style(enter,palette.accent,palette.onAccent,10,false);bottom.addView(enter,weight(1.3f)); keys.addView(bottom);
        if(speechShowing)setSpeechControls(true);
    }
    private void updateMicrophone(){
        if(microphone==null)return;boolean available=!privateInput && !numbers;
        microphone.setEnabled(available);microphone.setAlpha(available?1:.3f);
        microphone.setContentDescription(speechShowing?"关闭语音输入":"语音输入");
    }
    private void setSpeechControls(boolean blocked){
        if(keys!=null)for(int i=0;i<keys.getChildCount();i++){View row=keys.getChildAt(i);if(row instanceof android.view.ViewGroup){android.view.ViewGroup group=(android.view.ViewGroup)row;for(int j=0;j<group.getChildCount();j++){View key=group.getChildAt(j);key.setEnabled(!blocked);key.setAlpha(blocked?.45f:1);}}}
        if(keys!=null)keys.setAlpha(1);
        if(hideKeyboardButton!=null){hideKeyboardButton.setEnabled(true);hideKeyboardButton.setAlpha(1);}
        updateMode();
        if(blocked && mode!=null){mode.setEnabled(false);mode.setAlpha(.45f);}
        if(language!=null)language.setEnabled(!blocked);if(themeButton!=null)themeButton.setEnabled(!blocked);
        if(previousPage!=null)previousPage.setEnabled(!blocked && displayed!=null && displayed.optInt("page")>0);
        if(nextPage!=null)nextPage.setEnabled(!blocked && displayed!=null && displayed.optInt("page")+1<displayed.optInt("page_count"));
        updateMicrophone();
    }
    private void closeSpeech(boolean restore){
        speechToken++;if(speech!=null)speech.cancel();if(localSpeech!=null)localSpeech.cancel();speechShowing=false;
        if(speechPanel!=null){speechPanel.setVisibility(View.GONE);speechPanel.removeAllViews();}
        if(candidateScroll!=null)candidateScroll.setVisibility(displayed!=null && !forceLatin && displayed.optJSONArray("candidates")!=null && displayed.optJSONArray("candidates").length()>0?View.VISIBLE:View.GONE);setSpeechControls(false);
        if(restore && displayed!=null && root!=null)render(displayed,false);
    }
    private boolean canDictate(){
        if(privateInput || numbers || getCurrentInputConnection()==null)return false;
        if(displayed==null){Toast.makeText(this,"键盘正在准备，请稍后再试",Toast.LENGTH_SHORT).show();return false;}
        if(!displayed.optString("input","").isEmpty()){Toast.makeText(this,"先选词或清空当前拼音，再开始语音",Toast.LENGTH_SHORT).show();return false;}
        return true;
    }
    private void requestSpeech(){
        if(!canDictate())return;
        if(useLocalSpeech()){
            if(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=android.content.pm.PackageManager.PERMISSION_GRANTED){
                startActivity(new android.content.Intent(this,SpeechPermissionActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));return;
            }
            beginSpeech(true);return;
        }
        boolean offline=SpeechInput.offlineAvailable(this);
        if(!offline && !SpeechInput.systemAvailable(this)){showSpeechNotice("没有可启动的系统服务",SpeechServices.description(this),false);return;}
        if(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=android.content.pm.PackageManager.PERMISSION_GRANTED){
            startActivity(new android.content.Intent(this,SpeechPermissionActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));return;
        }
        if(offline)beginSpeech(true);
        else if(getSharedPreferences("settings",MODE_PRIVATE).getBoolean("speech_allow_system",false))beginSpeech(false);
        else offerSystemSpeech("设备离线识别不可用");
    }
    private void revealSpeechPanel(){
        stopRepeat();themeChoicesOpen=false;speechShowing=true;
        candidateScroll.setVisibility(View.GONE);speechPanel.setVisibility(View.VISIBLE);speechPanel.removeAllViews();
        pronunciationPanel.setVisibility(View.GONE);pronunciationPanel.removeAllViews();setSpeechControls(true);
    }
    private void showSpeechNotice(String title,String subtitle,boolean canUseSystem){
        revealSpeechPanel();
        TextView message=detailLine(title+" · "+subtitle);message.setTextSize(11);message.setMaxLines(2);speechPanel.addView(message,new LinearLayout.LayoutParams(-1,dp(32)));
        LinearLayout choices=row();
        Button proceed=control(canUseSystem?"使用系统语音":"语音设置",v->{
            if(canUseSystem){getSharedPreferences("settings",MODE_PRIVATE).edit().putBoolean("speech_allow_system",true).apply();closeSpeech(false);if(canDictate())beginSpeech(false);}
            else openSpeechSettings();
        });palette.style(proceed,palette.soft,palette.accent,10,false);choices.addView(proceed,new LinearLayout.LayoutParams(0,dp(34),1));
        Button back=control("返回键盘",v->closeSpeech(true));choices.addView(back,new LinearLayout.LayoutParams(dp(90),dp(34)));speechPanel.addView(choices);
    }
    private void offerSystemSpeech(String reason){showSpeechNotice(reason,"系统语音服务可能联网处理录音",true);}
    private void openSpeechSettings(){closeSpeech(true);startActivity(new android.content.Intent(this,SpeechSettingsActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));}
    private void showSpeechFailure(int code,boolean offline){
        String service=useLocalSpeech()?"词伴本机离线识别":offline?"设备离线识别":SpeechServices.description(this);
        String error=SpeechInput.errorMessage(code)+"（"+code+"）";
        getSharedPreferences("settings",MODE_PRIVATE).edit().putString("speech_last_error",error+" · "+service).apply();
        closeSpeech(false);revealSpeechPanel();
        TextView message=detailLine(error+"\n"+service);message.setTextSize(10);message.setMaxLines(2);message.setEllipsize(android.text.TextUtils.TruncateAt.END);speechPanel.addView(message,new LinearLayout.LayoutParams(-1,dp(32)));
        LinearLayout choices=row();
        Button settings=control("语音设置",v->openSpeechSettings());choices.addView(settings,new LinearLayout.LayoutParams(0,dp(34),1));
        Button picker=control("切换输入法",v->{closeSpeech(true);((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker();});choices.addView(picker,new LinearLayout.LayoutParams(0,dp(34),1));
        Button back=control("返回键盘",v->closeSpeech(true));choices.addView(back,new LinearLayout.LayoutParams(0,dp(34),1));speechPanel.addView(choices);
    }
    private void beginSpeech(boolean offline){
        if(!canDictate())return;
        final boolean local=useLocalSpeech();
        revealSpeechPanel();speechLocale=isEnglish()?"en-US":"zh-CN";
        speechTitle=detailLine((speechLocale.equals("zh-CN")?"中文":"英文")+(local?" · 本机离线，录音不上网":offline?" · 设备离线识别":" · 系统语音服务，可能联网"));speechTitle.setTextSize(11);speechTitle.setPadding(0,0,0,0);speechPanel.addView(speechTitle,new LinearLayout.LayoutParams(-1,dp(22)));
        LinearLayout line=row();speechPreview=detailLine("正在打开麦克风…");speechPreview.setTextSize(14);speechPreview.setMaxLines(2);speechPreview.setEllipsize(android.text.TextUtils.TruncateAt.END);line.addView(speechPreview,new LinearLayout.LayoutParams(0,dp(44),1));
        speechStop=control("完成",v->{if(local)localSpeech.stop();else speech.stop();});speechStop.setEnabled(!local);speechStop.setContentDescription("停止录音并识别");palette.style(speechStop,palette.soft,palette.accent,10,false);line.addView(speechStop,new LinearLayout.LayoutParams(dp(52),dp(34)));
        Button cancel=control("取消",v->closeSpeech(true));cancel.setContentDescription("取消语音输入");line.addView(cancel,new LinearLayout.LayoutParams(dp(52),dp(34)));speechPanel.addView(line);
        final int token=++speechToken;final int editorGeneration=epoch;
        // Drain pending native key actions before deciding the composing buffer is empty.
        worker.execute(()->main.post(()->{
            if(token!=speechToken || editorGeneration!=epoch || !isInputViewShown())return;
            if(!canDictate()){closeSpeech(true);return;}
            SpeechInput.Listener listener=new SpeechInput.Listener(){
                private boolean valid(){return token==speechToken && editorGeneration==epoch && isInputViewShown();}
                @Override public void ready(){if(valid()){speechPreview.setText("请说话…");speechStop.setEnabled(true);}}
                @Override public void partial(String text){if(valid())speechPreview.setText(text);}
                @Override public void waiting(){if(valid()){speechPreview.setText("正在识别…");speechStop.setEnabled(false);}}
                @Override public void result(String text){
                    if(!valid())return;closeSpeech(true);InputConnection connection=getCurrentInputConnection();if(connection==null)return;
                    applying=true;try{connection.beginBatchEdit();connection.commitText(text,1);connection.finishComposingText();connection.endBatchEdit();}finally{applying=false;}
                }
                @Override public void error(int code){
                    if(!valid())return;
                    if(!local && offline && code!=android.speech.SpeechRecognizer.ERROR_NO_MATCH && code!=android.speech.SpeechRecognizer.ERROR_SPEECH_TIMEOUT && code!=android.speech.SpeechRecognizer.ERROR_AUDIO && code!=android.speech.SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS && SpeechInput.systemAvailable(WordtrailIME.this)){
                        if(getSharedPreferences("settings",MODE_PRIVATE).getBoolean("speech_allow_system",false)){closeSpeech(false);beginSpeech(false);}
                        else offerSystemSpeech("离线识别暂不可用");
                    }
                    else showSpeechFailure(code,offline);
                }
            };
            if(local)localSpeech.start(speechLocale,listener);else speech.start(offline,speechLocale,listener);
        }));
    }
    private boolean useLocalSpeech(){return !getSharedPreferences("settings",MODE_PRIVATE).getString("speech_engine","local").equals("system");}
    private void backspace(){if(forceLatin){InputConnection c=getCurrentInputConnection();if(c!=null)c.deleteSurroundingTextInCodePoints(1,0);}else action("backspace",null);}
    private void stopRepeat(){if(repeating!=null){main.removeCallbacks(repeating);repeating=null;}}
    private int dp(float value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private LinearLayout row(){LinearLayout view=new LinearLayout(this);view.setOrientation(LinearLayout.HORIZONTAL);view.setBaselineAligned(false);view.setGravity(Gravity.CENTER_VERTICAL);return view;}
    private LinearLayout.LayoutParams weight(float value){LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,dp(keyHeight),value);int margin=dp(wide?4:3);params.setMargins(margin,dp(3),margin,dp(3));return params;}
    private LinearLayout.LayoutParams toolbarSize(int width){return new LinearLayout.LayoutParams(dp(width),dp(34));}
    private Button button(String label,View.OnClickListener listener){return styleButton(new Button(this),label,listener);}
    private Button typingButton(String label,View.OnClickListener listener){return styleButton(new TypingKey(this),label,listener);}
    private Button styleButton(Button b,String label,View.OnClickListener listener){b.setText(label);b.setGravity(Gravity.CENTER);b.setIncludeFontPadding(false);boolean letter=label.matches("[a-zA-Z0-9]");b.setTextSize(letter?compact?19:wide?23:21:17);palette.style(b,letter?palette.key:palette.function,palette.ink,10,letter);palette.feedback(b);b.setOnClickListener(listener);return b;}
    private Button iconButton(android.graphics.drawable.Drawable icon,String description,View.OnClickListener listener){Button b=new IconButton(this,icon,description);palette.style(b,palette.function,palette.ink,10,false);palette.feedback(b);b.setOnClickListener(listener);return b;}
    private Button control(String label,View.OnClickListener listener){Button b=button(label,listener);b.setTextSize(label.equals("◐")||label.equals("‹")||label.equals("›")?20:12);palette.style(b,palette.background,palette.muted,10,false);return b;}
    private void applyTheme(){
        stopRepeat();palette=WordtrailStyle.load(this);
        root.setBackground(palette.shape(this,palette.background,0,18));brand.setTextColor(palette.accent);status.setTextColor(palette.muted);
        for(Button item:new Button[]{language,themeButton,previousPage,nextPage})palette.style(item,palette.background,palette.muted,10,false);
        if(microphone instanceof IconButton){((IconButton)microphone).setIcon(new KeyboardIcon(KeyboardIcon.MICROPHONE,palette.accent,false));palette.style(microphone,palette.background,palette.accent,10,false);}
        if(hideKeyboardButton instanceof IconButton){((IconButton)hideKeyboardButton).setIcon(new KeyboardIcon(KeyboardIcon.HIDE,palette.ink,false));palette.style(hideKeyboardButton,palette.background,palette.ink,10,false);}
        if(getWindow()!=null && getWindow().getWindow()!=null){getWindow().getWindow().setNavigationBarColor(palette.background);getWindow().getWindow().getDecorView().setSystemUiVisibility(palette.id.equals("night")?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);}
        buildKeys();if(displayed!=null)render(displayed,false);
    }
    private void chooseTheme(View anchor){
        pronunciationPanel.setVisibility(View.GONE);pronunciationPanel.removeAllViews();
        if(themeChoicesOpen){themeChoicesOpen=false;if(displayed!=null)render(displayed,false);return;}
        themeChoicesOpen=true;candidates.removeAllViews();status.setText("选择主题  ·  点 ◐ 返回候选");candidateScroll.setVisibility(View.VISIBLE);candidateScroll.scrollTo(0,0);
        String[] ids={"jade","lavender","night"};String[] names={"青绿","粉紫","深色"};
        int width=Math.max(dp(70),(candidateScroll.getWidth()-dp(16))/3);
        for(int i=0;i<ids.length;i++){
            final String id=ids[i];Button choice=button(names[i],v->{getSharedPreferences("settings",MODE_PRIVATE).edit().putString("theme",id).apply();themeChoicesOpen=false;applyTheme();});
            choice.setTextSize(14);palette.style(choice,id.equals(palette.id)?palette.soft:palette.surface,id.equals(palette.id)?palette.accent:palette.muted,12,false);
            LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(width,-1);params.setMargins(dp(2),0,dp(2),0);candidates.addView(choice,params);
        }
    }
}
