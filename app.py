import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ۱. تنظیمات پایه صفحه و استایل RTL
st.set_page_config(page_title="داشبورد جامع مالی", layout="wide", page_icon="💎")
st.markdown("""
<style>
    * { direction: rtl; font-family: Tahoma; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# تابع پاکسازی داده‌ها - دقیقاً طبق منطق کد اول شما
# ---------------------------------------------------------
@st.cache_data 
def clean_data(file):
    # خواندن فایل از سطر ۴ (header=3)
    df = pd.read_excel(file, header=3)
    df = df.dropna(subset=['تاریخ'], how='all')

    # نرمال‌سازی تاریخ
    def normalize_date(val):
        s = str(val).split(' ')[0].strip()
        parts = s.replace('-', '/').split('/')
        try:
            y, m, d = (int(p) for p in parts[:3])
            return f"{y:04d}/{m:02d}/{d:02d}"
        except (ValueError, TypeError):
            return s
    df['تاریخ'] = df['تاریخ'].apply(normalize_date)

    # تمیز کردن مبالغ (حذف کاما و مدیریت خط تیره)
    def clean_money(val):
        if pd.isna(val) or val == '-':
            return 0
        return int(str(val).replace(',', '').strip())

    df['واریز (ریال)'] = df['واریز (ریال)'].apply(clean_money)
    df['برداشت (ریال)'] = df['برداشت (ریال)'].apply(clean_money)
    df['تراز خالص'] = df['واریز (ریال)'] - df['برداشت (ریال)']

    # منطق شکستن تگ‌ها به ۵ ستون اصلی
    def split_tags(text):
        if pd.isna(text) or str(text).strip() == '':
            return ['-', '-', '-', '-', '-']
        parts = str(text).strip('/').split('/')
        while len(parts) < 5:
            parts.append('-')
        return parts[:5]

    tags_df = df['توضیحات کاربر'].apply(split_tags).apply(pd.Series)
    tags_df.columns = ['ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی']

    df = pd.concat([df, tags_df], axis=1)
    
    cols = ['ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی']
    df[cols] = df[cols].fillna('-')
    df['مرکز'] = df['مرکز'].astype(str).str.strip()
    df = df.sort_values('تاریخ')

    columns_to_keep = [
        'تاریخ', 'واریز (ریال)', 'برداشت (ریال)', 'تراز خالص', 
        'ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی'
    ]
    return df[columns_to_keep]

# ---------------------------------------------------------
# تابع ساخت محتوای تب‌ها (حذف میله‌ای - حفظ نقشه درختی و جدول)
# ---------------------------------------------------------
def build_tab_content(tab_data, tab_key):
    if tab_data.empty:
        st.info("داده‌ای برای این مرکز در این بازه زمانی وجود ندارد.")
        return

    # ۱. نقشه درختی هزینه‌ها (Treemap)
    expense_data = tab_data[tab_data['برداشت (ریال)'] > 0]
    if not expense_data.empty:
        fig_tree = px.treemap(
            expense_data, path=['کلاس', 'جزئیات'], values='برداشت (ریال)',
            color='برداشت (ریال)', color_continuous_scale='Reds',
            title="🟥 نقشه درختی هزینه‌ها (سلسله‌مراتب)", 
            template="plotly_white", height=500
        )
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f} ریال")
        st.plotly_chart(fig_tree, use_container_width=True)
    
    st.divider()

    # ۲. کاوشگر ریز آمار (Drill-down)
    st.markdown("#### 🧮 کاوشگر ریز آمار")
    unique_classes = sorted([c for c in tab_data['کلاس'].unique() if str(c) not in ['-', 'nan']])
    selected_drill = st.selectbox("انتخاب کلاس:", ["نمایش همه"] + unique_classes, key=f"dr_{tab_key}")

    if selected_drill == "نمایش همه":
        c1, c2 = st.columns(2)
        with c1:
            st.write("**خلاصه کلاس:**")
            st.dataframe(tab_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum(), use_container_width=True)
        with c2:
            st.write("**خلاصه جزئیات:**")
            st.dataframe(tab_data.groupby('جزئیات')[['واریز (ریال)', 'برداشت (ریال)']].sum(), use_container_width=True)
    else:
        drill_df = tab_data[tab_data['کلاس'] == selected_drill]
        st.dataframe(drill_df.groupby(['جزئیات', 'تکمیلی'])[['واریز (ریال)', 'برداشت (ریال)']].sum(), use_container_width=True)

# ---------------------------------------------------------
# بدنه اصلی برنامه
# ---------------------------------------------------------
def format_currency(num):
    if abs(num) >= 1_000_000_000: return f"{num / 1_000_000_000:.2f} میلیارد"
    elif abs(num) >= 1_000_000: return f"{num / 1_000_000:.2f} میلیون"
    else: return f"{num:,.0f}"

st.title("داشبورد جامع و هوشمند مالی")
st.markdown("---")

uploaded_file = st.sidebar.file_uploader("📥 آپلود فایل اکسل خام", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = clean_data(uploaded_file)
        st.sidebar.success("✅ فایل با موفقیت پردازش شد!")
        
        # فیلترهای پیشرفته کناری (منطق اصلی)
        dates = df['تاریخ'].unique().tolist()
        start_date, end_date = st.sidebar.select_slider("📅 بازه زمانی:", options=dates, value=(dates[0], dates[-1]))
        selected_mahiyat = st.sidebar.multiselect("ماهیت:", df['ماهیت'].unique().tolist(), default=df['ماهیت'].unique().tolist())
        selected_center = st.sidebar.multiselect("مرکز:", df['مرکز'].unique().tolist(), default=df['مرکز'].unique().tolist())

        filtered_df = df[
            (df['تاریخ'] >= start_date) & (df['تاریخ'] <= end_date) &
            (df['ماهیت'].isin(selected_mahiyat)) & (df['مرکز'].isin(selected_center))
        ]

        # ۲. شاخص‌های KPIs
        total_inc = filtered_df['واریز (ریال)'].sum()
        total_exp = filtered_df['برداشت (ریال)'].sum()
        
        st.markdown("### 📊 شاخص‌های کلیدی عملکرد")
        k1, k2, k3 = st.columns(3)
        k1.metric("🟢 درآمد کل", format_currency(total_inc) + " ریال")
        k2.metric("🔴 هزینه کل", format_currency(total_exp) + " ریال")
        k3.metric("🔵 تراز نهایی", format_currency(total_inc - total_exp) + " ریال")
        st.divider()

        # ۳. روندهای زمانی (Line Charts)
        st.markdown("### 🌊 روند نقدینگی")
        t_1, t_2 = st.tabs(["📈 روند درآمد و هزینه", "💰 موجودی تجمعی"])
        with t_1:
            daily = filtered_df.groupby('تاریخ')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(x=daily['تاریخ'], y=daily['واریز (ریال)'], fill='tozeroy', name='درآمد', line=dict(color='#2ecc71')))
            fig_daily.add_trace(go.Scatter(x=daily['تاریخ'], y=daily['برداشت (ریال)'], fill='tozeroy', name='هزینه', line=dict(color='#e74c3c')))
            st.plotly_chart(fig_daily, use_container_width=True)
        with t_2:
            daily['تجمعی'] = (daily['واریز (ریال)'] - daily['برداشت (ریال)']).cumsum()
            fig_cum = px.area(daily, x='تاریخ', y='تجمعی', title="روند موجودی تجمعی", color_discrete_sequence=['#3498db'])
            st.plotly_chart(fig_cum, use_container_width=True)

        st.divider()

        # ۴. نمودار دونات یکپارچه (درخواست: درآمد + هزینه شخصی + هزینه کارگاه)
        st.markdown("### 🍩 نسبت درآمد و تفکیک هزینه‌ها")
        p_exp = filtered_df[filtered_df['مرکز'] == 'شخصی']['برداشت (ریال)'].sum()
        w_exp = filtered_df[filtered_df['مرکز'] == 'کارگاه']['برداشت (ریال)'].sum()

        fig_donut = px.pie(
            names=['درآمد کل', 'هزینه کارگاه', 'هزینه شخصی'],
            values=[total_inc, w_exp, p_exp],
            hole=0.45,
            color_discrete_map={'درآمد کل': '#2ecc71', 'هزینه کارگاه': '#e74c3c', 'هزینه شخصی': '#f1948a'}
        )
        fig_donut.update_traces(textinfo='percent+label', hovertemplate="%{label}: %{value:,.0f} ریال")
        st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        # ۵. تب‌های تحلیل تفکیکی مراکز
        st.markdown("### 📑 تحلیل مراکز")
        tabs = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه"])
        with tabs[0]: build_tab_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "personal")
        with tabs[1]: build_tab_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "work")

        # ۶. سیستم هشدار (Outliers)
        exp_df = filtered_df[filtered_df['برداشت (ریال)'] > 0]
        if not exp_df.empty:
            threshold = exp_df['برداشت (ریال)'].mean() + (2 * exp_df['برداشت (ریال)'].std())
            outliers = exp_df[exp_df['برداشت (ریال)'] > threshold]
            if not outliers.empty:
                st.warning(f"🚨 تراکنش‌های غیرعادی شناسایی شد (بیش از {threshold:,.0f} ریال):")
                st.dataframe(outliers[['تاریخ', 'مرکز', 'کلاس', 'برداشت (ریال)']], use_container_width=True)

    except Exception as e:
        st.error(f"❌ خطایی رخ داد: {e}")
else:
    st.info("👋 برای شروع، فایل اکسل را آپلود کنید.")
