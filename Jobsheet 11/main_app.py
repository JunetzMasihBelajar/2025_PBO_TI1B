# main_app.py
import streamlit as st
import datetime
import pandas as pd
import locale
import time
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Indonesian_Indonesia.1252')
    except:
        print("Locale id_ID/Indonesian tidak tersedia.")

def format_rp(angka):
    try:
        return locale.currency(angka or 0, grouping=True, symbol='Rp ')[:-3]
    except:
        return f"Rp {angka or 0:,.0f}".replace(",", ".")

from model import Transaksi
from manajer_anggaran import AnggaranHarian
from konfigurasi import KATEGORI_PENGELUARAN

st.set_page_config(page_title="Catatan Pengeluaran", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def get_anggaran_manager():
    return AnggaranHarian()

anggaran = get_anggaran_manager()

def halaman_input(anggaran: AnggaranHarian):
    st.header("Tambah Pengeluaran Baru")
    with st.form("form_transaksi_baru", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            deskripsi = st.text_input("Deskripsi*", placeholder="Contoh: Makan siang")
        with col2:
            kategori = st.selectbox("Kategori*:", KATEGORI_PENGELUARAN, index=0)

        col3, col4 = st.columns([1, 1])
        with col3:
            jumlah = st.number_input("Jumlah (Rp)*:", min_value=0.01, step=1000.0, format="%.0f", placeholder="Contoh: 25000")
        with col4:
            tanggal = st.date_input("Tanggal*:", value=datetime.date.today())

        submitted = st.form_submit_button("Simpan Transaksi")
        if submitted:
            if not deskripsi:
                st.warning("Deskripsi wajib!")
            elif jumlah is None or jumlah <= 0:
                st.warning("Jumlah wajib!")
            else:
                with st.spinner("Menyimpan..."):
                    tx = Transaksi(deskripsi, float(jumlah), kategori, tanggal)
                    if anggaran.tambah_transaksi(tx):
                        st.success("Transaksi berhasil disimpan.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan transaksi.")

def halaman_riwayat(anggaran: AnggaranHarian):
    st.subheader("Riwayat Transaksi")

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    transaksi_list = anggaran.get_semua_transaksi_obj()
    if not transaksi_list:
        st.info("Belum ada transaksi.")
        return

    st.markdown("""
    <style>
        .tabel-header div {
            font-weight: bold;
            background-color: #EEE;
            padding: 6px 0;
            border-bottom: 1px solid #CCC;
        }
        .tabel-baris:hover {
            background-color: #f9f9f9;
        }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns([1, 2, 3, 2, 1])  
    with cols[0]:
        st.markdown("**ID**")
    with cols[1]:
        st.markdown("**Tanggal**")
    with cols[2]:
        st.markdown("**Deskripsi**")
    with cols[3]:
        st.markdown("**Jumlah (Rp)**")
    with cols[4]:
        st.markdown("**Aksi**")


    if "hapus_id" not in st.session_state:
        st.session_state.hapus_id = None

    for transaksi in transaksi_list:
        cols = st.columns([1, 2, 3, 2, 1])
        with cols[0]:
            st.write(transaksi.id)
        with cols[1]:
            st.write(transaksi.tanggal.strftime("%d %b %Y"))
        with cols[2]:
            st.write(transaksi.deskripsi)
        with cols[3]:
            st.write(f"Rp {transaksi.jumlah:,.0f}")
        with cols[4]:
            if st.button("Hapus", key=f"hapus_{transaksi.id}"):
                st.session_state.hapus_id = transaksi.id


    
    if st.session_state.hapus_id is not None:
        st.warning(f"Yakin ingin menghapus transaksi ID {st.session_state.hapus_id}?")
        col_konfirmasi, col_batal = st.columns([1, 1])
        with col_konfirmasi:
            if st.button("✅ Konfirmasi Hapus"):
                sukses = anggaran.hapus_transaksi(st.session_state.hapus_id)
                if sukses:
                    st.success(f"✅ Transaksi ID {st.session_state.hapus_id} berhasil dihapus.")
                else:
                    st.error(f"❌ Gagal menghapus transaksi ID {st.session_state.hapus_id}.")
                time.sleep(1)
                
                st.session_state.hapus_id = None
                st.cache_data.clear()
                st.rerun() 
        with col_batal:
            if st.button("❌ Batal"):
                st.session_state.hapus_id = None
                st.rerun()



def halaman_ringkasan(anggaran: AnggaranHarian):
    st.subheader("Ringkasan Pengeluaran")
    filter = st.selectbox("Filter Waktu", ["Semua", "Hari Ini", "Pilih Tanggal"])
    tanggal_filter = None
    if filter == "Hari Ini":
        tanggal_filter = datetime.date.today()
    elif filter == "Pilih Tanggal":
        tanggal_filter = st.date_input("Pilih Tanggal")

    total = anggaran.hitung_total_pengeluaran(tanggal=tanggal_filter)
    st.metric("Total Pengeluaran", format_rp(total))

    data_kategori = anggaran.get_pengeluaran_per_kategori(tanggal=tanggal_filter)
    if not data_kategori:
        st.info("Tidak ada data.")
    else:
        df_kat = pd.DataFrame(
            [{"Kategori": k, "Total": format_rp(v)} for k, v in data_kategori.items()]
        )
        st.dataframe(df_kat, use_container_width=True)
        st.bar_chart(pd.DataFrame.from_dict(data_kategori, orient='index'))

def main():
    st.sidebar.title("Catatan Pengeluaran")
    menu = st.sidebar.radio("Menu", ["Tambah", "Riwayat", "Ringkasan"])
    if menu == "Tambah":
        halaman_input(anggaran)
    elif menu == "Riwayat":
        halaman_riwayat(anggaran)
    elif menu == "Ringkasan":
        halaman_ringkasan(anggaran)

if __name__ == "__main__":
    main()

