import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ۱. تنظیمات پایه و استایل‌های حرفه‌ای (RTL و فونت وزیر)
st.set_page_config(page_title="LedgerLens | داشبورد مالی پرو", layout="wide", page_icon="💎")

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
    .kpi-value { font-size: 24px; font-weight: bold; color: #1E1E1E; }
    
    /* حذف حاشیه‌های اضافی */
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# توابع اعتبارسنجی و پاکسازی (لایه امنیتی و منطق اصلی)
# ---------------------------------------------------------
def validate_excel_structure(file):
    """بررسی ساختار فایل قبل از پردازش برای جلوگیری از کراش"""
    try:
        temp_df = pd.read_excel(file, header=3, nrows=0)
        required = ['تاریخ', 'توضیحات کاربر', 'واریز (ریال)', 'برداشت (ریال)']
        missing = [c for c in required if c not in temp_df.columns]
        if missing:
            return False, f"ستون‌های ضروری یافت نشد: {', '.join(missing)}"
        return True, ""
    except:
        return False, "فایل اکسل معتبر نیست."

@st.cache_data 
def clean_data(file):
    # ۱. ابتدا اعتبارسنجی ساختار
    is_valid, err_msg = validate_excel_structure(file)
    if not is_valid:
        st.error(f"❌ **خطا در فرمت فایل:** {err_msg}")
        st.info("💡 فایل باید دارای ستون‌های 'تاریخ' و 'توضیحات کاربر' در ردیف ۴ باشد.")
        st.stop()

    # ۲. پردازش داده‌ها (منطق حساس شما)
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
# توابع کمکی UI و کاوشگر
# ---------------------------------------------------------
def kpi_card(label, value, color="#0068c9"):
    st.markdown(f"""
        <div class="kpi-card" style="border-right-color: {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value:,.0f} <small style="font-size:12px;">ریال</small></div>
        </div>
    """, unsafe_allow_html=True)

def build_explorer_content(data, key_suffix, title_prefix=""):
    if data.empty:
        st.info(f"داده‌ای برای {title_prefix} وجود ندارد.")
        return

    # نقشه درختی هزینه‌ها
    exp_data = data[data['برداشت (ریال)'] > 0]
    if not exp_data.empty:
        fig_tree = px.treemap(exp_data, path=['کلاس', 'جزئیات'], values='برداشت (ریال)', 
                             color='برداشت (ریال)', color_continuous_scale='Reds', height=400)
        st.plotly_chart(fig_tree, use_container_width=True)
    
    st.divider()

    # کاوشگر Drill-down
    st.markdown(f"#### 🧮 کاوشگر ریز آمار {title_prefix}")
    classes = sorted([c for c in data['کلاس'].unique() if str(c) not in ['-', 'nan']])
    sel_class = st.selectbox("انتخاب دسته‌بندی:", ["نمایش همه"] + classes, key=f"sel_{key_suffix}")

    if sel_class == "نمایش همه":
        c1, c2 = st.columns(2)
        with c1:
            st.write("**خلاصه کلاس:**")
            st.dataframe(data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)
        with c2:
            st.write("**خلاصه جزئیات:**")
            st.dataframe(data.groupby('جزئیات')[['واریز (ریال)', 'برداشت (ریال)']].sum().style.format("{:,.0f}"), use_container_width=True)
    else:
        filtered = data[data['کلاس'] == sel_class]
        drill = filtered.groupby(['جزئیات', 'تکمیلی'])[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
        st.dataframe(drill.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# بدنه اصلی داشبورد
# ---------------------------------------------------------
st.title("💎 LedgerLens Pro")
st.caption("تحلیل‌گر پیشرفته جریان نقدینگی | نسخه سازمانی")

uploaded_file = st.sidebar.file_uploader("📂 بارگذاری فایل اکسل (خروجی خام)", type=['xlsx'])

if uploaded_file:
    df = clean_data(uploaded_file)
    
    # سایدبار: فیلترها
    st.sidebar.header("🔍 فیلترهای زمانی")
    dates = df['تاریخ'].unique().tolist()
    d_range = st.sidebar.select_slider("بازه گزارش", options=dates, value=(dates[0], dates[-1]))
    filtered_df = df[(df['تاریخ'] >= d_range[0]) & (df['تاریخ'] <= d_range[1])]

    # ۱. ردیف شاخص‌های کلیدی
    t_inc = filtered_df['واریز (ریال)'].sum()
    t_exp = filtered_df['برداشت (ریال)'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1: kpi_card("درآمد کل", t_inc, "#2ecc71")
    with col2: kpi_card("هزینه کل", t_exp, "#e74c3c")
    with col3: kpi_card("موجودی تراز", (t_inc - t_exp), "#3498db")

    # ۲. نمودار دونات مرکزی
    st.divider()
    p_exp = filtered_df[filtered_df['مرکز'] == 'شخصی']['برداشت (ریال)'].sum()
    w_exp = filtered_df[filtered_df['مرکز'] == 'کارگاه']['برداشت (ریال)'].sum()
    fig_donut = px.pie(names=['درآمد', 'هزینه کارگاه', 'هزینه شخصی'], values=[t_inc, w_exp, p_exp], hole=0.5,
                       color_discrete_sequence=['#2ecc71', '#e74c3c', '#f39c12'], title="⚖️ نسبت منابع و مصارف")
    st.plotly_chart(fig_donut, use_container_width=True)

    # ۳. تب‌های تحلیل و کاوش
    st.markdown("### 📑 تحلیل و کاوش عمیق داده‌ها")
    tab1, tab2, tab3 = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه", "🔍 کاوشگر هوشمند کل"])

    with tab1:
        build_explorer_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "p", "شخصی")
    
    with tab2:
        build_explorer_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "w", "کارگاه")

    with tab3:
        # کاوشگر برای کل داده‌ها
        build_explorer_content(filtered_df, "all", "کل منابع")
        
        # لیست خام تراکنش‌ها در انتهای همین تب
        with st.expander("📋 مشاهده لیست خام تمام تراکنش‌های فیلتر شده"):
            st.dataframe(filtered_df.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True)

else:
    st.info("👋 خوش آمدید! لطفاً برای شروع، فایل اکسل خود را بارگذاری کنید.")
