import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# ۱. تنظیمات پایه و استایل‌های حرفه‌ای (RTL و فونت وزیر)
st.set_page_config(page_title="LedgerLens | Pro Financial Dashboard", layout="wide", page_icon="💎")

st.markdown("""
<style>
    @import url('https://v1.fontapi.ir/css/Vazir');
    * { direction: rtl; font-family: 'Vazir', sans-serif; }
    
    /* استایل اختصاصی کارت‌های KPI */
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
    
    /* بهینه‌سازی تب‌ها */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #0068c9 !important; color: white !important; }
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
# توابع کمکی UI
# ---------------------------------------------------------
def format_currency(num):
    if abs(num) >= 1_000_000_000: return f"{num / 1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000: return f"{num / 1_000_000:.1f}M"
    else: return f"{num:,.0f}"

def kpi_card(label, value, color="#0068c9"):
    st.markdown(f"""
        <div class="kpi-card" style="border-right-color: {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def display_pro_grid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_pagination(paginationPageSize=10)
    # راست‌چین کردن ستون‌های مالی و فرمت ۳ رقم ۳ رقم
    gb.configure_column('واریز (ریال)', cellStyle={'textAlign': 'right'}, valueFormatter="x.toLocaleString()")
    gb.configure_column('برداشت (ریال)', cellStyle={'textAlign': 'right'}, valueFormatter="x.toLocaleString()")
    grid_options = gb.build()
    return AgGrid(df, gridOptions=grid_options, theme="alpine", columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, height=350)

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens Pro")
st.caption("سیستم تحلیل هوشمند تراکنش‌های مالی | نسخه سازمانی")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل", type=['xlsx'])

if uploaded_file:
    try:
        df = clean_data(uploaded_file)
        
        # سایدبار: فیلترها
        st.sidebar.header("🔍 فیلترهای گزارش")
        dates = df['تاریخ'].unique().tolist()
        date_range = st.sidebar.select_slider("بازه زمانی", options=dates, value=(dates[0], dates[-1]))
        
        filtered_df = df[(df['تاریخ'] >= date_range[0]) & (df['تاریخ'] <= date_range[1])]

        # ۱. ردیف شاخص‌های کلیدی (KPIs)
        total_inc = filtered_df['واریز (ریال)'].sum()
        total_exp = filtered_df['برداشت (ریال)'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1: kpi_card("مجموع درآمد", format_currency(total_inc), "#2ecc71")
        with col2: kpi_card("مجموع هزینه‌ها", format_currency(total_exp), "#e74c3c")
        with col3: kpi_card("تراز خالص نهایی", format_currency(total_inc - total_exp), "#3498db")

        # ۲. نمودار دونات یکپارچه (سه قسمتی)
        st.markdown("### 🍩 ساختار کلی منابع و مصارف")
        p_exp = filtered_df[filtered_df['مرکز'] == 'شخصی']['برداشت (ریال)'].sum()
        w_exp = filtered_df[filtered_df['مرکز'] == 'کارگاه']['برداشت (ریال)'].sum()
        
        fig_donut = px.pie(
            names=['درآمد کل', 'هزینه کارگاه', 'هزینه شخصی'],
            values=[total_inc, w_exp, p_exp],
            hole=0.5,
            color_discrete_map={'درآمد کل': '#2ecc71', 'هزینه کارگاه': '#e74c3c', 'هزینه شخصی': '#f39c12'}
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # ۳. تحلیل تفکیکی در تب‌ها
        st.markdown("### 📑 تحلیل جزئیات تراکنش‌ها")
        tab1, tab2, tab3 = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه", "📋 کل تراکنش‌ها (Grid)"])

        with tab1:
            p_df = filtered_df[filtered_df['مرکز'] == 'شخصی']
            if not p_df.empty:
                fig_p = px.treemap(p_df[p_df['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)', title="توزیع هزینه‌های شخصی")
                st.plotly_chart(fig_p, use_container_width=True)
            else: st.info("تراکنی در بخش شخصی یافت نشد.")

        with tab2:
            w_df = filtered_df[filtered_df['مرکز'] == 'کارگاه']
            if not w_df.empty:
                fig_w = px.treemap(w_df[w_df['برداشت (ریال)']>0], path=['کلاس', 'جزئیات'], values='برداشت (ریال)', title="توزیع هزینه‌های کارگاه")
                st.plotly_chart(fig_w, use_container_width=True)
            else: st.info("تراکنی در بخش کارگاه یافت نشد.")

        with tab3:
            st.info("💡 در این جدول می‌توانید روی هر ستون فیلترهای دلخواه (مثل اکسل) اعمال کنید.")
            display_pro_grid(filtered_df[['تاریخ', 'مرکز', 'کلاس', 'جزئیات', 'واریز (ریال)', 'برداشت (ریال)']])

    except Exception as e:
        st.error(f"❌ خطایی در پردازش رخ داد: {e}")
else:
    st.info("👋 خوش آمدید! لطفاً برای شروع فایل اکسل خود را بارگذاری کنید.")
