import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ۱. تنظیمات پایه صفحه و استایل‌های سفارشی (RTL و فونت)
st.set_page_config(page_title="داشبورد جامع مالی", layout="wide", page_icon="💎")

st.markdown("""
<style>
    * { direction: rtl; font-family: Tahoma; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    
    /* تنظیمات مخصوص موبایل */
    @media (max-width: 768px) {
        div[data-testid="stMetricValue"] > div { font-size: 1.1rem !important; }
        div[data-testid="stMetricLabel"] > div { font-size: 0.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# توابع کمکی
# ---------------------------------------------------------

@st.cache_data 
def clean_data(file):
    """پاکسازی و آماده‌سازی داده‌های اکسل"""
    df = pd.read_excel(file, header=3)
    df = df.dropna(subset=['تاریخ'], how='all')

    def normalize_date(val):
        s = str(val).split(' ')[0].strip()
        parts = s.replace('-', '/').split('/')
        try:
            y, m, d = (int(p) for p in parts[:3])
            return f"{y:04d}/{m:02d}/{d:02d}"
        except (ValueError, TypeError):
            return s

    df['تاریخ'] = df['تاریخ'].apply(normalize_date)

    def clean_money(val):
        if pd.isna(val) or val == '-':
            return 0
        return int(str(val).replace(',', '').strip())

    df['واریز (ریال)'] = df['واریز (ریال)'].apply(clean_money)
    df['برداشت (ریال)'] = df['برداشت (ریال)'].apply(clean_money)
    df['تراز خالص'] = df['واریز (ریال)'] - df['برداشت (ریال)']

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
    df['مرکز'] = df['مرکز'].astype(str).str.strip()
    df = df.sort_values('تاریخ')

    cols_to_keep = ['تاریخ', 'واریز (ریال)', 'برداشت (ریال)', 'تراز خالص', 'ماهیت', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی']
    return df[cols_to_keep]

def format_currency(num):
    """فرمت‌دهی اعداد به صورت خوانا (همت، میلیارد، میلیون)"""
    if abs(num) >= 1_000_000_000_000:
        return f"{num / 1_000_000_000_000:.2f} همت"
    elif abs(num) >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f} میلیارد"
    elif abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.2f} میلیون"
    else:
        return f"{num:,.0f}"

def build_tab_content(tab_data, tab_key):
    """ساختار محتوای هر تب (تحلیل مرکز)"""
    if tab_data.empty:
        st.info("داده‌ای برای این مرکز در این بازه زمانی وجود ندارد.")
        return

    custom_template = "plotly_white"
    
    # ۱. نقشه درختی هزینه‌ها
    expense_data = tab_data[tab_data['برداشت (ریال)'] > 0]
    if not expense_data.empty:
        fig_tree = px.treemap(
            expense_data, path=['کلاس', 'جزئیات'], values='برداشت (ریال)',
            color='برداشت (ریال)', color_continuous_scale='Reds',
            title="🟥 نقشه درختی هزینه‌ها (برای جزئیات کلیک کنید)", 
            template=custom_template, height=500
        )
        fig_tree.update_traces(textinfo="label+value+percent parent", texttemplate="<b>%{label}</b><br>%{value:,.0f} ریال")
        st.plotly_chart(fig_tree, use_container_width=True)

        # ۲. نمودار میله‌ای ۱۰ هزینه برتر
        top_10 = expense_data.groupby('جزئیات')['برداشت (ریال)'].sum().nlargest(10).reset_index()
        fig_bar = px.bar(
            top_10, x='برداشت (ریال)', y='جزئیات', orientation='h', text='برداشت (ریال)',
            title="🔥 ۱۰ رکورد اصلی هزینه‌ها", color='برداشت (ریال)', color_continuous_scale='Reds',
            template=custom_template, height=400
        )
        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, xaxis={'visible': False})
        st.plotly_chart(fig_bar, use_container_width=True)

    # ۳. کاوشگر Drill-down
    st.markdown("#### 🧮 کاوشگر ریز آمار")
    unique_classes = sorted([c for c in tab_data['کلاس'].unique() if str(c) not in ['-', 'nan']])
    selected_drill_class = st.selectbox("یک کلاس را انتخاب کنید:", ["نمایش همه"] + unique_classes, key=f"drill_{tab_key}")

    if selected_drill_class == "نمایش همه":
        c1, c2 = st.columns(2)
        with c1:
            st.write("**خلاصه بر اساس کلاس:**")
            st.dataframe(tab_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum(), use_container_width=True)
        with c2:
            st.write("**خلاصه بر اساس جزئیات:**")
            st.dataframe(tab_data.groupby('جزئیات')[['واریز (ریال)', 'برداشت (ریال)']].sum(), use_container_width=True)
    else:
        class_df = tab_data[tab_data['کلاس'] == selected_drill_class]
        drill_grouped = class_df.groupby(['جزئیات', 'تکمیلی'])[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
        st.dataframe(drill_grouped.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}'}), use_container_width=True)

# ---------------------------------------------------------
# بدنه اصلی اپلیکیشن
# ---------------------------------------------------------
st.title("💎 داشبورد جامع و هوشمند مالی")
st.markdown("---")

st.sidebar.title("⚙️ تنظیمات")
uploaded_file = st.sidebar.file_uploader("📥 آپلود فایل اکسل خام", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = clean_data(uploaded_file)
        st.sidebar.success("✅ فایل پردازش شد")
        
        # فیلترها
        dates = df['تاریخ'].unique().tolist()
        start_date, end_date = st.sidebar.select_slider("📅 بازه زمانی:", options=dates, value=(dates[0], dates[-1]))
        
        filtered_df = df[
            (df['تاریخ'] >= start_date) & 
            (df['تاریخ'] <= end_date)
        ]

        # ۱. شاخص‌های کلان (KPIs)
        total_inc = filtered_df['واریز (ریال)'].sum()
        total_exp = filtered_df['برداشت (ریال)'].sum()
        net_bal = total_inc - total_exp

        st.markdown("### 📊 شاخص‌های کلیدی عملکرد")
        k1, k2, k3 = st.columns(3)
        k1.metric("🟢 مجموع درآمد", format_currency(total_inc))
        k2.metric("🔴 مجموع هزینه‌ها", format_currency(total_exp))
        k3.metric("🔵 موجودی نهایی", format_currency(net_bal))
        
        st.divider()

        # ۲. نمودارهای روند
        st.markdown("### 🌊 روند نقدینگی")
        t1, t2 = st.tabs(["📈 روند روزانه", "💰 موجودی تجمعی"])
        
        with t1:
            daily = filtered_df.groupby('تاریخ')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(x=daily['تاریخ'], y=daily['واریز (ریال)'], fill='tozeroy', name='درآمد', line=dict(color='#2ecc71')))
            fig_daily.add_trace(go.Scatter(x=daily['تاریخ'], y=daily['برداشت (ریال)'], fill='tozeroy', name='هزینه', line=dict(color='#e74c3c')))
            st.plotly_chart(fig_daily, use_container_width=True)
            
        with t2:
            daily['تجمعی'] = (daily['واریز (ریال)'] - daily['برداشت (ریال)']).cumsum()
            fig_cum = px.area(daily, x='تاریخ', y='تجمعی', title="روند موجودی تجمعی", color_discrete_sequence=['#3498db'])
            st.plotly_chart(fig_cum, use_container_width=True)

        st.divider()

        # ۳. تحلیل تفکیکی مراکز
        st.markdown("### 📑 تحلیل تفکیکی مراکز")
        tabs = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه"])
        with tabs[0]:
            build_tab_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "personal")
        with tabs[1]:
            build_tab_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "work")

        st.divider()

        # ۴. بینش هوشمند
        st.markdown("### 💡 بینش هوشمند و هشدار")
        if total_inc > 0:
            s_rate = (net_bal / total_inc) * 100
            if s_rate > 0: st.success(f"**وضعیت پس‌انداز:** شما **{s_rate:.1f}٪** درآمد را حفظ کرده‌اید.")
            else: st.error(f"**هشدار:** هزینه‌ها **{abs(s_rate):.1f}٪** بیش از درآمد است!")

        # شناسایی تراکنش‌های مشکوک (Outliers)
        exp_df = filtered_df[filtered_df['برداشت (ریال)'] > 0]
        if not exp_df.empty:
            threshold = exp_df['برداشت (ریال)'].mean() + (2 * exp_df['برداشت (ریال)'].std())
            outliers = exp_df[exp_df['برداشت (ریال)'] > threshold]
            if not outliers.empty:
                st.warning(f"🚨 **تراکنش‌های غیرعادی:** {len(outliers)} مورد با مبلغ بسیار بالا شناسایی شد.")
                st.dataframe(outliers[['تاریخ', 'جزئیات', 'برداشت (ریال)']], use_container_width=True)

    except Exception as e:
        st.error(f"❌ خطای سیستم: {e}")
else:
    st.info("👋 برای شروع، لطفاً فایل اکسل را از منوی سمت راست آپلود کنید.")
