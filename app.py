import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ۱. تنظیمات پایه و استایل‌های موبایل-فرست
st.set_page_config(page_title="LedgerLens AI Ultra", layout="wide", page_icon="💎")

st.markdown("""
<style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { direction: rtl; font-family: 'Vazir', sans-serif; }
    
    /* بهینه‌سازی کارت‌ها برای نمایش در موبایل */
    .kpi-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        text-align: center;
        border-right: 6px solid #0068c9;
    }
    .kpi-label { font-size: 13px; color: #666; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #1E1E1E; margin-top: 5px; }
    
    /* حذف حاشیه‌های اضافی در موبایل */
    .main .block-container { padding: 1rem; }
    [data-testid="stHeader"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# توابع منطقی (بدون تغییر در محاسبات)
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

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens Pro")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل", type=['xlsx'])

if uploaded_file:
    df = clean_data(uploaded_file)
    
    # فیلتر بازه گزارش در سایدبار (مخصوص موبایل)
    dates = df['تاریخ'].unique().tolist()
    d_range = st.sidebar.select_slider("📅 بازه گزارش", options=dates, value=(dates[0], dates[-1]))
    filtered_df = df[(df['تاریخ'] >= d_range[0]) & (df['تاریخ'] <= d_range[1])]

    # ۱. شاخص‌ها (KPIs) - چیدمان عمودی برای موبایل
    ti, te = filtered_df['واریز (ریال)'].sum(), filtered_df['برداشت (ریال)'].sum()
    bal = ti - te
    s_rate = ((ti - te) / ti * 100) if ti > 0 else 0
    
    # نمایش کارت‌ها (در موبایل زیر هم می‌آیند)
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card" style="border-right-color: #2ecc71;">
            <div class="kpi-label">درآمد کل</div><div class="kpi-value">{ti:,.0f}</div>
        </div>
        <div class="kpi-card" style="border-right-color: #e74c3c;">
            <div class="kpi-label">هزینه کل</div><div class="kpi-value">{te:,.0f}</div>
        </div>
        <div class="kpi-card" style="border-right-color: #3498db;">
            <div class="kpi-label">تراز نهایی</div><div class="kpi-value">{bal:,.0f}</div>
        </div>
        <div class="kpi-card" style="border-right-color: #f39c12;">
            <div class="kpi-label">نرخ پس‌انداز</div><div class="kpi-value">{s_rate:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ۲. نمودار Trend (بهینه‌سازی شده برای عرض کم)
    st.markdown("### 📈 روند موجودی")
    fig_trend = px.area(filtered_df, x='تاریخ', y='موجودی_لحظه‌ای', color_discrete_sequence=['#0068c9'])
    fig_trend.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
    st.plotly_chart(fig_trend, use_container_width=True)

    # ۳. تب‌ها با استایل موبایلی
    tab1, tab2, tab3 = st.tabs(["👤 شخصی", "🏭 کارگاه", "🔍 جستجو"])

    with tab1:
        p_df = filtered_df[filtered_df['مرکز'] == 'شخصی']
        if not p_df.empty:
            fig_p = px.treemap(p_df[p_df['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)')
            fig_p.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(p_df.groupby('کلاس')[['برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)

    with tab2:
        w_df = filtered_df[filtered_df['مرکز'] == 'کارگاه']
        if not w_df.empty:
            fig_w = px.treemap(w_df[w_df['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)')
            fig_w.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_w, use_container_width=True)
            st.dataframe(w_df.groupby('کلاس')[['برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)

    with tab3:
        query = st.text_input("🔍 جستجوی تراکنش:")
        if query:
            res = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)]
            st.dataframe(res[['تاریخ', 'کلاس', 'جزئیات', 'برداشت (ریال)']].style.format({'برداشت (ریال)': '{:,.0f}'}), use_container_width=True)

else:
    st.info("👋 حاجی خوش آمدی! اکسل رو آپلود کن.")
