import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ۱. تنظیمات پایه و تم اختصاصی هوشا
st.set_page_config(page_title="LedgerLens AI | هوش مالی", layout="wide", page_icon="💎")

st.markdown("""
<style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { direction: rtl; font-family: 'Vazir', sans-serif; }
    
    /* استایل کارت‌های شاخص هوشمند */
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
    .insight-box {
        background: #f0f7ff;
        border: 1px solid #cce5ff;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# توابع منطقی و نوآوری‌های محاسباتی
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
    
    # نوآوری: محاسبه موجودی لحظه‌ای (Cumulative Sum)
    df = df.sort_values('تاریخ')
    df['موجودی_لحظه‌ای'] = df['واریز (ریال)'].cumsum() - df['برداشت (ریال)'].cumsum()
    return df

def detect_anomalies(df):
    """نوآوری: شناسایی مخارج مشکوک بر اساس انحراف معیار"""
    expenses = df[df['برداشت (ریال)'] > 0]
    if expenses.empty: return pd.DataFrame()
    
    # مخارجی که بیش از ۲ برابر انحراف معیار از میانگین فاصله دارند
    mean = expenses['برداشت (ریال)'].mean()
    std = expenses['برداشت (ریال)'].std()
    threshold = mean + (2 * std)
    
    anomalies = expenses[expenses['برداشت (ریال)'] > threshold]
    return anomalies

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens AI Ultra")
st.caption("تحلیل‌گر هوشمند منابع مالی | قدرت گرفته از هوشا")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل", type=['xlsx'])

if uploaded_file:
    df = clean_data(uploaded_file)
    
    # فیلتر بازه زمانی
    dates = df['تاریخ'].unique().tolist()
    d_range = st.sidebar.select_slider("📅 انتخاب بازه گزارش", options=dates, value=(dates[0], dates[-1]))
    filtered_df = df[(df['تاریخ'] >= d_range[0]) & (df['تاریخ'] <= d_range[1])]

    # ۱. ردیف KPIs ارتقا یافته
    ti, te = filtered_df['واریز (ریال)'].sum(), filtered_df['برداشت (ریال)'].sum()
    savings_rate = ((ti - te) / ti * 100) if ti > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="kpi-card" style="border-right-color: #2ecc71;"><div class="kpi-label">درآمد کل</div><div class="kpi-value">{ti:,.0f}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card" style="border-right-color: #e74c3c;"><div class="kpi-label">هزینه کل</div><div class="kpi-value">{te:,.0f}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card" style="border-right-color: #3498db;"><div class="kpi-label">تراز نهایی</div><div class="kpi-value">{(ti - te):,.0f}</div></div>', unsafe_allow_html=True)
    with c4: 
        health_color = "#2ecc71" if savings_rate > 20 else "#f39c12" if savings_rate > 0 else "#e74c3c"
        st.markdown(f'<div class="kpi-card" style="border-right-color: {health_color};"><div class="kpi-label">نرخ پس‌انداز</div><div class="kpi-value">{savings_rate:.1f}%</div></div>', unsafe_allow_html=True)

    # ۲. نوآوری: نمودار جریان نقدینگی انباشته (Trend)
    st.subheader("📈 روند تغییرات موجودی در بازه انتخاب شده")
    fig_trend = px.area(filtered_df, x='تاریخ', y='موجودی_لحظه‌ای', 
                        title="نمودار جریان نقدینگی (Cumulative Cashflow)",
                        line_shape="spline", color_discrete_sequence=['#0068c9'])
    st.plotly_chart(fig_trend, use_container_width=True)

    # ۳. تب‌های تحلیل پیشرفته
    st.markdown("### 📑 کاوشگر هوشمند")
    tab_insight, tab_personal, tab_work, tab_search = st.tabs([
        "🧠 بینش هوشمند (AI)", "👤 حساب شخصی", "🏭 حساب کارگاه", "🔍 جستجوی تراکنش"
    ])

    with tab_insight:
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown("#### 🚨 رادار ناهنجاری")
            anomalies = detect_anomalies(filtered_df)
            if not anomalies.empty:
                st.warning(f"سیستم {len(anomalies)} تراکنش مشکوک (خارج از الگوی عادی) پیدا کرد.")
                st.dataframe(anomalies[['تاریخ', 'کلاس', 'جزئیات', 'برداشت (ریال)']].style.format("{:,.0f}"), use_container_width=True)
            else:
                st.success("الگوی مخارج شما کاملاً پایدار است.")
        
        with col_in2:
            st.markdown("#### 🏆 ۵ چاله پولی اصلی")
            top_5 = filtered_df[filtered_df['برداشت (ریال)'] > 0].groupby('جزئیات')['برداشت (ریال)'].sum().nlargest(5).reset_index()
            fig_top = px.bar(top_5, x='برداشت (ریال)', y='جزئیات', orientation='h', color='برداشت (ریال)', color_continuous_scale='Reds')
            st.plotly_chart(fig_top, use_container_width=True)

    with tab_personal:
        # استفاده از تابع شما با کمی بهبود بصری
        p_data = filtered_df[filtered_df['مرکز'] == 'شخصی']
        if not p_data.empty:
            st.plotly_chart(px.treemap(p_data[p_data['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)', title="توزیع مخارج شخصی"), use_container_width=True)
        else: st.info("داده‌ای موجود نیست.")

    with tab_work:
        w_data = filtered_df[filtered_df['مرکز'] == 'کارگاه']
        if not w_data.empty:
            st.plotly_chart(px.treemap(w_data[w_data['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)', title="توزیع مخارج کارگاه"), use_container_width=True)
        else: st.info("داده‌ای موجود نیست.")

    with tab_search:
        search_query = st.text_input("🔎 جستجو در توضیحات، کلاس یا جزئیات:")
        if search_query:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            st.dataframe(filtered_df[mask].style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True)
        else:
            st.write("برای جستجو، کلمه‌ای تایپ کنید...")

else:
    st.markdown("""
    <div style="text-align: center; padding: 100px;">
        <h2 style="color: #0068c9;">💎 به LedgerLens AI خوش آمدید</h2>
        <p>لطفاً فایل اکسل بانکی خود را برای تحلیل هوشمند بارگذاری کنید.</p>
    </div>
    """, unsafe_allow_html=True)
