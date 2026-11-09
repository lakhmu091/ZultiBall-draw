package com.zultiball.predictor;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.content.SharedPreferences;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends Activity {
    private final int bg = Color.rgb(8, 13, 11);
    private final int green = Color.rgb(84, 255, 133);
    private final int panel = Color.rgb(16, 37, 26);
    private LinearLayout content;
    private TextView resultView, statusView;
    private EditText urlInput;
    private WebView reader;
    private final Handler handler = new Handler();
    private final long REFRESH_MS = 6L * 60L * 60L * 1000L;
    private final Runnable periodicRefresh = new Runnable() {
        @Override public void run() {
            String saved = prefs().getString("draw_url", "");
            if (!saved.isEmpty()) loadOfficialPage(saved);
            handler.postDelayed(this, REFRESH_MS);
        }
    };

    private SharedPreferences prefs() {
        return getSharedPreferences("zultiball", MODE_PRIVATE);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(bg);
        getWindow().setNavigationBarColor(bg);
        setupReader();
        showDashboard();
        String saved = prefs().getString("draw_url", "");
        if (!saved.isEmpty()) {
            urlInput.setText(saved);
            resultView.setText(prefs().getString("last_result", "No result saved yet."));
            statusView.setText("Saved result loaded. Waiting for refresh.");
        }
        handler.postDelayed(periodicRefresh, REFRESH_MS);
    }

    @Override protected void onDestroy() {
        handler.removeCallbacks(periodicRefresh);
        if (reader != null) reader.destroy();
        super.onDestroy();
    }

    private void setupReader() {
        reader = new WebView(this);
        reader.getSettings().setJavaScriptEnabled(true);
        reader.addJavascriptInterface(new PageBridge(), "ZultiBridge");
        reader.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                String js = "(function(){"
                    + "var t=document.body?document.body.innerText:'';"
                    + "var a=t.indexOf('Winning numbers');"
                    + "if(a<0){ZultiBridge.failed('Could not find Winning numbers on this page.');return;}"
                    + "var s=t.substring(a+'Winning numbers'.length);"
                    + "var b=s.indexOf('Divisions');if(b>=0)s=s.substring(0,b);"
                    + "var m=s.match(/\\d+/g)||[];"
                    + "ZultiBridge.received(m.join(','));"
                    + "})();";
                view.evaluateJavascript(js, null);
            }
        });
    }

    private class PageBridge {
        @JavascriptInterface public void received(final String raw) {
            runOnUiThread(() -> {
                String[] parts = raw.split(",");
                StringBuilder out = new StringBuilder();
                int count = 0;
                java.util.HashSet<Integer> seen = new java.util.HashSet<>();
                for (String p : parts) {
                    try {
                        int n = Integer.parseInt(p.trim());
                        if (n < 1 || n > 99 || !seen.add(n)) continue;
                        if (count > 0) out.append("   ");
                        out.append(String.format("%02d", n));
                        count++;
                    } catch (Exception ignored) {}
                }
                if (count < 5 || count > 10) {
                    failed("The page was found, but the number list could not be verified. Check the official page manually.");
                    return;
                }
                String value = out.toString();
                resultView.setText(value + "\\n\\n" + count + " winning numbers");
                statusView.setText("Synced from official Zulti page • " + new java.text.SimpleDateFormat("dd MMM yyyy, HH:mm", java.util.Locale.getDefault()).format(new java.util.Date()));
                prefs().edit().putString("last_result", resultView.getText().toString()).apply();
            });
        }
        @JavascriptInterface public void failed(final String message) {
            runOnUiThread(() -> statusView.setText(message));
        }
    }

    private void loadOfficialPage(String url) {
        if (url == null || !url.startsWith("https://zulti.com/draws/")) {
            statusView.setText("Please use a public https://zulti.com/draws/... result link.");
            return;
        }
        prefs().edit().putString("draw_url", url).apply();
        statusView.setText("Loading official result page...");
        reader.loadUrl(url);
    }

    private GradientDrawable shape(int color, int stroke) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(24f);
        if (stroke != 0) d.setStroke(2, stroke);
        return d;
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        t.setPadding(4, 8, 4, 8);
        return t;
    }

    private void section(String title) {
        TextView t = text(title, 14, green, true);
        t.setPadding(4, 20, 4, 8);
        content.addView(t);
    }

    private void showDashboard() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(bg);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(22, 18, 22, 28);
        scroll.addView(content);

        content.addView(text("ZULTIBALL AI", 28, green, true));
        content.addView(text("ADVANCED DRAW ANALYSIS", 12, Color.LTGRAY, true));

        section("OFFICIAL RESULT SYNC");
        TextView help = text("Paste a public Zulti draw result link. The app reads the visible winning-number section.", 13, Color.WHITE, false);
        help.setBackground(shape(panel, green));
        help.setPadding(14, 14, 14, 14);
        content.addView(help);

        urlInput = new EditText(this);
        urlInput.setSingleLine(true);
        urlInput.setTextColor(Color.WHITE);
        urlInput.setHintTextColor(Color.GRAY);
        urlInput.setHint("https://zulti.com/draws/...");
        urlInput.setTextSize(12);
        urlInput.setPadding(12, 12, 12, 12);
        urlInput.setBackground(shape(Color.rgb(20, 28, 23), Color.rgb(40, 124, 66)));
        LinearLayout.LayoutParams inputParams = new LinearLayout.LayoutParams(-1, -2);
        inputParams.setMargins(0, 12, 0, 8);
        content.addView(urlInput, inputParams);

        Button sync = button("SYNC OFFICIAL RESULT");
        content.addView(sync);
        sync.setOnClickListener(v -> loadOfficialPage(urlInput.getText().toString().trim()));

        statusView = text("Not synced yet.", 12, Color.LTGRAY, false);
        content.addView(statusView);

        section("LATEST SAVED WINNING NUMBERS");
        resultView = text("No result saved yet.", 23, green, true);
        resultView.setGravity(Gravity.CENTER);
        resultView.setBackground(shape(panel, Color.rgb(40, 124, 66)));
        resultView.setPadding(12, 22, 12, 22);
        content.addView(resultView);

        section("AUTO-REFRESH");
        content.addView(text("The saved result page is checked every 6 hours while this app stays open. This version cannot discover a new draw URL automatically because no documented public Zulti draw-feed/API was found.", 12, Color.LTGRAY, false));

        section("ANALYSIS");
        content.addView(text("Hot/Cold statistics and prediction evaluation are planned for the next build. Draw results are random; statistics cannot guarantee future outcomes.", 12, Color.LTGRAY, false));

        content.addView(text("Source: Zulti public draw page. This app only reads public results; it does not access accounts or alter Zulti servers.", 11, Color.GRAY, false));
        setContentView(scroll);
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextColor(green);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        b.setBackground(shape(panel, Color.rgb(40, 124, 66)));
        return b;
    }
}
