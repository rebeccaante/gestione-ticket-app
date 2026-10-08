import pandas as pd
import streamlit as st
from supabase import create_client

# Configurazione Pagina
st.set_page_config(
    page_title="Gestione Ticket HR", layout="wide", page_icon="🎟️"
)

# -----------------------------------------------------------------------------
# CONFIGURAZIONE CREDENZIALI & PASSWORD HR
# -----------------------------------------------------------------------------
SUPABASE_URL = "https://mvdcrqmgjtqtllnexdwb.supabase.co"
SUPABASE_KEY = "sb_publishable_BzXfnuLH_bur-gQFf77keQ_RTbUSiOo"

PASSWORD_HR = "HR2026!"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Anni disponibili (dal 2026 al 2060)
ANNI_DISPONIBILI = list(range(2026, 2061))

# Mesi per ciascun anno
MESI_2026 = ["ottobre", "novembre", "dicembre"]
MESI_TUTTI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]

# -----------------------------------------------------------------------------
# MENU NAVIGAZIONE
# -----------------------------------------------------------------------------
st.sidebar.title("📌 Menu Navigazione")
ruolo = st.sidebar.radio(
    "Seleziona Sezione:",
    [
        "Nuova Richiesta",
        "HR - Gestione Richieste",
        "HR - Magazzino & Ordini",
    ],
)

def verifica_accesso_hr():
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Area Riservata HR")
    pwd_inserita = st.sidebar.text_input(
        "Inserisci Password HR:", type="password"
    )
    if pwd_inserita == PASSWORD_HR:
        return True
    elif pwd_inserita != "":
        st.sidebar.error("❌ Password errata")
        return False
    else:
        st.info("🔒 Inserisci la password HR nella barra laterale per accedere a questa sezione.")
        return False

# -----------------------------------------------------------------------------
# 1. PORTALE RICHIESTE
# -----------------------------------------------------------------------------
if ruolo == "Nuova Richiesta":
    st.title("🎟️ Richiesta Ticket Buoni Pasto")
    st.markdown("Compila i campi sottostanti e carica la foto o il PDF del modulo firmato.")

    with st.form("form_richiesta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email aziendale *")
            nome_cognome = st.text_input("Cognome e Nome *")
            anno = st.selectbox("Anno *", ANNI_DISPONIBILI)
        with c2:
            mese = st.selectbox(
                "Mese *",
                [
                    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
                ],
            )
            num_ticket = st.number_input(
                "N° totale Ticket richiesti *", min_value=1, step=1
            )

        allegato = st.file_uploader(
            "Carica foto o PDF del modulo firmato *",
            type=["pdf", "png", "jpg", "jpeg"],
        )
        submitted = st.form_submit_button("Invia Richiesta")

        if submitted:
            if not email or not nome_cognome or not allegato:
                st.error("Tutti i campi e l'allegato del modulo firmato sono obbligatori.")
            else:
                try:
                    file_bytes = allegato.read()
                    file_name = f"{nome_cognome.replace(' ', '_')}_{allegato.name}"

                    supabase.storage.from_("moduli.firmati").upload(
                        file_name,
                        file_bytes,
                        file_options={"content-type": allegato.type},
                    )

                    file_url = supabase.storage.from_("moduli.firmati").get_public_url(file_name)

                    data = {
                        "email": email,
                        "nome_cognome": nome_cognome,
                        "anno": anno,
                        "mese": mese,
                        "num_ticket": num_ticket,
                        "file_url": file_url,
                        "stato": "In lavorazione",
                    }
                    supabase.table("richieste").insert(data).execute()
                    st.success("✅ Richiesta inviata con successo!")
                except Exception as e:
                    st.error(f"Errore durante l'invio della richiesta: {e}")

# -----------------------------------------------------------------------------
# 2. PORTALE HR: GESTIONE RICHIESTE & TICKET DIGITALI
# -----------------------------------------------------------------------------
elif ruolo == "HR - Gestione Richieste":
    if verifica_accesso_hr():
        st.title("📋 Dashboard Gestione Richieste (HR)")

        tab1, tab2 = st.tabs(["📑 Richieste Moduli Cartacei/PDF", "💳 Ticket Digitali (Tessere)"])

        # SUB-TAB 1: RICHIESTE STANDARD
        with tab1:
            richieste_res = supabase.table("richieste").select("*").execute()
            ordini_res = supabase.table("ordini").select("*").order("created_at", desc=True).execute()

            df_req = pd.DataFrame(richieste_res.data)
            df_ordini = pd.DataFrame(ordini_res.data)

            if df_req.empty:
                st.info("Nessuna richiesta ricevuta al momento.")
            else:
                filtro = st.radio(
                    "Filtra per Stato:",
                    ["In lavorazione", "Pronti", "Tutti"],
                    horizontal=True,
                )

                if filtro != "Tutti":
                    df_filtered = df_req[df_req["stato"] == filtro]
                else:
                    df_filtered = df_req

                for idx, row in df_filtered.iterrows():
                    is_pronto = row["stato"] == "Pronti"
                    color = "#D4EDDA" if is_pronto else "#FFF3CD"
                    badge = "✅ PRONTI" if is_pronto else "⏳ IN LAVORAZIONE"

                    st.markdown(
                        f"""
                    <div style="background-color:{color}; padding:15px; border-radius:8px; margin-top:10px; border:1px solid #ccc;">
                        <h4 style="margin:0;">{row['nome_cognome']} — <strong>{badge}</strong></h4>
                        <p style="margin:5px 0 0 0;">
                            <b>Email:</b> {row['email']} | <b>Periodo:</b> {row['mese']} {row['anno']} | <b>N° Ticket:</b> {row['num_ticket']}
                        </p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    col1, col2 = st.columns([2, 3])
                    with col1:
                        st.link_button("📄 Scarica/Apri Modulo Firmato", row["file_url"])

                    with col2:
                        if not is_pronto:
                            if not df_ordini.empty:
                                ord_sel = st.selectbox(
                                    "Assegna all'Ordine/Fattura:",
                                    df_ordini["numero_fattura"].tolist(),
                                    key=f"sel_{row['id']}",
                                )
                                if st.button("Segna come PRONTI 🚀", key=f"btn_{row['id']}"):
                                    ord_data = df_ordini[df_ordini["numero_fattura"] == ord_sel].iloc[0]

                                    supabase.table("richieste").update(
                                        {
                                            "stato": "Pronti",
                                            "ordine_id": ord_data["id"],
                                        }
                                    ).eq("id", row["id"]).execute()

                                    st.success("Stato aggiornato a PRONTI!")
                                    st.rerun()
                            else:
                                st.warning("⚠️ Nessun ordine disponibile in magazzino.")

        # SUB-TAB 2: TICKET DIGITALI & LIBRO PRESENZE
        with tab2:
            st.subheader("💳 Tracciamento Tessere Digitali & Calcolo Presenze")

            sub_tab_a, sub_tab_b, sub_tab_c = st.tabs([
                "📊 Matrice Tessere Digitali", 
                "📁 Upload & Calcolo Libro Presenze", 
                "👥 Anagrafica Nominativi con Diritto"
            ])

            # SUB-TAB A: MATRICE TESSERE
            with sub_tab_a:
                c_anno, c_add_tess = st.columns([2, 3])
                with c_anno:
                    anno_sel = st.selectbox("Seleziona Anno di Riferimento:", ANNI_DISPONIBILI, index=0)

                with c_add_tess:
                    with st.expander("➕ Aggiungi Nuova Tessera Digital"):
                        with st.form("form_nuova_tessera", clear_on_submit=True):
                            nuovo_num_tess = st.text_input("Numero Nuova Tessera *")
                            nuovo_ass = st.text_input("Assegnato Momentaneamente a")
                            if st.form_submit_button("Aggiungi Tessera"):
                                if nuovo_num_tess:
                                    payload_new = {
                                        "numero_tessera": nuovo_num_tess,
                                        "assegnato_a": nuovo_ass,
                                        "anno": anno_sel
                                    }
                                    for m in MESI_TUTTI:
                                        payload_new[m] = 0
                                    supabase.table("matrice_tessere").insert(payload_new).execute()
                                    st.success(f"Tessera {nuovo_num_tess} aggiunta con successo!")
                                    st.rerun()

                mesi_visibili = MESI_2026 if anno_sel == 2026 else MESI_TUTTI

                res_matrice = supabase.table("matrice_tessere").select("*").eq("anno", anno_sel).execute()
                df_db = pd.DataFrame(res_matrice.data) if res_matrice.data else pd.DataFrame()

                tessere_base = [f"008000{i:02d}" for i in range(1, 31)]
                
                rows_data = []
                tessere_esistenti = df_db["numero_tessera"].tolist() if not df_db.empty else []
                tessere_totali = list(set(tessere_base + tessere_esistenti))
                tessere_totali.sort()

                for t_num in tessere_totali:
                    if not df_db.empty and t_num in df_db["numero_tessera"].values:
                        r = df_db[df_db["numero_tessera"] == t_num].iloc[0].to_dict()
                    else:
                        r = {"numero_tessera": t_num, "assegnato_a": "", "anno": anno_sel}
                        for m in MESI_TUTTI:
                            r[m] = 0
                    rows_data.append(r)

                df_grid = pd.DataFrame(rows_data)

                cols_order = ["numero_tessera", "assegnato_a"] + mesi_visibili
                df_grid = df_grid[cols_order]

                rename_dict = {
                    "numero_tessera": "N° Tessera",
                    "assegnato_a": "Assegnato Momentaneamente a",
                }
                for m in mesi_visibili:
                    rename_dict[m] = m.capitalize()

                df_display = df_grid.rename(columns=rename_dict)

                st.info("💡 Inserisci o modifica i dati nelle celle e salva.")

                edited_df = st.data_editor(
                    df_display,
                    use_container_width=True,
                    disabled=["N° Tessera"],
                    num_rows="dynamic",
                    key=f"editor_tessere_{anno_sel}"
                )

                if st.button("💾 Salva Modifiche Tabella Tessere", type="primary"):
                    try:
                        for _, row in edited_df.iterrows():
                            t_num = row["N° Tessera"]
                            ass_a = row["Assegnato Momentaneamente a"]
                            
                            update_payload = {
                                "numero_tessera": t_num,
                                "assegnato_a": ass_a if pd.notna(ass_a) else "",
                                "anno": anno_sel,
                            }
                            for m in mesi_visibili:
                                val_m = row[m.capitalize()]
                                update_payload[m] = int(val_m) if pd.notna(val_m) else 0

                            supabase.table("matrice_tessere").upsert(
                                update_payload, on_conflict="numero_tessera,anno"
                            ).execute()

                        st.success("✅ Tabelle salvate con successo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore durante il salvataggio: {e}")

                # Totali
                st.markdown("---")
                tot_ticket_anno = 0
                for m in mesi_visibili:
                    col_cap = m.capitalize()
                    if col_cap in edited_df.columns:
                        tot_ticket_anno += edited_df[col_cap].fillna(0).sum()

                tot_valore_anno = tot_ticket_anno * 5.20

                col_m1, col_m2 = st.columns(2)
                col_m1.metric(f"Totale Ticket Caricati ({anno_sel})", f"{int(tot_ticket_anno)} ticket")
                col_m2.metric(f"Valore Economico Totale ({anno_sel})", f"€ {tot_valore_anno:.2f}")

            # SUB-TAB B: UPLOAD & CALCOLO LIBRO PRESENZE
            with sub_tab_b:
                st.markdown("### 📄 Upload Libro Presenze Mensile")
                st.markdown("Carica il file Excel o CSV del Libro Presenze. Verranno cont
