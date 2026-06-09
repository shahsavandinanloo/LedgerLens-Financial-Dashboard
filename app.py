# app.py - Step 3 (Final Integrated Version - Professional UI - Improved Layout)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ۱. تنظیمات پایه صفحه و مخفی کردن المان‌های اضافی استریم‌لیت
st.set_page_config(page_title="داشبورد جامع مالی", layout="wide", page_icon="💎")
hide_st_style = """
<style>
    * { direction: rtl; font-family: Tahoma; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    
    /* تنظیمات مخصوص موبایل */
    @media (max-width: 768px) {
        div[data-testid="stMetricValue"] > div {
            font-size: 1.1rem !important;
        }
        div[data-testid="stMetricLabel"] > div {
            font-size: 0.8rem !important;
        }
    }
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ---------------------------------------------------------
# تابع پاکسازی داده‌ها 
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
# تنظیمات سراسری قالب نمودارهای Plotly
# ---------------------------------------------------------
custom_template = "plotly_white"

# ---------------------------------------------------------
# تابع ساخت محتوای تب‌ها (فقط Treemap + Bar + Drill-down)
# ---------------------------------------------------------
def build_tab_content(tab_data, tab_key):
    if tab_data.empty:
        st.info("داده‌ای برای این مرکز در این بازه زمانی وجود ندارد.")
        return

    t_inc = tab_data['واریز (ریال)'].sum()
    t_exp = tab_data['برداشت (ریال)'].sum()
    t_net = t_inc - t_exp
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # -----------------------------------------------------
    # ردیف اول: نقشه درختی (بزرگ و تمام‌عرض)
    # -----------------------------------------------------
    expense_data = tab_data[tab_data['برداشت (ریال)'] > 0]
    if not expense_data.empty:
        fig_tree = px.treemap(
            expense_data, path=['کلاس', 'جزئیات'], values='برداشت (ریال)',
            color='برداشت (ریال)', color_continuous_scale='Reds',
            title="🟥 نقشه درختی هزینه‌ها (سلسله‌مراتب - برای مشاهده ریز جزئیات کلیک کنید)", 
            template=custom_template, height=550
        )
        fig_tree.update_traces(
            textinfo="label+value+percent parent", 
            texttemplate="<b>%{label}</b><br>%{value:,.0f} ریال", 
            hovertemplate="دسته: %{label}<br>مبلغ: %{value:,.0f} ریال<extra></extra>"
        )
        fig_tree.update_layout(
            margin=dict(t=50, b=20, l=20, r=20),
            title_font_size=18
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("داده‌ای برای نمایش هزینه‌ها وجود ندارد.")

    # -----------------------------------------------------
    # ردیف دوم: نمودار میله‌ای (تمام‌عرض)
    # -----------------------------------------------------
    if not expense_data.empty:
        top_10 = expense_data.groupby('جزئیات')['برداشت (ریال)'].sum().nlargest(10).reset_index()
        fig_bar = px.bar(
            top_10, x='برداشت (ریال)', y='جزئیات', orientation='h', text='برداشت (ریال)',
            title="🔥 ۱۰ رکورد اصلی هزینه‌ها (پرهزینه‌ترین جزئیات)", 
            color='برداشت (ریال)', color_continuous_scale='Reds',
            template=custom_template, height=450
        )
        fig_bar.update_traces(
            texttemplate=' %{text:,.0f} ', 
            textposition='outside', 
            hovertemplate="%{y}: %{x:,.0f} ریال<extra></extra>"
        )
        fig_bar.update_layout(
            yaxis={'categoryorder': 'total ascending', 'showgrid': False}, 
            xaxis={'showgrid': False, 'visible': False}, 
            yaxis_title=None, xaxis_title=None, 
            margin=dict(t=50, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ====== بخش کاوشگر ریز آمار (Drill-down) ======
    st.markdown("#### 🧮 کاوشگر ریز آمار و اطلاعات")
    unique_classes = sorted([c for c in tab_data['کلاس'].unique() if str(c) not in ['-', 'nan']])
    
    selected_drill_class = st.selectbox(
        "یک دسته‌بندی (کلاس) را برای مشاهده ریز آمار انتخاب کنید:", 
        ["نمایش همه (گزارش کلی)"] + unique_classes,
        key=f"drill_{tab_key}"
    )

    if selected_drill_class == "نمایش همه (گزارش کلی)":
        mat_col1, mat_col2 = st.columns(2)
        with mat_col1:
            st.write("**خلاصه کلی بر اساس کلاس:**")
            class_matrix = tab_data.groupby('کلاس')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
            class_matrix['تراز'] = class_matrix['واریز (ریال)'] - class_matrix['برداشت (ریال)']
            st.dataframe(class_matrix.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}', 'تراز': '{:,.0f}'}), use_container_width=True, hide_index=True)
            
        with mat_col2:
            st.write("**خلاصه کلی بر اساس جزئیات:**")
            detail_matrix = tab_data.groupby('جزئیات')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
            detail_matrix['تراز'] = detail_matrix['واریز (ریال)'] - detail_matrix['برداشت (ریال)']
            st.dataframe(detail_matrix.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}', 'تراز': '{:,.0f}'}), use_container_width=True, hide_index=True)

    else:
        class_df = tab_data[tab_data['کلاس'] == selected_drill_class]
        c_inc = class_df['واریز (ریال)'].sum()
        c_exp = class_df['برداشت (ریال)'].sum()
        c_net = c_inc - c_exp
        
        st.info(f"📊 **جمع کل برای «{selected_drill_class}»** ⸺ مجموع واریزی: **{c_inc:,.0f}** ریال | مجموع برداشت: **{c_exp:,.0f}** ریال | تراز خالص: **{c_net:,.0f}** ریال")
        
        st.write(f"**ریز آمار «{selected_drill_class}» به تفکیک:**")
        drill_grouped = class_df.groupby(['جزئیات', 'تکمیلی'])[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
        drill_grouped['تراز'] = drill_grouped['واریز (ریال)'] - drill_grouped['برداشت (ریال)']
        st.dataframe(drill_grouped.style.format({'واریز (ریال)': '{:,.0f}', 'برداشت (ریال)': '{:,.0f}', 'تراز': '{:,.0f}'}), use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# بدنه اصلی اپلیکیشن
# ---------------------------------------------------------
def format_currency(num):
    if abs(num) >= 1_000_000_000_000:
        return f"{num / 1_000_000_000_000:.2f} همت"
    elif abs(num) >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f} میلیارد"
    elif abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.2f} میلیون"
    else:
        return f"{num:,.0f}"
        
st.title("داشبورد جامع و هوشمند مالی")
st.markdown("---")

st.sidebar.title("⚙️ تنظیمات داشبورد")
uploaded_file = st.sidebar.file_uploader("📥 آپلود فایل اکسل خام", type=['xlsx', 'xls'])

if uploaded_file is not None:
    with st.spinner('در حال پردازش داده‌ها...'):
        try:
            df = clean_data(uploaded_file)
            st.sidebar.success("✅ فایل با موفقیت پردازش شد!")
            
            st.sidebar.header("🎛️ فیلترهای پیشرفته")
            dates = df['تاریخ'].unique().tolist()
            start_date, end_date = st.sidebar.select_slider("📅 انتخاب بازه زمانی:", options=dates, value=(dates[0], dates[-1]))

            selected_mahiyat = st.sidebar.multiselect("ماهیت:", df['ماهیت'].unique().tolist(), default=df['ماهیت'].unique().tolist())
            selected_center = st.sidebar.multiselect("مرکز (شخصی/کارگاه):", df['مرکز'].unique().tolist(), default=df['مرکز'].unique().tolist())
            selected_class = st.sidebar.multiselect("کلاس:", df['کلاس'].unique().tolist(), default=df['کلاس'].unique().tolist())
            selected_detail = st.sidebar.multiselect("جزئیات:", df['جزئیات'].unique().tolist(), default=df['جزئیات'].unique().tolist())

            filtered_df = df[
                (df['تاریخ'] >= start_date) & 
                (df['تاریخ'] <= end_date) &
                (df['ماهیت'].isin(selected_mahiyat)) &
                (df['مرکز'].isin(selected_center)) &
                (df['کلاس'].isin(selected_class)) &
                (df['جزئیات'].isin(selected_detail))
            ]

            # ۲. شاخص‌های کلان (KPIs) 
            total_inc = filtered_df['واریز (ریال)'].sum()
            total_exp = filtered_df['برداشت (ریال)'].sum()
            net_bal = total_inc - total_exp

            st.markdown("### 📊 شاخص‌های کلیدی عملکرد (KPIs)")
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric("🟢 مجموع درآمد", format_currency(total_inc) + " ریال")
            kpi_col2.metric("🔴 مجموع هزینه‌ها", format_currency(total_exp) + " ریال")
            kpi_col3.metric("🔵 موجودی نهایی", format_currency(net_bal) + " ریال")
            st.divider()

            # ۳. نمودارهای کلان (روند روزانه و موجودی تجمعی) 
            st.markdown("### 🌊 روند نقدینگی در طول زمان")
            
            tab_trend_1, tab_trend_2 = st.tabs(["📈 روند درآمد و هزینه‌های روزانه", "💰 روند موجودی تجمعی"])

            with tab_trend_1:
                daily_trend = filtered_df.groupby('تاریخ')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
                
                fig_daily = go.Figure()
                
                fig_daily.add_trace(go.Scatter(
                    x=daily_trend['تاریخ'], y=daily_trend['واریز (ریال)'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#2ecc71', width=3), name='روند درآمد (واریزی‌ها)',
                    fillcolor='rgba(46, 204, 113, 0.4)', 
                    hovertemplate="<b>تاریخ:</b> %{x}<br><b>درآمد:</b> %{y:,.0f} ریال<extra></extra>"
                ))
                
                fig_daily.add_trace(go.Scatter(
                    x=daily_trend['تاریخ'], y=daily_trend['برداشت (ریال)'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#e74c3c', width=3), name='تمامی هزینه‌ها (برداشت‌ها)',
                    fillcolor='rgba(231, 76, 60, 0.4)', 
                    hovertemplate="<b>تاریخ:</b> %{x}<br><b>هزینه:</b> %{y:,.0f} ریال<extra></extra>"
                ))

                fig_daily.update_layout(
                    title=None, template=custom_template, hovermode="x unified",
                    xaxis=dict(title=None, tickangle=-45, showgrid=False),
                    yaxis=dict(title='مبلغ (ریال)'),
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="center",
                        x=0.5
                    ),
                )
                
                st.plotly_chart(fig_daily, use_container_width=True)

            with tab_trend_2:
                daily_summary = filtered_df.groupby('تاریخ')['تراز خالص'].sum().reset_index()
                daily_summary['موجودی تجمعی'] = daily_summary['تراز خالص'].cumsum()
                
                fig_cum = go.Figure()
                fig_cum.add_trace(go.Scatter(
                    x=daily_summary['تاریخ'], y=daily_summary['موجودی تجمعی'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#3498db', width=3), name='موجودی تجمعی',
                    fillcolor='rgba(52, 152, 219, 0.4)',
                    hovertemplate="تاریخ: %{x}<br>موجودی: %{y:,.0f} ریال<extra></extra>"
                ))
                fig_cum.update_layout(
                    title=None, template=custom_template,
                    xaxis=dict(title=None, tickangle=-45, showgrid=False),
                    yaxis=dict(title='موجودی (ریال)'),
                    height=500
                )
                st.plotly_chart(fig_cum, use_container_width=True)
            
            st.divider()

            # ====== نمودار دونات یکپارچه (درآمد + هزینه شخصی + هزینه کارگاه) ======
            st.markdown("### 🍩 نسبت درآمد و هزینه‌ها")
            
            personal_exp = filtered_df[filtered_df['مرکز'] == 'شخصی']['برداشت (ریال)'].sum()
            work_exp = filtered_df[filtered_df['مرکز'] == 'کارگاه']['برداشت (ریال)'].sum()

            fig_donut = px.pie(
                names=['درآمد', 'هزینه کارگاه', 'هزینه شخصی'],
                values=[total_inc, work_exp, personal_exp],
                hole=0.45,
                color=['درآمد', 'هزینه کارگاه', 'هزینه شخصی'],
                color_discrete_map={
                    'درآمد': '#2ecc71',
                    'هزینه کارگاه': '#e74c3c',
                    'هزینه شخصی': '#f1948a'
                },
                title="⚖️ نسبت درآمد و هزینه‌ها (تفکیک شخصی/کارگاه)",
                template=custom_template, height=450
            )
            fig_donut.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate="%{label}: %{value:,.0f} ریال<extra></extra>",
                insidetextfont=dict(size=14, color='white')
            )
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                margin=dict(t=50, b=50, l=20, r=20)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

            st.divider()

            # ۴. تب‌های تفکیک شده 
            st.markdown("### 📑 تحلیل تفکیکی مراکز")
            tabs = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه"])

            with tabs[0]: 
                build_tab_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "personal")
            with tabs[1]: 
                build_tab_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "work")

            st.divider()

            # ۵. سیستم هشدار و بینش خودکار
            st.markdown("### 💡 بینش هوشمند و هشدار سیستم")
            insight_col1, insight_col2 = st.columns(2)
            with insight_col1:
                if total_inc > 0:
                    savings_rate = (net_bal / total_inc) * 100
                    if savings_rate > 0:
                        st.success(f"**وضعیت پس‌انداز:** شما در این بازه **{savings_rate:.1f}٪** از درآمد خود را حفظ کرده‌اید.")
                    else:
                        st.error(f"**هشدار کسری بودجه:** هزینه‌های شما **{abs(savings_rate):.1f}٪** بیشتر از درآمدتان بوده است!")
            with insight_col2:
                if total_exp > 0:
                    top_drainer = filtered_df.groupby('کلاس')['برداشت (ریال)'].sum().idxmax()
                    top_drainer_val = filtered_df.groupby('کلاس')['برداشت (ریال)'].sum().max()
                    st.warning(f"**بزرگترین چاه هزینه:** بخش **«{top_drainer}»** با مبلغ **{top_drainer_val:,.0f}** ریال بیشترین هزینه را داشته است.")

            exp_df = filtered_df[filtered_df['برداشت (ریال)'] > 0]
            if not exp_df.empty:
                mean_exp = exp_df['برداشت (ریال)'].mean()
                std_exp = exp_df['برداشت (ریال)'].std()
                threshold = mean_exp + (2 * std_exp)
                outliers = exp_df[exp_df['برداشت (ریال)'] > threshold]
                
                if not outliers.empty:
                    st.error(f"🚨 **هشدار تراکنش‌های مشکوک:** سیستم {len(outliers)} تراکنش پیدا کرد که مبلغ آن‌ها به شکل غیرعادی بالاست (بیشتر از حد آستانه {threshold:,.0f} ریال):")
                    st.dataframe(outliers[['تاریخ', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی', 'برداشت (ریال)']].style.format({'برداشت (ریال)': '{:,.0f}'}), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ خطایی رخ داد: {e}")
else:
    st.info("👋 برای شروع، لطفاً فایل اکسل خام خود را از منوی سمت راست آپلود کنید.")   else:
        return f"{num:,.0f}"
        
st.title("داشبورد جامع و هوشمند مالی")
st.markdown("---")

st.sidebar.title("⚙️ تنظیمات داشبورد")
uploaded_file = st.sidebar.file_uploader("📥 آپلود فایل اکسل خام", type=['xlsx', 'xls'])

if uploaded_file is not None:
    with st.spinner('در حال پردازش داده‌ها...'):
        try:
            df = clean_data(uploaded_file)
            st.sidebar.success("✅ فایل با موفقیت پردازش شد!")
            
            st.sidebar.header("🎛️ فیلترهای پیشرفته")
            dates = df['تاریخ'].unique().tolist()
            start_date, end_date = st.sidebar.select_slider("📅 انتخاب بازه زمانی:", options=dates, value=(dates[0], dates[-1]))

            selected_mahiyat = st.sidebar.multiselect("ماهیت:", df['ماهیت'].unique().tolist(), default=df['ماهیت'].unique().tolist())
            selected_center = st.sidebar.multiselect("مرکز (شخصی/کارگاه):", df['مرکز'].unique().tolist(), default=df['مرکز'].unique().tolist())
            selected_class = st.sidebar.multiselect("کلاس:", df['کلاس'].unique().tolist(), default=df['کلاس'].unique().tolist())
            selected_detail = st.sidebar.multiselect("جزئیات:", df['جزئیات'].unique().tolist(), default=df['جزئیات'].unique().tolist())

            filtered_df = df[
                (df['تاریخ'] >= start_date) & 
                (df['تاریخ'] <= end_date) &
                (df['ماهیت'].isin(selected_mahiyat)) &
                (df['مرکز'].isin(selected_center)) &
                (df['کلاس'].isin(selected_class)) &
                (df['جزئیات'].isin(selected_detail))
            ]

            # ۲. شاخص‌های کلان (KPIs) 
            total_inc = filtered_df['واریز (ریال)'].sum()
            total_exp = filtered_df['برداشت (ریال)'].sum()
            net_bal = total_inc - total_exp

            st.markdown("### 📊 شاخص‌های کلیدی عملکرد (KPIs)")
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric("🟢 مجموع درآمد", format_currency(total_inc) + " ریال")
            kpi_col2.metric("🔴 مجموع هزینه‌ها", format_currency(total_exp) + " ریال")
            kpi_col3.metric("🔵 موجودی نهایی", format_currency(net_bal) + " ریال")
            st.divider()

            # ۳. نمودارهای کلان (روند روزانه و موجودی تجمعی) 
            st.markdown("### 🌊 روند نقدینگی در طول زمان")
            
            tab_trend_1, tab_trend_2 = st.tabs(["📈 روند درآمد و هزینه‌های روزانه", "💰 روند موجودی تجمعی"])

            with tab_trend_1:
                # ---------------------------------------------------------
                # محاسبه دقیق درآمد و هزینه به صورت مجزا (بدون در نظر گرفتن تراز خالص)
                # ---------------------------------------------------------
                daily_trend = filtered_df.groupby('تاریخ')[['واریز (ریال)', 'برداشت (ریال)']].sum().reset_index()
                
                fig_daily = go.Figure()
                
                # خط درآمد (مبتنی بر واریز)
                fig_daily.add_trace(go.Scatter(
                    x=daily_trend['تاریخ'], y=daily_trend['واریز (ریال)'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#2ecc71', width=3), name='روند درآمد (واریزی‌ها)',
                    fillcolor='rgba(46, 204, 113, 0.4)', 
                    hovertemplate="<b>تاریخ:</b> %{x}<br><b>درآمد:</b> %{y:,.0f} ریال<extra></extra>"
                ))
                
                # خط هزینه‌ها (مبتنی بر تمامی برداشت‌ها)
                fig_daily.add_trace(go.Scatter(
                    x=daily_trend['تاریخ'], y=daily_trend['برداشت (ریال)'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#e74c3c', width=3), name='تمامی هزینه‌ها (برداشت‌ها)',
                    fillcolor='rgba(231, 76, 60, 0.4)', 
                    hovertemplate="<b>تاریخ:</b> %{x}<br><b>هزینه:</b> %{y:,.0f} ریال<extra></extra>"
                ))

                fig_daily.update_layout(
                    title=None, template=custom_template, hovermode="x unified",
                    xaxis=dict(title=None, tickangle=-45, showgrid=False),
                    yaxis=dict(title='مبلغ (ریال)'),
                    legend=dict(
    orientation="h", 
    yanchor="bottom", 
    y=1.02, 
    xanchor="center", # تغییر از right به center برای تعادل بهتر در موبایل
    x=0.5
),
                )
                
                st.plotly_chart(fig_daily, use_container_width=True)

            with tab_trend_2:
                daily_summary = filtered_df.groupby('تاریخ')['تراز خالص'].sum().reset_index()
                daily_summary['موجودی تجمعی'] = daily_summary['تراز خالص'].cumsum()
                
                fig_cum = go.Figure()
                fig_cum.add_trace(go.Scatter(
                    x=daily_summary['تاریخ'], y=daily_summary['موجودی تجمعی'],
                    fill='tozeroy', mode='lines+markers', line_shape='spline',
                    line=dict(color='#3498db', width=3), name='موجودی تجمعی',
                    fillcolor='rgba(52, 152, 219, 0.4)',
                    hovertemplate="تاریخ: %{x}<br>موجودی: %{y:,.0f} ریال<extra></extra>"
                ))
                fig_cum.update_layout(
                    title=None, template=custom_template,
                    xaxis=dict(title=None, tickangle=-45, showgrid=False),
                    yaxis=dict(title='موجودی (ریال)'),
                    height=500
                )
                st.plotly_chart(fig_cum, use_container_width=True)
            
            st.divider()

            # ۴. تب‌های تفکیک شده 
            st.markdown("### 📑 تحلیل تفکیکی مراکز")
            tabs = st.tabs(["👤 حساب شخصی", "🏭 حساب کارگاه"])

            with tabs[0]: 
                build_tab_content(filtered_df[filtered_df['مرکز'] == 'شخصی'], "personal")
            with tabs[1]: 
                build_tab_content(filtered_df[filtered_df['مرکز'] == 'کارگاه'], "work")

            st.divider()

            # ۵. سیستم هشدار و بینش خودکار
            st.markdown("### 💡 بینش هوشمند و هشدار سیستم")
            insight_col1, insight_col2 = st.columns(2)
            with insight_col1:
                if total_inc > 0:
                    savings_rate = (net_bal / total_inc) * 100
                    if savings_rate > 0:
                        st.success(f"**وضعیت پس‌انداز:** شما در این بازه **{savings_rate:.1f}٪** از درآمد خود را حفظ کرده‌اید.")
                    else:
                        st.error(f"**هشدار کسری بودجه:** هزینه‌های شما **{abs(savings_rate):.1f}٪** بیشتر از درآمدتان بوده است!")
            with insight_col2:
                if total_exp > 0:
                    top_drainer = filtered_df.groupby('کلاس')['برداشت (ریال)'].sum().idxmax()
                    top_drainer_val = filtered_df.groupby('کلاس')['برداشت (ریال)'].sum().max()
                    st.warning(f"**بزرگترین چاه هزینه:** بخش **«{top_drainer}»** با مبلغ **{top_drainer_val:,.0f}** ریال بیشترین هزینه را داشته است.")

            exp_df = filtered_df[filtered_df['برداشت (ریال)'] > 0]
            if not exp_df.empty:
                mean_exp = exp_df['برداشت (ریال)'].mean()
                std_exp = exp_df['برداشت (ریال)'].std()
                threshold = mean_exp + (2 * std_exp)
                outliers = exp_df[exp_df['برداشت (ریال)'] > threshold]
                
                if not outliers.empty:
                    st.error(f"🚨 **هشدار تراکنش‌های مشکوک:** سیستم {len(outliers)} تراکنش پیدا کرد که مبلغ آن‌ها به شکل غیرعادی بالاست (بیشتر از حد آستانه {threshold:,.0f} ریال):")
                    st.dataframe(outliers[['تاریخ', 'مرکز', 'کلاس', 'جزئیات', 'تکمیلی', 'برداشت (ریال)']].style.format({'برداشت (ریال)': '{:,.0f}'}), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ خطایی رخ داد: {e}")
else:                                                     # ← هم‌سطح if
    st.info("👋 برای شروع، لطفاً فایل اکسل خام خود را از منوی سمت راست آپلود کنید.")
