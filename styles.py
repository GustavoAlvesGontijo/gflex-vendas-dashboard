"""
CSS compartilhado — importar em todas as paginas.
"""
import streamlit as st

def inject_css():
    st.markdown("""
<style>
/* Header escuro */
[data-testid="stHeader"]{background-color:#1a1a2e}
/* Sidebar */
[data-testid="stSidebar"]{background:#f8f9fa}
/* Sidebar NAV */
[data-testid="stSidebarNav"]{padding-top:8px}
[data-testid="stSidebarNav"] a{
    font-size:0.95rem!important;font-weight:500;padding:10px 16px!important;
    border-radius:8px;margin:2px 8px;transition:all 0.2s;
    color:#333!important;text-decoration:none!important;
}
[data-testid="stSidebarNav"] a:hover{background:#EC850012;color:#EC8500!important}
[data-testid="stSidebarNav"] a[aria-selected="true"]{
    background:linear-gradient(90deg,#EC850018,#EC850008)!important;
    border-left:4px solid #EC8500!important;font-weight:700!important;
    color:#1a1a2e!important;
}
/* Metricas */
[data-testid="stMetricValue"]{font-size:1.5rem;font-weight:700;color:#1a1a2e}
[data-testid="stMetricLabel"]{font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#666}
/* Tabelas Streamlit */
[data-testid="stDataFrame"] th{
    background:#1a1a2e!important;color:white!important;
    font-weight:600;font-size:0.85rem!important;text-transform:uppercase;
    padding:12px 14px!important;
}
[data-testid="stDataFrame"] td{
    padding:10px 14px!important;font-size:0.95rem!important;
    border-bottom:1px solid #eee!important;color:#1a1a2e!important;
}
[data-testid="stDataFrame"] tr:nth-child(even){background:#F8F9FA!important}
[data-testid="stDataFrame"] tr:hover{background:#FFF3E0!important}
/* Footer */
footer{visibility:hidden}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}
</style>
""", unsafe_allow_html=True)
