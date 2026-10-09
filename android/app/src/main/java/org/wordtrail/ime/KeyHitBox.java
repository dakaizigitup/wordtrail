package org.wordtrail.ime;

import android.graphics.Rect;
import android.view.MotionEvent;
import android.view.TouchDelegate;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;

/** 保持键帽外观，把按键间距与第二行缩进纳入各自的独立触摸区。 */
final class KeyHitBox extends FrameLayout {
    private final View key;
    private TouchDelegate delegate;

    private KeyHitBox(View key, LinearLayout.LayoutParams old, int left, int right) {
        super(key.getContext());
        this.key = key;
        setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        setClipChildren(false);
        setClipToPadding(false);
        FrameLayout.LayoutParams cap = new FrameLayout.LayoutParams(-1, old.height);
        cap.setMargins(old.leftMargin + left, old.topMargin, old.rightMargin + right, old.bottomMargin);
        addView(key, cap);
    }

    @Override protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        delegate = new TouchDelegate(new Rect(0, 0, w, h), key);
        setTouchDelegate(delegate);
    }

    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        if (!isEnabled() || delegate == null || !key.isEnabled() || key.getVisibility() != View.VISIBLE) return false;
        // TouchDelegate 会调整局部坐标；保留原事件供父容器继续分发其他手指。
        MotionEvent copy = MotionEvent.obtain(event);
        try { return delegate.onTouchEvent(copy); }
        finally { copy.recycle(); }
    }

    @Override public void setEnabled(boolean enabled) {
        super.setEnabled(enabled);
        if (key != null) key.setEnabled(enabled);
    }

    static void expandRow(LinearLayout row) {
        int count = row.getChildCount();
        View[] children = new View[count];
        for (int i = 0; i < count; i++) children[i] = row.getChildAt(i);
        int left = row.getPaddingLeft(), right = row.getPaddingRight();
        row.removeAllViews();
        row.setPadding(0, row.getPaddingTop(), 0, row.getPaddingBottom());
        // Android 原生分指派发：两只手指可分别落在两个键的容器内。
        row.setMotionEventSplittingEnabled(true);
        for (int i = 0; i < count; i++) {
            View key = children[i];
            LinearLayout.LayoutParams old = (LinearLayout.LayoutParams) key.getLayoutParams();
            int extraLeft = i == 0 ? left : 0, extraRight = i == count - 1 ? right : 0;
            KeyHitBox box = new KeyHitBox(key, old, extraLeft, extraRight);
            LinearLayout.LayoutParams hit = new LinearLayout.LayoutParams(
                old.width + old.leftMargin + old.rightMargin + extraLeft + extraRight,
                old.height + old.topMargin + old.bottomMargin, old.weight);
            row.addView(box, hit);
        }
    }
}
