import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ۱. تنظیمات پایه و تم اختصاصی
st.set_page_config(page_title="LedgerLens AI Ultra", layout="wide", page_icon="💎")

st.markdown("""
<style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { direction: rtl; font-family: 'Vazir', sans-serif; }
    
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-right: 5px solid #0068c9;
        margin-bottom: 20px;
    }
    .kpi-label { font-size: 14px; color: #666; margin-bottom: 10px; }
    .kpi-value { font-size: 24px; font-weight: bold; color: #1E1E1E; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# توابع منطقی (بدون ارور)
# ---------------------------------------------------------
@st.cache_data 
def clean_data(file):
    df = pd.read_excel(file, header=3)
    df = df.dropna(subset=['تاریخ'], how='all')

    def normalize_date(val):
        s = str(val).split(' ')[0].strip()
        parts = s.replace('-', '/').split('/')
        try:
            y, m, d = (int(p) for p in parts[:3])
            return f"{y:04d}/{m:02d}/{d:02d}"
        except: return s
    df['تاریخ'] = df['تاریخ'].apply(normalize_date)

    def clean_money(val):
        if pd.isna(val) or val == '-': return 0
        return int(str(val).replace(',', '').strip())

    df['واریز (ریال)'] = df['واریز (ریال)'].apply(clean_money)
    df['برداشت (ریال)'] = df['برداشت (ریال)'].apply(clean_money)
    
    def split_tags(text):
        if pd.isna(text) or str(text).strip() == '': return ['-', '-', '-', '-', '-']
        parts = str(text).strip('/').split('/')
        while len(parts) < 5: parts.append('-')
        return parts[:5]

    tags_df = df['توضیحات کاربر'].apply(split_tags).apply(pd.Series)
    tags_df.columns = ['ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی']
    df = pd.concat([df, tags_df], axis=1)
    df['مرکز'] = df['مرکز'].astype(str).str.strip()
    
    df = df.sort_values('تاریخ')
    df['موجودی_لحظه‌ای'] = df['واریز (ریال)'].cumsum() - df['برداشت (ریال)'].cumsum()
    return df

def detect_anomalies(df):
    expenses = df[df['برداشت (ریال)'] > 0]
    if expenses.empty: return pd.DataFrame()
    mean = expenses['برداشت (ریال)'].mean()
    std = expenses['برداشت (ریال)'].std()
    threshold = mean + (2 * std)
    return expenses[expenses['برداشت (ریال)'] > threshold]

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens AI Ultra")
st.caption("سیستم هوشمند مدیریت و پایش منابع مالی")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل", type=['xlsx'])

if uploaded_file:
    df = clean_data(uploaded_file)
    
    dates = df['تاریخ'].unique().tolist()
    d_range = st.sidebar.select_slider("📅 بازه گزارش", options=dates, value=(dates[0], dates[-1]))
    filtered_df = df[(df['تاریخ'] >= d_range[0]) & (df['تاریخ'] <= d_range[1])]

    # ۱. KPIs
    ti, te = filtered_df['واریز (ریال)'].sum(), filtered_df['برداشت (ریال)'].sum()
    savings_rate = ((ti - te) / ti * 100) if ti > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="kpi-card" style="border-right-color: #2ecc71;"><div class="kpi-label">درآمد کل</div><div class="kpi-value">{ti:,.0f}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card" style="border-right-color: #e74c3c;"><div class="kpi-label">هزینه کل</div><div class="kpi-value">{te:,.0f}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card" style="border-right-color: #3498db;"><div class="kpi-label">تراز نهایی</div><div class="kpi-value">{(ti - te):,.0f}</div></div>', unsafe_allow_html=True)
    with c4: 
        h_color = "#2ecc71" if savings_rate > 20 else "#f39c12" if savings_rate > 0 else "#e74c3c"
        st.markdown(f'<div class="kpi-card" style="border-right-color: {h_color};"><div class="kpi-label">نرخ پس‌انداز</div><div class="kpi-value">{savings_rate:.1f}%</div></div>', unsafe_allow_html=True)

    # ۲. نمودار Trend
    st.subheader("📈 روند موجودی لحظه‌ای")
    st.plotly_chart(px.area(filtered_df, x='تاریخ', y='موجودی_لحظه‌ای', color_discrete_sequence=['#0068c9']), use_container_width=True)

    # ۳. تب‌ها
    tab_insight, tab_personal, tab_work, tab_search = st.tabs([
        "🧠 بینش هوشمند (AI)", "👤 حساب شخصی", "🏭 حساب کارگاه", "🔍 جستجوی تراکنش"
    ])

    with tab_insight:
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown("#### 🚨 رادار ناهنجاری")
            anoms = detect_anomalies(filtered_df)
            if not anoms.empty:
                st.warning("موارد مشکوک شناسایی شد:")
                # اصلاح ارور: فقط ستون مبلغ فرمت می‌گیرد
                st.dataframe(anoms[['تاریخ', 'کلاس', 'جزئیات', 'برداشت (ریال)']].style.format({
                    'برداشت (ریال)': '{:,.0f}'
                }), use_container_width=True)
            else:
                st.success("الگوی مخارج کاملاً نرمال است.")
        
        with col_in2:
            st.markdown("#### 🏆 ۵ منبع اصلی هزینه")
            top_5 = filtered_df[filtered_df['برداشت (ریال)'] > 0].groupby('جزئیات')['برداشت (ریال)'].sum().nlargest(5).reset_index()
            st.plotly_chart(px.bar(top_5, x='برداشت (ریال)', y='جزئیات', orientation='h', color_discrete_sequence=['#e74c3c']), use_container_width=True)

    with tab_personal:
        p_data = filtered_df[filtered_df['مرکز'] == 'شخصی']
        if not p_data.empty:
            st.plotly_chart(px.treemap(p_data[p_data['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)'), use_container_width=True)
            st.dataframe(p_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format('{:,.0f}'), use_container_width=True)

    with tab_work:
        w_data = filtered_df[filtered_df['مرکز'] == 'کارگاه']
        if not w_data.empty:
            st.plotly_chart(px.treemap(w_data[w_data['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)'), use_container_width=True)
            st.dataframe(w_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format('{:,.0f}'), use_container_width=True)

    with tab_search:
        query = st.text_input("🔎 جستجو (مثلاً: اسنپ، اجاره، خرید...):")
        if query:
            res = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)]
            # اصلاح فرمت در جستجو
            st.dataframe(res.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True)

else:
    st.info("👋 فایل اکسل را آپلود کنید تا تحلیل هوشمند فعال شود.")
