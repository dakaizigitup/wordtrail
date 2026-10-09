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
    private final KeyAlternatives keyAlternatives=new KeyAlternatives();
    private android.content.SharedPreferences settings;
    private final android.content.SharedPreferences.OnSharedPreferenceChangeListener settingsListener=(prefs,key)->settingsChanged(key);
    private long handle;
    private volatile int epoch;
    private LinearLayout root, content, candidates, keys;
    private FrameLayout keyboardBody;
    private LinearLayout candidateBar, expandedPanel, nineReadings;
    private TextView status;
    private Button mode, language;
    private EnterKey enterKey;
    private boolean numericEditor, symbolPage, greekPage, greekUpper;
    private boolean numbers, upper, capsLock, forceLatin, privateInput, layoutEnglish;
    private boolean nineKey;
    private boolean panelBackHandled;
    private boolean requestedCandidateExpanded;
    private int candidateLayoutPending;
    private boolean wide, compact;
    private int keyHeight=46, layoutWidth=-1;
    private int navBottomInset;
    private long lastShiftTap;
    private String editorPackage;
    private int editorField, editorType, editorOptions;
    private JSONObject displayed;
    private String lastComposition = "";
    private boolean applying;
    private Runnable repeating;
    private WordtrailStyle palette;
    private HorizontalScrollView candidateScroll;
    private Button previousPage, nextPage, candidateExpandButton, layoutButton;
    private LinearLayout expandedCandidateArea, expandedCandidates, readingChoices;
    private ScrollView expandedCandidateScroll, readingScroll;
    private ScrollView nineReadingScroll;
    private String readingProgressSignature="";
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
        settings=getSharedPreferences("settings",MODE_PRIVATE);settings.registerOnSharedPreferenceChangeListener(settingsListener);
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
        nineKey=getSharedPreferences("settings",MODE_PRIVATE).getString("keyboard_layout","qwerty").equals("nine");
        layoutWidth=-1;
        root = new LinearLayout(this){
            @Override protected void onMeasure(int widthSpec,int heightSpec){
                int available=View.MeasureSpec.getSize(widthSpec)-getPaddingLeft()-getPaddingRight();
                if(available>0 && available!=layoutWidth){
                    layoutWidth=available;wide=available>=dp(600);compact=getResources().getConfiguration().screenHeightDp<500;
                    String height=getSharedPreferences("settings",MODE_PRIVATE).getString("keyboard_height","standard");
                    keyHeight=height.equals("tall")?(compact?44:wide?58:52):height.equals("compact")?(compact?34:wide?46:40):(compact?38:wide?52:46);
                    content.getLayoutParams().width=Math.min(available,dp(900));
                    if(keys!=null)buildKeys();
                    if(displayed!=null)render(displayed,false);
                }
                super.onMeasure(widthSpec,heightSpec);
            }
        };
        root.setOrientation(LinearLayout.VERTICAL);root.setGravity(Gravity.CENTER_HORIZONTAL);root.setContentDescription("词伴键盘");root.setBackground(palette.shape(this,palette.background,0,18));root.setPadding(dp(6),dp(6),dp(6),dp(6)+keyboardLift());
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);root.addView(content,new LinearLayout.LayoutParams(-1,-2));
        if(getWindow()!=null && getWindow().getWindow()!=null){getWindow().getWindow().setNavigationBarColor(palette.background);getWindow().getWindow().getDecorView().setSystemUiVisibility(palette.id.equals("night")?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);}
        if(android.os.Build.VERSION.SDK_INT>=30) {
            root.setOnApplyWindowInsetsListener((view,insets) -> {
                navBottomInset=insets.getInsets(WindowInsets.Type.navigationBars()).bottom;
                view.setPadding(dp(6),dp(6),dp(6),dp(6)+navBottomInset+keyboardLift());
                return insets;
            });
            root.requestApplyInsets();
        }
        LinearLayout toolbar = row();
        brand=new TextView(this);brand.setText("词伴");brand.setTextSize(13);brand.setTextColor(palette.accent);brand.setGravity(Gravity.CENTER);brand.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));toolbar.addView(brand,new LinearLayout.LayoutParams(dp(40),dp(44)));
        status=new TextView(this);status.setText("正在准备词库…");status.setTextSize(11);status.setSingleLine(true);status.setEllipsize(android.text.TextUtils.TruncateAt.END);status.setTextColor(palette.muted);status.setGravity(Gravity.CENTER_VERTICAL);status.setPadding(dp(8),0,dp(4),0);toolbar.addView(status,new LinearLayout.LayoutParams(0,dp(44),1));
        brand.setContentDescription("打开词伴设置");brand.setOnClickListener(v->startActivity(new android.content.Intent(this,MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)));
        language = control("EN 译词", v -> cycleLanguage()); toolbar.addView(language,toolbarSize(58));
        microphone=iconButton(new KeyboardIcon(KeyboardIcon.MICROPHONE,palette.accent,false),"语音输入",v -> {if(speechShowing)closeSpeech(true);else requestSpeech();});palette.style(microphone,palette.background,palette.accent,10,false);toolbar.addView(microphone,toolbarSize(44));
        layoutButton=control("九键",v->switchLayout());toolbar.addView(layoutButton,toolbarSize(44));
        themeButton=control("◐",v->chooseTheme(v));themeButton.setContentDescription("切换主题");toolbar.addView(themeButton,toolbarSize(36));
        hideKeyboardButton=iconButton(new KeyboardIcon(KeyboardIcon.HIDE,palette.ink,false),"收起键盘",v -> {closeSpeech(true);requestHideSelf(0);});palette.style(hideKeyboardButton,palette.background,palette.ink,10,false);toolbar.addView(hideKeyboardButton,toolbarSize(44));
        content.addView(toolbar);
        candidateBar=row();candidateBar.setVisibility(View.GONE);content.addView(candidateBar,new LinearLayout.LayoutParams(-1,dp(candidateHeight())));
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setFillViewport(true);candidateScroll.setHorizontalScrollBarEnabled(false);
        candidates = row(); candidateScroll.addView(candidates);candidateBar.addView(candidateScroll,new LinearLayout.LayoutParams(0,-1,1));
        candidateExpandButton=control("⌄",v->toggleCandidateLayout());candidateExpandButton.setTextSize(24);candidateExpandButton.setContentDescription("展开全部候选并隐藏键盘");candidateBar.addView(candidateExpandButton,new LinearLayout.LayoutParams(dp(44),-1));
        keyboardBody=new FrameLayout(this);content.addView(keyboardBody,new LinearLayout.LayoutParams(-1,dp(keyboardHeight())));
        expandedPanel=new LinearLayout(this);expandedPanel.setOrientation(LinearLayout.VERTICAL);expandedPanel.setVisibility(View.GONE);keyboardBody.addView(expandedPanel,new FrameLayout.LayoutParams(-1,-1));
        expandedCandidateArea=row();expandedCandidateArea.setGravity(Gravity.TOP);expandedCandidateArea.setVisibility(View.GONE);
        readingScroll=new ScrollView(this);readingScroll.setVerticalScrollBarEnabled(false);readingScroll.setFillViewport(true);readingChoices=new LinearLayout(this);readingChoices.setOrientation(LinearLayout.VERTICAL);readingChoices.setPadding(0,0,dp(4),0);readingScroll.addView(readingChoices);expandedCandidateArea.addView(readingScroll,new LinearLayout.LayoutParams(dp(62),-1));
        expandedCandidateScroll=new ScrollView(this);expandedCandidateScroll.setVerticalScrollBarEnabled(true);expandedCandidateScroll.setFillViewport(false);expandedCandidates=new LinearLayout(this);expandedCandidates.setOrientation(LinearLayout.VERTICAL);expandedCandidateScroll.addView(expandedCandidates);expandedCandidateArea.addView(expandedCandidateScroll,new LinearLayout.LayoutParams(0,-1,1));
        expandedPanel.addView(expandedCandidateArea,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout candidateActions=row();previousPage=control("上一页",v->action("previous_page",null));nextPage=control("下一页",v->action("next_page",null));candidateActions.addView(previousPage,new LinearLayout.LayoutParams(0,dp(44),1));candidateActions.addView(nextPage,new LinearLayout.LayoutParams(0,dp(44),1));candidateActions.addView(backspaceButton(),new LinearLayout.LayoutParams(dp(52),dp(40)));Button backToKeys=control("返回键盘",v->requestCandidateLayout(false));backToKeys.setContentDescription("收起候选并显示键盘");candidateActions.addView(backToKeys,new LinearLayout.LayoutParams(dp(92),dp(44)));expandedPanel.addView(candidateActions);
        speechPanel=new LinearLayout(this);speechPanel.setOrientation(LinearLayout.VERTICAL);speechPanel.setGravity(Gravity.CENTER_VERTICAL);speechPanel.setPadding(dp(12),dp(12),dp(12),dp(12));speechPanel.setVisibility(View.GONE);keyboardBody.addView(speechPanel,new FrameLayout.LayoutParams(-1,-1));
        pronunciationPanel=new LinearLayout(this);pronunciationPanel.setOrientation(LinearLayout.VERTICAL);pronunciationPanel.setVisibility(View.GONE);keyboardBody.addView(pronunciationPanel,new FrameLayout.LayoutParams(-1,-1));
        keys = new LinearLayout(this); keys.setOrientation(LinearLayout.VERTICAL); keyboardBody.addView(keys,new FrameLayout.LayoutParams(-1,-1)); buildKeys();
        if(displayed!=null) render(displayed,false); else action("state",null);
        return root;
    }

    @Override public void onStartInput(EditorInfo info, boolean restarting) {
        super.onStartInput(info,restarting);
        boolean sameEditor=restarting && displayed!=null && java.util.Objects.equals(editorPackage,info.packageName) && editorField==info.fieldId && editorType==info.inputType && editorOptions==info.imeOptions;
        if(sameEditor){if(keys!=null)buildKeys();action("state",null);return;}
        closeSpeech(false);
        editorPackage=info.packageName;editorField=info.fieldId;editorType=info.inputType;editorOptions=info.imeOptions;
        epoch++; lastComposition=""; displayed=null; candidateLayoutPending=0;requestedCandidateExpanded=false; upper=false;capsLock=false;
        int variation = info.inputType & InputType.TYPE_MASK_VARIATION;
        int klass = info.inputType & InputType.TYPE_MASK_CLASS;
        privateInput = (klass == InputType.TYPE_CLASS_TEXT && (variation==InputType.TYPE_TEXT_VARIATION_PASSWORD || variation==InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD || variation==InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD))
            || (klass==InputType.TYPE_CLASS_NUMBER && variation==InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        numericEditor=klass==InputType.TYPE_CLASS_NUMBER || klass==InputType.TYPE_CLASS_PHONE || klass==InputType.TYPE_CLASS_DATETIME;
        numbers=numericEditor;symbolPage=false;greekPage=false;
        forceLatin = privateInput || numbers || (klass==InputType.TYPE_CLASS_TEXT && (variation==InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS || variation==InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS || variation==InputType.TYPE_TEXT_VARIATION_URI));
        try { JSONObject reset=new JSONObject().put("private",privateInput || (info.imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING)!=0); action("reset",reset);
            action("language",new JSONObject().put("language",getSharedPreferences("settings",MODE_PRIVATE).getString("language","en")));
        } catch(JSONException ignored) {}
        if(keys!=null) buildKeys();
    }
    @Override public void onStartInputView(EditorInfo info,boolean restarting){
        super.onStartInputView(info,restarting);refreshKeyboardSettings();
        if(palette!=null && !palette.id.equals(WordtrailStyle.load(this).id))applyTheme();
        try{action("vocabulary",new JSONObject().put("vocabulary_targets",VocabularySettings.targets(this)));}catch(JSONException ignored){}
    }
    private void refreshKeyboardSettings(){
        if(root==null || keys==null)return;
        boolean newNine=settings.getString("keyboard_layout","qwerty").equals("nine");boolean layoutChanged=newNine!=nineKey;
        String height=settings.getString("keyboard_height","standard");
        int preferred=height.equals("tall")?(compact?44:wide?58:52):height.equals("compact")?(compact?34:wide?46:40):(compact?38:wide?52:46);
        boolean heightChanged=preferred!=keyHeight;nineKey=newNine;keyHeight=preferred;
        root.setPadding(dp(6),dp(6),dp(6),dp(6)+navBottomInset+keyboardLift());
        if(layoutChanged){numbers=numericEditor;symbolPage=false;greekPage=false;action("clear",null);}
        if(layoutChanged || heightChanged)buildKeys();
        if(displayed!=null && !speechShowing)render(displayed,false);
        root.requestLayout();
    }
    private void settingsChanged(String key){
        if(root==null)return;
        if(key==null || key.equals("keyboard_layout") || key.equals("keyboard_height") || key.equals("keyboard_bottom_gap")){refreshKeyboardSettings();return;}
        if(key.equals("theme")){if(!palette.id.equals(WordtrailStyle.load(this).id))applyTheme();return;}
        try{
            if(key.equals("language"))action("language",new JSONObject().put("language",settings.getString("language","en")));
            else if(key.equals("vocabulary_targets"))action("vocabulary",new JSONObject().put("vocabulary_targets",VocabularySettings.targets(this)));
            else if(key.equals("show_vocabulary_tags") && displayed!=null)render(displayed,false);
            else if(key.equals("nine_reading_steps")){
                if(displayed!=null && displayed.optString("input").matches("[2-9]+"))action("keypad_reading",new JSONObject().put("reading",""));
                else if(displayed!=null)render(displayed,false);
            }
            else if(key.equals("speech_engine") && speechShowing)closeSpeech(true);
        }catch(JSONException ignored){}
    }

    @Override public void onFinishInput() {
        closeSpeech(false);
        epoch++; lastComposition=""; stopRepeat(); action("flush",null); action("reset",null); super.onFinishInput();
    }
    @Override public void onFinishInputView(boolean finishingInput){stopRepeat();keyAlternatives.dismiss();closeSpeech(false);super.onFinishInputView(finishingInput);}
    @Override public void onUpdateSelection(int oldStart,int oldEnd,int newStart,int newEnd,int candidatesStart,int candidatesEnd) {
        super.onUpdateSelection(oldStart,oldEnd,newStart,newEnd,candidatesStart,candidatesEnd);
        if(!applying && speechShowing && (newStart!=oldStart || newEnd!=oldEnd))closeSpeech(true);
        if (!applying && !lastComposition.isEmpty() && (newStart!=candidatesEnd || newEnd!=candidatesEnd)) {
            epoch++; lastComposition="";
            try{action("reset",new JSONObject().put("private",privateInput || (editorOptions&EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING)!=0));}catch(JSONException ignored){}
            InputConnection connection=getCurrentInputConnection(); if(connection!=null) connection.finishComposingText();
        }
    }
    @Override public void onDestroy() {
        if(settings!=null)settings.unregisterOnSharedPreferenceChangeListener(settingsListener);
        keyAlternatives.dismiss();
        closeSpeech(false);
        if(localSpeech!=null)localSpeech.destroy();
        epoch++; stopRepeat();
        worker.execute(() -> { if(handle!=0) { call(new JSONObject(),"destroy",epoch); handle=0; }});
        worker.shutdown(); super.onDestroy();
    }
    @Override public boolean onEvaluateFullscreenMode() { return false; }
    @Override public boolean onKeyDown(int keyCode,KeyEvent event){
        if(keyCode==KeyEvent.KEYCODE_BACK && event.getRepeatCount()==0){
            panelBackHandled=false;
            if(keyAlternatives.isOpen()){keyAlternatives.dismiss();panelBackHandled=true;}
            else if(speechShowing){closeSpeech(true);panelBackHandled=true;}
            else if(pronunciationPanel!=null&&pronunciationPanel.getVisibility()==View.VISIBLE){render(displayed,false);panelBackHandled=true;}
            else if(expandedPanel!=null&&expandedPanel.getVisibility()==View.VISIBLE){requestCandidateLayout(false);panelBackHandled=true;}
            if(panelBackHandled)return true;
        }
        return super.onKeyDown(keyCode,event);
    }
    @Override public boolean onKeyUp(int keyCode,KeyEvent event){if(keyCode==KeyEvent.KEYCODE_BACK&&panelBackHandled){panelBackHandled=false;return true;}return super.onKeyUp(keyCode,event);}
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
    private void toggleCandidateLayout(){
        boolean current=candidateLayoutPending>0?requestedCandidateExpanded:displayed!=null&&displayed.optBoolean("expanded");
        requestCandidateLayout(!current);
    }
    private void requestCandidateLayout(boolean expanded){
        boolean current=candidateLayoutPending>0?requestedCandidateExpanded:displayed!=null&&displayed.optBoolean("expanded");
        if(current==expanded)return;
        requestedCandidateExpanded=expanded;candidateLayoutPending++;updateCandidateLayoutButton();
        try{action("candidate_layout",new JSONObject().put("expanded",expanded));}
        catch(JSONException ignored){candidateLayoutPending=Math.max(0,candidateLayoutPending-1);updateCandidateLayoutButton();}
    }
    private void updateCandidateLayoutButton(){
        if(candidateExpandButton==null)return;
        boolean expanded=candidateLayoutPending>0?requestedCandidateExpanded:displayed!=null&&displayed.optBoolean("expanded");
        candidateExpandButton.setText("⌄");
        candidateExpandButton.setContentDescription(expanded?"收起候选并显示键盘":"展开全部候选并隐藏键盘");
    }
    private void call(JSONObject request,String op,int generation) {
        if(handle==0) return;
        try {
            request.put("op",op).put("handle",handle);
            JSONObject response=new JSONObject(NativeBridge.request(request.toString()));
            if(!response.isNull("error")) { if(!op.equals("flush")) main.post(() -> { if(generation==epoch){if(op.equals("candidate_layout")){candidateLayoutPending=Math.max(0,candidateLayoutPending-1);updateCandidateLayoutButton();}if(status!=null)status.setText("候选已更新，请重新选择");} }); return; }
            JSONObject state=response.optJSONObject("state");
            if(state!=null && !op.equals("flush")) main.post(() -> { if(generation==epoch){if(op.equals("candidate_layout"))candidateLayoutPending=Math.max(0,candidateLayoutPending-1);render(state);} });
        } catch(Exception error) { main.post(() -> { if(generation==epoch){if(op.equals("candidate_layout")){candidateLayoutPending=Math.max(0,candidateLayoutPending-1);updateCandidateLayoutButton();}if(status!=null)status.setText("暂时无法生成候选，请切换键盘后重试");} }); }
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
                    if(commit.equals("\n"))EditorBehavior.enter(connection,getCurrentInputEditorInfo());
                    else connection.commitText(commit,1);
                }
                if(state.optBoolean("delete_backward"))EditorBehavior.delete(connection);
                if(!input.isEmpty() && !forceLatin) connection.setComposingText(input,1);
                else if(!lastComposition.isEmpty() && commit.isEmpty()) connection.setComposingText("",1);
                if(input.isEmpty()) connection.finishComposingText();
                connection.endBatchEdit();
            }
        } finally { applying=false; }
        if(applyDocumentChange) lastComposition=input;
        if(layoutEnglish!=isEnglish())buildKeys();
        updateMode();
        updateEnterKey();
        updateMicrophone();
        language.setText(state.optBoolean("english")?"中释义":state.optString("language","en").toUpperCase()+" 译词");
        String preedit=state.optString("preedit","");
        JSONArray keypadReadings=state.optJSONArray("readings");
        if(keypadReadings!=null&&keypadReadings.length()>0){
            JSONArray prefix=state.optJSONArray("reading_prefix");
            if(settings.getBoolean("nine_reading_steps",true)){
                java.util.ArrayList<String> selected=new java.util.ArrayList<>();if(prefix!=null)for(int i=0;i<prefix.length();i++)selected.add(prefix.optString(i));
                preedit=selected.isEmpty()?"选第1个拼音":String.join(" · ",selected)+(state.optBoolean("reading_complete")?" · 已选好":" · 第"+(selected.size()+1)+"个");
            }else preedit=state.optString("input")+" · "+preedit.replace("'","·");
        }
        status.setText(forceLatin ? privateInput ? "私密输入 · 不学习" : numericEditor?"数字输入":"直接输入 · EN" : preedit.isEmpty() ? isEnglish()?"英文输入":"拼音输入" : preedit+"    "+(state.optInt("page")+1)+"/"+state.optInt("page_count",1));
        status.setVisibility(View.VISIBLE);
        previousPage.setEnabled(state.optInt("page")>0);nextPage.setEnabled(state.optInt("page")+1<state.optInt("page_count"));previousPage.setAlpha(previousPage.isEnabled()?1:.3f);nextPage.setAlpha(nextPage.isEnabled()?1:.3f);
        boolean expanded=state.optBoolean("expanded");if(candidateLayoutPending==0)requestedCandidateExpanded=expanded;updateCandidateLayoutButton();
        if(speechShowing){setSpeechControls(true);return;}
        candidates.removeAllViews(); JSONArray list=state.optJSONArray("candidates");
        boolean hasCandidates=list!=null && list.length()>0 && !forceLatin;
        boolean candidateFocus=hasCandidates&&expanded;
        candidateBar.setVisibility(hasCandidates&&!expanded?View.VISIBLE:View.GONE);
        candidateScroll.setVisibility(View.VISIBLE);
        candidateBar.getLayoutParams().height=dp(candidateHeight());
        expandedPanel.setVisibility(candidateFocus?View.VISIBLE:View.GONE);
        expandedCandidateArea.setVisibility(candidateFocus?View.VISIBLE:View.GONE);
        keys.setVisibility(candidateFocus?View.GONE:View.VISIBLE);
        keyboardBody.getLayoutParams().height=dp(keyboardHeight()+(candidateFocus?candidateHeight():0));
        keyboardBody.requestLayout();
        renderReadingChoices(state.optJSONArray("readings"),state.optString("input"),state.optString("selected_reading"));
        candidates.setGravity(Gravity.CENTER_VERTICAL);
        if(!hasCandidates)return;
        expandedCandidates.removeAllViews();
        JSONArray readings=state.optJSONArray("readings");
        long revision=state.optLong("revision");
        if(expanded){
            int columns=wide?6:4;int areaWidth=Math.max(dp(180),Math.min(layoutWidth,dp(900))-dp(readings!=null&&readings.length()>0?62:0));int cellWidth=Math.max(dp(54),areaWidth/columns);
            LinearLayout gridRow=null;
            for(int i=0;i<list.length();i++){
                if(i%columns==0){gridRow=row();expandedCandidates.addView(gridRow,new LinearLayout.LayoutParams(-1,dp(candidateHeight())));}
                JSONObject candidate=list.optJSONObject(i);if(candidate==null)continue;
                gridRow.addView(candidateCell(candidate,i,revision,cellWidth,candidateHeight(),true),new LinearLayout.LayoutParams(cellWidth,-1));
            }
        } else {
            int cellWidth=candidateWidth();
            for(int i=0;i<list.length();i++){
                JSONObject candidate=list.optJSONObject(i);if(candidate!=null)candidates.addView(candidateCell(candidate,i,revision,cellWidth,candidateHeight(),false),new LinearLayout.LayoutParams(cellWidth,-1));
            }
        }
    }
    private View candidateCell(JSONObject candidate,int position,long revision,int cellWidth,int cellHeight,boolean grid){
        int index=candidate.optInt("id");
        LinearLayout cell=new LinearLayout(this);cell.setOrientation(LinearLayout.VERTICAL);cell.setGravity(Gravity.CENTER);cell.setPadding(dp(grid?3:4),dp(2),dp(grid?3:4),dp(2));cell.setBackground(palette.shape(this,position==0?palette.soft:palette.background,0,grid?8:10));
        JSONArray senses=candidate.optJSONArray("translation_senses");JSONObject firstSense=senses==null?null:senses.optJSONObject(0);
        LinearLayout heading=row();
        TextView word=new TextView(this);word.setText(candidate.optString("text"));word.setIncludeFontPadding(true);word.setTextSize(grid||candidate.optString("kind").equals("english")?16:18);word.setSingleLine(true);word.setEllipsize(android.text.TextUtils.TruncateAt.END);word.setTextColor(position==0?palette.accent:palette.ink);word.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));word.setGravity(Gravity.CENTER);heading.addView(word,new LinearLayout.LayoutParams(0,-2,1));
        JSONArray tags=candidate.optString("kind").equals("english")?candidate.optJSONArray("word_tags"):firstSense==null?null:firstSense.optJSONArray("tags");
        if(tags!=null&&tags.length()>0&&getSharedPreferences("settings",MODE_PRIVATE).getBoolean("show_vocabulary_tags",true)){
            JSONObject tag=tags.optJSONObject(0);if(tag!=null){TextView badge=new TextView(this);badge.setText(VocabularySettings.shortLabel(tag.optString("id"))+(tags.length()>1?"+":""));badge.setTextSize(7);badge.setTextColor(tag.optBoolean("selected")?palette.accent:palette.muted);badge.setContentDescription("词汇标签 "+tagLabels(tags));badge.setOnClickListener(v->showPronunciation(candidate));heading.addView(badge,new LinearLayout.LayoutParams(-2,-2));}
        }
        cell.addView(heading,new LinearLayout.LayoutParams(-1,-2));
        String glossText=firstSense==null||!displayed.optString("language").equals("en")?candidate.optString("annotation"):firstSense.optString("text");
        LinearLayout subtitle=row();subtitle.setGravity(Gravity.CENTER);subtitle.setContentDescription("查看"+candidate.optString("text")+"的音标和释义");subtitle.setOnClickListener(v->showPronunciation(candidate));
        TextView gloss=new TextView(this);gloss.setText(glossText);gloss.setIncludeFontPadding(true);gloss.setTextSize(10);gloss.setSingleLine(true);gloss.setEllipsize(android.text.TextUtils.TruncateAt.END);gloss.setGravity(Gravity.CENTER);gloss.setTextColor((firstSense==null?candidate.optBoolean("fresh"):firstSense.optBoolean("fresh"))?palette.fresh:palette.muted);subtitle.addView(gloss,new LinearLayout.LayoutParams(0,-2,1));
        TextView detail=new TextView(this);detail.setText("▾");detail.setTextSize(9);detail.setTextColor(palette.muted);detail.setGravity(Gravity.CENTER);subtitle.addView(detail,new LinearLayout.LayoutParams(dp(10),-2));
        cell.addView(subtitle,new LinearLayout.LayoutParams(-1,0,1));
        if(glossText.isEmpty())subtitle.setVisibility(View.INVISIBLE);
        cell.setContentDescription(candidate.optString("text")+" "+candidate.optString("annotation"));cell.setHapticFeedbackEnabled(true);
        cell.setOnClickListener(v->{v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);select("select",index,revision);});
        // Android supplies the long-press feedback once when this listener handles it.
        cell.setOnLongClickListener(v->{if(senses==null||senses.length()==0)return false;select("translation",index,revision);return true;});
        if(!grid)cell.setOnTouchListener(new View.OnTouchListener(){float startX,startY;boolean dragged,expandDragged;@Override public boolean onTouch(View view,MotionEvent event){if(event.getAction()==MotionEvent.ACTION_DOWN){startX=event.getX();startY=event.getY();dragged=false;expandDragged=false;return false;}if(event.getAction()==MotionEvent.ACTION_MOVE&&Math.abs(event.getY()-startY)>Math.abs(event.getX()-startX)*1.2f){if(event.getY()-startY>dp(16)){dragged=true;}else if(startY-event.getY()>dp(24)){expandDragged=true;}if(dragged||expandDragged){view.cancelLongPress();view.setPressed(false);view.getParent().requestDisallowInterceptTouchEvent(true);return true;}}if(event.getAction()==MotionEvent.ACTION_UP&&expandDragged){requestCandidateLayout(true);return true;}if(event.getAction()==MotionEvent.ACTION_UP&&dragged){showPronunciation(candidate);return true;}return dragged||expandDragged;}});
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(cellWidth,dp(cellHeight));params.setMargins(dp(2),0,dp(2),0);cell.setLayoutParams(params);return cell;
    }
    private void renderReadingChoices(JSONArray readings,String input,String selected){
        boolean hasReadings=readings!=null&&readings.length()>0&&input.matches("[2-9]+");
        readingScroll.setVisibility(hasReadings?View.VISIBLE:View.GONE);
        fillReadings(readingChoices,readings,selected,hasReadings);
        if(nineReadings!=null)fillReadings(nineReadings,readings,selected,hasReadings);
        String signature=settings.getBoolean("nine_reading_steps",true)+":"+(displayed==null?"":displayed.optJSONArray("reading_prefix"));
        if(!signature.equals(readingProgressSignature)){readingProgressSignature=signature;readingScroll.post(()->readingScroll.scrollTo(0,0));if(nineReadingScroll!=null){ScrollView rail=nineReadingScroll;rail.post(()->rail.scrollTo(0,0));}}
    }
    private void fillReadings(LinearLayout target,JSONArray readings,String selected,boolean hasReadings){
        target.removeAllViews();
        if(!hasReadings){for(String mark:new String[]{"。","？","！","、"}){Button b=control(mark,v->key(mark));b.setTextSize(19);target.addView(b,new LinearLayout.LayoutParams(-1,dp(40)));}return;}
        if(settings.getBoolean("nine_reading_steps",true) && displayed!=null && displayed.has("syllable_choices")){
            JSONArray prefix=displayed.optJSONArray("reading_prefix");int step=prefix==null?0:prefix.length();
            TextView heading=new TextView(this);heading.setText(displayed.optBoolean("reading_complete")?"已选好":"第"+(step+1)+"个");heading.setTextSize(10);heading.setTextColor(palette.muted);heading.setGravity(Gravity.CENTER);target.addView(heading,new LinearLayout.LayoutParams(-1,dp(20)));
            if(step>0){Button back=control("‹ "+prefix.optString(step-1),v->action("keypad_reading_back",null));back.setContentDescription("重选上一个拼音");back.setTextColor(palette.accent);target.addView(back,new LinearLayout.LayoutParams(-1,dp(32)));}
            JSONArray choices=displayed.optJSONArray("syllable_choices");
            if(choices!=null)for(int i=0;i<choices.length();i++){
                String syllable=choices.optString(i);Button option=control(syllable,v->{try{action("keypad_syllable",new JSONObject().put("reading",syllable).put("index",step));}catch(JSONException ignored){}});
                option.setContentDescription("选择第"+(step+1)+"个拼音 "+syllable);option.setAutoSizeTextTypeUniformWithConfiguration(9,14,1,android.util.TypedValue.COMPLEX_UNIT_SP);option.setEllipsize(null);option.setTextColor(palette.ink);target.addView(option,new LinearLayout.LayoutParams(-1,dp(40)));
            }
            if(step>0){Button all=control("全部重选",v->{try{action("keypad_reading",new JSONObject().put("reading",""));}catch(JSONException ignored){}});all.setContentDescription("重选全部拼音");target.addView(all,new LinearLayout.LayoutParams(-1,dp(36)));}
            return;
        }
        addReadingChoice(target,"全部",selected.isEmpty(),"");
        for(int i=0;i<readings.length();i++){String reading=readings.optString(i);if(!reading.isEmpty())addReadingChoice(target,reading,reading.equals(selected),reading);}
    }
    private void addReadingChoice(LinearLayout target,String label,boolean selected,String reading){
        Button choice=control(label.replace("'","·"),v->{try{action("keypad_reading",new JSONObject().put("reading",reading));}catch(JSONException ignored){}});choice.setTextSize(13);choice.setSingleLine(true);choice.setEllipsize(android.text.TextUtils.TruncateAt.END);choice.setContentDescription("选择读音 "+label);palette.style(choice,selected?palette.soft:palette.background,selected?palette.accent:palette.muted,7,false);target.addView(choice,new LinearLayout.LayoutParams(-1,dp(40)));
    }
    private int candidateWidth(){
        int available=Math.min(layoutWidth>0?layoutWidth:getResources().getDisplayMetrics().widthPixels-dp(12),dp(900))-dp(44);
        int visible=Math.min(9,Math.max(isEnglish()?3:4,available/dp(isEnglish()?100:76)));
        return Math.max(dp(48),available/visible);
    }
    private int candidateHeight(){return Math.max(54,(int)Math.ceil(44*Math.min(2,getResources().getConfiguration().fontScale))+8);}
    private int keyboardHeight(){return (keyHeight+6)*4;}
    private void switchLayout(){
        if(speechShowing || numericEditor)return;
        settings.edit().putString("keyboard_layout",nineKey?"qwerty":"nine").apply();
    }
    private void select(String op,int index,long revision) { try {action(op,new JSONObject().put("index",index).put("revision",revision));} catch(JSONException ignored) {} }
    private String tagLabels(JSONArray tags){StringBuilder labels=new StringBuilder();if(tags!=null)for(int i=0;i<tags.length();i++){JSONObject tag=tags.optJSONObject(i);if(tag!=null){if(labels.length()>0)labels.append(" · ");labels.append(tag.optString("label"));}}return labels.toString();}
    private void showPronunciation(JSONObject candidate){
        pronunciationPanel.removeAllViews();pronunciationPanel.setBackground(palette.shape(this,palette.surface,palette.line,12));
        LinearLayout header=row();header.setGravity(Gravity.CENTER_VERTICAL);header.setPadding(dp(12),0,dp(4),0);
        JSONObject pronunciation=candidate.optJSONObject("pronunciation");String word=pronunciation==null?candidate.optString("text"):pronunciation.optString("word");
        TextView title=new TextView(this);title.setText(word+" · "+(pronunciation==null?"释义":"音标"));title.setTextColor(palette.accent);title.setTextSize(12);title.setSingleLine(true);title.setEllipsize(android.text.TextUtils.TruncateAt.END);header.addView(title,new LinearLayout.LayoutParams(0,dp(28),1));
        Button close=control("收起",v -> {render(displayed,false);});close.setContentDescription("收起音标详情");header.addView(close,new LinearLayout.LayoutParams(dp(64),dp(44)));pronunciationPanel.addView(header);
        ScrollView scroll=new ScrollView(this);scroll.setFocusable(false);scroll.setVerticalScrollBarEnabled(true);scroll.setFillViewport(false);
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(12),0,dp(12),dp(10));
        TextView gloss=detailLine(candidate.optString("text")+" · 全部译词（向上滑动查看更多）");body.addView(gloss);
        JSONArray senses=candidate.optJSONArray("translation_senses");
        if(senses!=null)for(int i=0;i<senses.length();i++){
            JSONObject sense=senses.optJSONObject(i);if(sense==null)continue;JSONArray tags=sense.optJSONArray("tags");
            String tagDescription=!candidate.optString("kind").equals("english")&&displayed.optString("language").equals("en")?" · "+(tags==null || tags.length()==0?"暂无词汇标签":tagLabels(tags)):"";
            TextView entry=detailLine(sense.optString("text")+tagDescription);entry.setTextColor(palette.accent);body.addView(entry);
            if(!sense.isNull("translation_source")){TextView origin=detailLine("新增译词："+sense.optString("translation_source"));origin.setTextSize(10);origin.setTextColor(palette.muted);body.addView(origin);}
            java.util.LinkedHashSet<String> sources=new java.util.LinkedHashSet<>();if(tags!=null)for(int t=0;t<tags.length();t++){JSONArray names=tags.optJSONObject(t).optJSONArray("sources");if(names!=null)for(int n=0;n<names.length();n++)sources.add(names.optString(n));}
            if(!sources.isEmpty()){TextView source=detailLine("词表来源："+String.join(" / ",sources));source.setTextSize(10);source.setTextColor(palette.muted);body.addView(source);}
            JSONObject ipa=sense.optJSONObject("pronunciation");if(ipa!=null){if(!ipa.isNull("uk"))body.addView(detailLine("英式  "+ipa.optString("uk")));if(!ipa.isNull("us"))body.addView(detailLine("美式  "+ipa.optString("us")));}
            final int senseIndex=sense.optInt("index",i);Button insert=control("输入译词 "+sense.optString("text"),v->{try{action("translation",new JSONObject().put("index",candidate.optInt("id")).put("sense_index",senseIndex).put("revision",displayed.optLong("revision")));}catch(JSONException ignored){}});insert.setTextSize(12);body.addView(insert,new LinearLayout.LayoutParams(-1,dp(40)));
        }
        if(candidate.optString("kind").equals("english")){String tags=tagLabels(candidate.optJSONArray("word_tags"));if(!tags.isEmpty())body.addView(detailLine(tags));}
        if(pronunciation!=null && (candidate.optString("kind").equals("english") || senses==null || senses.length()==0)){
            String uk=pronunciation.isNull("uk")?"":pronunciation.optString("uk","");String us=pronunciation.isNull("us")?"":pronunciation.optString("us","");
            if(!uk.isEmpty())body.addView(detailLine("英式  "+uk));
            if(!us.isEmpty())body.addView(detailLine("美式  "+us));
        }
        scroll.addView(body);pronunciationPanel.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));keys.setVisibility(View.GONE);expandedPanel.setVisibility(View.GONE);pronunciationPanel.setVisibility(View.VISIBLE);
    }
    private TextView detailLine(String text){TextView label=new TextView(this);label.setText(text);label.setTextSize(13);label.setTextColor(palette.ink);label.setPadding(0,dp(3),0,dp(3));label.setLineSpacing(dp(2),1);return label;}
    private void cycleLanguage() {
        closeSpeech(true);
        String current=getSharedPreferences("settings",MODE_PRIVATE).getString("language","en"); String next=current.equals("en")?"ja":current.equals("ja")?"es":"en";
        getSharedPreferences("settings",MODE_PRIVATE).edit().putString("language",next).apply();
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
        keyAlternatives.dismiss();
        stopRepeat();layoutEnglish=isEnglish();
        if(keyboardBody!=null){keyboardBody.getLayoutParams().height=dp(keyboardHeight()+((expandedPanel!=null&&expandedPanel.getVisibility()==View.VISIBLE)?candidateHeight():0));keyboardBody.requestLayout();}
        boolean useNineKey=nineKey&&!numbers&&!layoutEnglish&&!forceLatin;
        keys.removeAllViews();nineReadings=null;nineReadingScroll=null;mode=null;enterKey=null;if(layoutButton!=null){layoutButton.setText(nineKey?"全键":"九键");layoutButton.setContentDescription(nineKey?"切换到全键拼音":"切换到九宫格拼音");layoutButton.setEnabled(!numericEditor&&!speechShowing);layoutButton.setAlpha(numericEditor?.35f:1);}
        if(numbers&&greekPage){buildGreekKeys();if(speechShowing)setSpeechControls(true);updateMicrophone();return;}
        if(numbers&&!symbolPage){buildNumberKeys();if(speechShowing)setSpeechControls(true);updateMicrophone();return;}
        if(numbers){
            String[] rows={"!@#$%&*()","-_=+/:;\"'",".,?!\\"};
            for(String rowText:rows){LinearLayout line=row();for(char symbol:rowText.toCharArray()){String value=String.valueOf(symbol);line.addView(typingButton(value,v->key(value)),weight(1));}if(rowText.length()==5){Button greek=button("希腊",v->{greekPage=true;buildKeys();});greek.setTextSize(13);line.addView(greek,weight(1.5f));line.addView(backspaceButton(),weight(1));}keys.addView(line);}
        }else if(useNineKey){
            buildNineKeys();updateMicrophone();if(speechShowing)setSpeechControls(true);return;
        }else{
            String[] rows={"qwertyuiop","asdfghjkl","zxcvbnm"};
            for(int i=0;i<rows.length;i++){LinearLayout line=row();if(i==1)line.setPadding(dp(wide?46:16),0,dp(wide?46:16),0);if(i==2){Button shift=iconButton(new KeyboardIcon(KeyboardIcon.SHIFT,upper?palette.onAccent:palette.ink,capsLock),capsLock?"大写锁定":upper?"大写已开启":"大写",v->shift());if(upper)palette.style(shift,palette.accent,palette.onAccent,10,false);line.addView(shift,weight(1.3f));}
                for(char letter:rows[i].toCharArray()){String value=String.valueOf(letter);String alternate=qwertyAlternate(letter);Button button=alternativeButton(layoutEnglish&&!upper?value:value.toUpperCase(),alternate,new String[]{value.toUpperCase(java.util.Locale.ROOT),alternate,value},1,v->{key(upper&&isEnglish()?value.toUpperCase():value);if(upper&&!capsLock){upper=false;buildKeys();}});line.addView(button,weight(1));}
                if(i==2){Button back=backspaceButton();line.addView(back,weight(1.3f));}KeyHitBox.expandRow(line);keys.addView(line);
            }
        }
        LinearLayout bottom=row();Button symbols=button(numbers?"ABC":"123",v->{numbers=!numbers;symbolPage=false;greekPage=false;buildKeys();});symbols.setTextSize(14);bottom.addView(symbols,weight(1.05f));
        mode=button("中/英",v->toggleMode());mode.setTextSize(12);bottom.addView(mode,weight(1.25f));updateMode();
        bottom.addView(punctuationButton(layoutEnglish?",":"，",true),weight(.8f));
        Button globe=iconButton(new GlobeIcon(palette.ink),"切换键盘",v->((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());bottom.addView(globe,weight(.7f));
        Button space=typingButton("空格",v->{if(forceLatin)key(" ");else action("space",null);});palette.style(space,palette.key,palette.muted,7,true);space.setTextSize(14);bottom.addView(space,weight(3.25f));
        bottom.addView(punctuationButton(layoutEnglish?".":"。",false),weight(.65f));
        bottom.addView(makeEnterKey(),weight(1.2f));if(!numbers)KeyHitBox.expandRow(bottom);keys.addView(bottom);
        updateMicrophone();
        if(speechShowing)setSpeechControls(true);
    }
    private void buildGreekKeys(){
        String[] rows={"αβγδεζηθ","ικλμνξοπ","ρστυφχψω"};
        for(String letters:rows){LinearLayout line=row();for(char ch:letters.toCharArray()){String value=String.valueOf(ch);if(greekUpper)value=value.toUpperCase(java.util.Locale.ROOT);final String symbol=value;Button b=typingButton(symbol,v->literal(symbol));b.setContentDescription("希腊字母 "+symbol);line.addView(b,weight(1));}keys.addView(line);}
        LinearLayout bottom=row();Button back=button("符号",v->{greekPage=false;buildKeys();});back.setTextSize(14);bottom.addView(back,weight(1.3f));Button cases=button(greekUpper?"αβγ":"ΑΒΓ",v->{greekUpper=!greekUpper;buildKeys();});cases.setContentDescription("切换希腊字母大小写");cases.setTextSize(16);bottom.addView(cases,weight(1.4f));Button alpha=button("ABC",v->{numbers=false;symbolPage=false;greekPage=false;buildKeys();});alpha.setTextSize(14);bottom.addView(alpha,weight(1.3f));Button space=typingButton("空格",v->{if(forceLatin)key(" ");else action("space",null);});space.setTextSize(14);bottom.addView(space,weight(2));bottom.addView(backspaceButton(),weight(1));bottom.addView(makeEnterKey(),weight(1));keys.addView(bottom);
    }
    private void buildNineKeys(){
        LinearLayout mainRow=row();keys.addView(mainRow,new LinearLayout.LayoutParams(-1,-1));
        LinearLayout left=new LinearLayout(this);left.setOrientation(LinearLayout.VERTICAL);mainRow.addView(left,new LinearLayout.LayoutParams(dp(wide?74:54),-1));
        ScrollView readings=new ScrollView(this);nineReadingScroll=readings;readings.setVerticalScrollBarEnabled(false);nineReadings=new LinearLayout(this);nineReadings.setOrientation(LinearLayout.VERTICAL);readings.addView(nineReadings);left.addView(readings,new LinearLayout.LayoutParams(-1,0,1));
        Button comma=punctuationButton("，",true);LinearLayout.LayoutParams commaSize=new LinearLayout.LayoutParams(-1,dp(keyHeight));commaSize.setMargins(dp(3),dp(3),dp(3),dp(3));left.addView(comma,commaSize);
        LinearLayout center=new LinearLayout(this);center.setOrientation(LinearLayout.VERTICAL);mainRow.addView(center,new LinearLayout.LayoutParams(0,-1,1));
        String[] captions={"符号","ABC","DEF","GHI","JKL","MNO","PQRS","TUV","WXYZ"};
        for(int r=0;r<3;r++){LinearLayout line=row();for(int c=0;c<3;c++){final String digit=String.valueOf(r*3+c+1);String caption=captions[r*3+c];java.util.ArrayList<String> choices=new java.util.ArrayList<>();if(!digit.equals("1"))for(char letter:caption.toCharArray())choices.add(String.valueOf(letter));int defaultIndex=choices.size();choices.add(digit);if(digit.equals("1")){choices.add("@");choices.add(".");}else for(char letter:caption.toLowerCase(java.util.Locale.ROOT).toCharArray())choices.add(String.valueOf(letter));Button b=alternativeButton(digit+"  "+caption,"",choices.toArray(new String[0]),defaultIndex,v->{if(digit.equals("1")){numbers=true;symbolPage=true;buildKeys();}else try{action("keypad",new JSONObject().put("text",digit));}catch(JSONException ignored){}});b.setTextSize(17);b.setContentDescription("九键 "+digit+" "+caption);palette.style(b,palette.key,palette.ink,7,true);line.addView(b,weight(1));}center.addView(line);}
        LinearLayout bottom=row();Button symbols=button("123",v->{numbers=true;buildKeys();});symbols.setTextSize(14);bottom.addView(symbols,weight(1));Button space=typingButton("空格",v->action("space",null));space.setTextSize(15);palette.style(space,palette.key,palette.muted,7,true);bottom.addView(space,weight(1.7f));mode=button("中/英",v->toggleMode());mode.setTextSize(13);bottom.addView(mode,weight(1));center.addView(bottom);updateMode();
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);mainRow.addView(right,new LinearLayout.LayoutParams(dp(wide?70:52),-1));
        Button back=backspaceButton();right.addView(back,railSize(1));Button clear=button("重输",v->action("clear",null));clear.setTextSize(13);right.addView(clear,railSize(1));
        Button globe=iconButton(new GlobeIcon(palette.ink),"切换键盘",v->((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());right.addView(globe,railSize(1));right.addView(makeEnterKey(),railSize(1));
        if(displayed!=null)renderReadingChoices(displayed.optJSONArray("readings"),displayed.optString("input"),displayed.optString("selected_reading"));else fillReadings(nineReadings,null,"",false);
    }
    private EnterKey makeEnterKey(){
        enterKey=new EnterKey(this,palette.onAccent);styleButton(enterKey,"",v->{
            if(forceLatin)EditorBehavior.enter(getCurrentInputConnection(),getCurrentInputEditorInfo());
            else action("enter",null);
        });palette.style(enterKey,palette.accent,palette.onAccent,7,false);updateEnterKey();return enterKey;
    }
    private void updateEnterKey(){
        if(enterKey==null)return;
        boolean composing=!forceLatin&&displayed!=null&&!displayed.optString("input").isEmpty();
        enterKey.actionLabel(composing?"上屏":EditorBehavior.label(getCurrentInputEditorInfo()));
    }
    private void buildNumberKeys(){
        int klass=editorType&InputType.TYPE_MASK_CLASS;boolean phone=klass==InputType.TYPE_CLASS_PHONE;
        boolean strictNumber=numericEditor&&klass==InputType.TYPE_CLASS_NUMBER;
        String decimal=phone?"*":strictNumber&&(editorType&InputType.TYPE_NUMBER_FLAG_DECIMAL)==0?"":".";
        String sign=phone?"+":strictNumber&&(editorType&InputType.TYPE_NUMBER_FLAG_SIGNED)==0?"":klass==InputType.TYPE_CLASS_DATETIME?":":"-";
        LinearLayout panel=row();keys.addView(panel,new LinearLayout.LayoutParams(-1,-1));
        LinearLayout grid=new LinearLayout(this);grid.setOrientation(LinearLayout.VERTICAL);panel.addView(grid,new LinearLayout.LayoutParams(0,-1,1));
        for(String digits:new String[]{"123","456","789"}){LinearLayout line=row();for(char digit:digits.toCharArray()){String value=String.valueOf(digit);line.addView(typingButton(value,v->literal(value)),weight(1));}grid.addView(line);}
        LinearLayout bottom=row();Button alpha=numericEditor?iconButton(new GlobeIcon(palette.ink),"切换键盘",v->((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker()):button("ABC",v->{numbers=false;symbolPage=false;greekPage=false;buildKeys();});alpha.setTextSize(14);bottom.addView(alpha,weight(1));bottom.addView(typingButton("0",v->literal("0")),weight(1));Button point=typingButton(decimal,v->literal(decimal));point.setEnabled(!decimal.isEmpty());if(decimal.isEmpty())point.setVisibility(View.INVISIBLE);bottom.addView(point,weight(1));grid.addView(bottom);
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);panel.addView(right,new LinearLayout.LayoutParams(dp(wide?74:58),-1));
        if(strictNumber){
            LinearLayout.LayoutParams fixed=new LinearLayout.LayoutParams(-1,dp(keyHeight));fixed.setMargins(dp(3),dp(3),dp(3),dp(3));right.addView(backspaceButton(),fixed);
            if(!sign.isEmpty()){Button minus=typingButton(sign,v->literal(sign));right.addView(minus,new LinearLayout.LayoutParams(fixed));}
            right.addView(makeEnterKey(),railSize(1));return;
        }
        right.addView(backspaceButton(),railSize(1));
        String extra=phone?"#":klass==InputType.TYPE_CLASS_DATETIME?"/":"符号";
        Button symbols=button(extra,v->{if(numericEditor)literal(extra);else{symbolPage=true;buildKeys();}});symbols.setTextSize(13);symbols.setEnabled(!strictNumber);symbols.setAlpha(strictNumber?.35f:1);right.addView(symbols,railSize(1));
        Button minus=typingButton(sign,v->literal(sign));minus.setEnabled(!sign.isEmpty());right.addView(minus,railSize(1));right.addView(makeEnterKey(),railSize(1));
    }
    private LinearLayout.LayoutParams railSize(float weight){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,0,weight);p.setMargins(dp(3),dp(3),dp(3),dp(3));return p;}
    private Button backspaceButton(){Button back=iconButton(new KeyboardIcon(KeyboardIcon.BACKSPACE,palette.ink,false),"删除",v->backspace());back.setOnTouchListener((v,event)->{if(event.getAction()==MotionEvent.ACTION_DOWN){v.setPressed(true);v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);backspace();repeating=new Runnable(){public void run(){backspace();main.postDelayed(repeating,65);}};main.postDelayed(repeating,400);}else if(event.getAction()==MotionEvent.ACTION_UP||event.getAction()==MotionEvent.ACTION_CANCEL){v.setPressed(false);stopRepeat();}return true;});return back;}
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
        if(language!=null)language.setEnabled(!blocked);if(themeButton!=null)themeButton.setEnabled(!blocked);if(layoutButton!=null)layoutButton.setEnabled(!blocked&&!numericEditor);
        if(candidateExpandButton!=null)candidateExpandButton.setEnabled(!blocked);
        if(previousPage!=null)previousPage.setEnabled(!blocked && displayed!=null && displayed.optInt("page")>0);
        if(nextPage!=null)nextPage.setEnabled(!blocked && displayed!=null && displayed.optInt("page")+1<displayed.optInt("page_count"));
        updateMicrophone();
    }
    private void closeSpeech(boolean restore){
        speechToken++;if(speech!=null)speech.cancel();if(localSpeech!=null)localSpeech.cancel();speechShowing=false;
        if(speechPanel!=null){speechPanel.setVisibility(View.GONE);speechPanel.removeAllViews();}
        if(candidateScroll!=null)candidateScroll.setVisibility(displayed!=null && !displayed.optBoolean("expanded") && !forceLatin && displayed.optJSONArray("candidates")!=null && displayed.optJSONArray("candidates").length()>0?View.VISIBLE:View.GONE);
        if(expandedCandidateArea!=null)expandedCandidateArea.setVisibility(displayed!=null && displayed.optBoolean("expanded") && !forceLatin && displayed.optJSONArray("candidates")!=null && displayed.optJSONArray("candidates").length()>0?View.VISIBLE:View.GONE);setSpeechControls(false);
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
        candidateBar.setVisibility(View.GONE);expandedPanel.setVisibility(View.GONE);keys.setVisibility(View.GONE);keyboardBody.getLayoutParams().height=dp(keyboardHeight());keyboardBody.requestLayout();speechPanel.setVisibility(View.VISIBLE);speechPanel.removeAllViews();
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
    private void backspace(){if(forceLatin)EditorBehavior.delete(getCurrentInputConnection());else action("backspace",null);}
    private void stopRepeat(){if(repeating!=null){main.removeCallbacks(repeating);repeating=null;}}
    private int dp(float value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private int keyboardLift(){String gap=getSharedPreferences("settings",MODE_PRIVATE).getString("keyboard_bottom_gap","standard");return dp(compact?4:gap.equals("raised")?28:gap.equals("small")?4:16);}
    private LinearLayout row(){LinearLayout view=new LinearLayout(this);view.setOrientation(LinearLayout.HORIZONTAL);view.setBaselineAligned(false);view.setGravity(Gravity.CENTER_VERTICAL);return view;}
    private LinearLayout.LayoutParams weight(float value){LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,dp(keyHeight),value);int margin=dp(wide?4:3);params.setMargins(margin,dp(3),margin,dp(3));return params;}
    private LinearLayout.LayoutParams toolbarSize(int width){return new LinearLayout.LayoutParams(dp(width),dp(44));}
    private Button button(String label,View.OnClickListener listener){return styleButton(new Button(this),label,listener);}
    private Button typingButton(String label,View.OnClickListener listener){return styleButton(new TypingKey(this),label,listener);}
    private Button alternativeButton(String label,String hint,String[] choices,int selected,View.OnClickListener tap){
        AlternativeKey key=new AlternativeKey(this,hint,palette.muted,new AlternativeKey.Listener(){
            public boolean open(AlternativeKey owner){return keyAlternatives.show(owner,root,choices,selected,palette,WordtrailIME.this::literal);}
            public void move(float x,float y){keyAlternatives.move(x,y);}
            public void finish(float x,float y){keyAlternatives.finish(x,y);}
            public void cancel(AlternativeKey owner){keyAlternatives.cancel(owner);}
        });return styleButton(key,label,tap);
    }
    private void literal(String value){if(speechShowing)return;if(forceLatin){InputConnection c=getCurrentInputConnection();if(c!=null)c.commitText(value,1);}else try{action("literal",new JSONObject().put("text",value));}catch(JSONException ignored){}}
    private String qwertyAlternate(char letter){String letters="qwertyuiopasdfghjklzxcvbnm";String symbols="1234567890~!@#%\"' *?()-_:;/".replace(" ","");return String.valueOf(symbols.charAt(letters.indexOf(letter)));}
    private Button punctuationButton(String label,boolean comma){String[] choices=layoutEnglish?new String[]{",",";","!","?",".","/"}:new String[]{"，","；","！","？","。","、"};return alternativeButton(label,"",choices,comma?1:3,v->key(comma?",":"."));}
    private Button styleButton(Button b,String label,View.OnClickListener listener){b.setText(label);b.setGravity(Gravity.CENTER);b.setIncludeFontPadding(false);boolean letter=label.matches("[a-zA-Z0-9]");b.setTextSize(letter?compact?19:wide?23:21:17);palette.style(b,letter?palette.key:palette.function,palette.ink,7,letter);palette.feedback(b);b.setOnClickListener(listener);return b;}
    private Button iconButton(android.graphics.drawable.Drawable icon,String description,View.OnClickListener listener){Button b=new IconButton(this,icon,description);palette.style(b,palette.function,palette.ink,10,false);palette.feedback(b);b.setOnClickListener(listener);return b;}
    private Button control(String label,View.OnClickListener listener){Button b=button(label,listener);boolean symbol=label.equals("◐")||label.equals("⌄")||label.equals("‹")||label.equals("›");b.setMaxLines(1);b.setHorizontallyScrolling(false);b.setAutoSizeTextTypeUniformWithConfiguration(8,symbol?22:13,1,android.util.TypedValue.COMPLEX_UNIT_SP);palette.style(b,palette.background,palette.muted,10,false);return b;}
    private void applyTheme(){
        stopRepeat();palette=WordtrailStyle.load(this);
        root.setBackground(palette.shape(this,palette.background,0,18));brand.setTextColor(palette.accent);status.setTextColor(palette.muted);
        for(Button item:new Button[]{language,layoutButton,themeButton,previousPage,nextPage,candidateExpandButton})if(item!=null)palette.style(item,palette.background,palette.muted,10,false);
        if(microphone instanceof IconButton){((IconButton)microphone).setIcon(new KeyboardIcon(KeyboardIcon.MICROPHONE,palette.accent,false));palette.style(microphone,palette.background,palette.accent,10,false);}
        if(hideKeyboardButton instanceof IconButton){((IconButton)hideKeyboardButton).setIcon(new KeyboardIcon(KeyboardIcon.HIDE,palette.ink,false));palette.style(hideKeyboardButton,palette.background,palette.ink,10,false);}
        if(getWindow()!=null && getWindow().getWindow()!=null){getWindow().getWindow().setNavigationBarColor(palette.background);getWindow().getWindow().getDecorView().setSystemUiVisibility(palette.id.equals("night")?0:View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);}
        buildKeys();if(displayed!=null)render(displayed,false);
    }
    private void chooseTheme(View anchor){
        PopupMenu menu=new PopupMenu(this,anchor);String[] ids={"jade","lavender","night"};String[] names={"青绿","粉紫","深色"};
        for(int i=0;i<ids.length;i++)menu.getMenu().add(0,i,i,names[i]);
        menu.setOnMenuItemClickListener(item->{settings.edit().putString("theme",ids[item.getItemId()]).apply();return true;});menu.show();
    }
}
