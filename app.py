import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ۱. تنظیمات پایه و استایل‌های حرفه‌ای (RTL و فونت)
st.set_page_config(page_title="LedgerLens | داشبورد مالی", layout="wide", page_icon="💎")

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
    .kpi-value { font-size: 22px; font-weight: bold; color: #1E1E1E; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# تابع اصلی پاکسازی داده‌ها (حفظ دقیق منطق شما)
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
    df['تراز خالص'] = df['واریز (ریال)'] - df['برداشت (ریال)']

    def split_tags(text):
        if pd.isna(text) or str(text).strip() == '': return ['-', '-', '-', '-', '-']
        parts = str(text).strip('/').split('/')
        while len(parts) < 5: parts.append('-')
        return parts[:5]

    tags_df = df['توضیحات کاربر'].apply(split_tags).apply(pd.Series)
    tags_df.columns = ['ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی']
    df = pd.concat([df, tags_df], axis=1)
    df['مرکز'] = df['مرکز'].astype(str).str.strip()
    return df.sort_values('تاریخ')

# ---------------------------------------------------------
# تابع ساخت محتوای تب‌ها (برگشت به سبک قبلی - ماتریس داده‌ها)
# ---------------------------------------------------------
def build_tab_content(tab_data, tab_key):
    if tab_data.empty:
        st.info("داده‌ای برای این مرکز وجود ندارد.")
        return

    # ۱. نقشه درختی
    expense_data = tab_data[tab_data['برداشت (ریال)'] > 0]
    if not expense_data.empty:
        fig_tree = px.treemap(expense_data, path=['کلاس', 'جزئیات'], values='برداشت (ریال)', 
                             color='برداشت (ریال)', color_continuous_scale='Reds', height=450)
        st.plotly_chart(fig_tree, use_container_width=True)
    
    st.divider()

    # ۲. کاوشگر ریز آمار (همان سبک قبلی که می‌خواستید)
    st.markdown("#### 🧮 کاوشگر ریز آمار")
    unique_classes = sorted([c for c in tab_data['کلاس'].unique() if str(c) not in ['-', 'nan']])
    selected_drill = st.selectbox("انتخاب کلاس برای مشاهده جزئیات:", ["نمایش همه"] + unique_classes, key=f"dr_{tab_key}")

    if selected_drill == "نمایش همه":
        c1, c2 = st.columns(2)
        with c1:
            st.write("**خلاصه کلاس:**")
            st.dataframe(tab_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)
        with c2:
            st.write("**خلاصه جزئیات:**")
            st.dataframe(tab_data.groupby('جزئیات')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)
    else:
        class_df = tab_data[tab_data['کلاس'] == selected_drill]
        drill_grouped = class_df.groupby(['جزئیات', 'تکمیلی'])[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
        st.dataframe(drill_grouped.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens Pro")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل", type=['xlsx'])

if uploaded_file:
    df = clean_data(uploaded_file)
    
    # فیلترها
    dates = df['تاریخ'].unique().tolist()
    date_range = st.sidebar.select_slider("بازه زمانی", options=dates, value=(dates[0], dates[-1]))
    filtered_df = df[(df['تاریخ'] >= date_range[0]) & (df['تاریخ'] <= date_range[1])]

    # ۱. کارت‌های شاخص (KPIs)
    total_inc = filtered_df['واریز (ریال)'].sum()
    total_exp = filtered_df['برداشت (ریال)'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        st.markdown(f'<div class="kpi-card" style="border-right-color: #2ecc71;"><div class="kpi-label">مجموع درآمد</div><div class="kpi-value">{total_inc:,.0f} <small>ریال</small></div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card" style="border-right-color: #e74c3c;"><div class="kpi-label">مجموع هزینه‌ها</div><div class="kpi-value">{total_exp:,.0f} <small>ریال</small></div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-card" style="border-right-color: #3498db;"><div class="kpi-label">تراز نهایی</div><div class="kpi-value">{(total_inc - total_exp):,.0f} <small>ریال</small></div></div>', unsafe_allow_html=True)

    # ۲. نمودار دونات یکپارچه
    st.markdown("### 🍩 نسبت منابع و مصارف")
    p_exp = filtered_df[filtered_df['مرکز'] == 'شخصی']['برداشت (ریال)'].sum()
    w_exp = filtered_df[filtered_df['مرکز'] == 'کارگاه']['برداشت (ریال)'].sum()
    fig_donut = px.pie(names=['درآمد', 'هزینه کارگاه', 'هزینه شخصی'], values=[total_inc, w_exp, p_exp], hole=0.5,
                       color_discrete_sequence=['#2ecc71', '#e74c3c', '#f39c12'])
    st.plotly_chart(fig_donut, use_container_width=True)

    # ۳. تب‌های تحلیلی و لیست تراکنش‌ها
    st.markdown("### 📑 جداول و تحلیل تراکنش‌ها")
    tab1, tab2, tab3 = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه", "📋 لیست کل تراکنش‌ها"])

    with tab1:
        build_tab_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "p")
    
    with tab2:
        build_tab_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "w")

    with tab3:
        st.write("**لیست کامل تراکنش‌های فیلتر شده:**")
        # نمایش به سبک کلاسیک st.dataframe با فرمت هزارگان
        st.dataframe(
            filtered_df[['تاریخ', 'مرکز', 'کلاس', 'جزئیات', 'واریز (ریال)', 'برداشت (ریال)', 'تکمیلی']]
            .style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), 
            use_container_width=True
        )

else:
    st.info("👋 خوش آمدید! لطفاً فایل اکسل خود را بارگذاری کنید.")
