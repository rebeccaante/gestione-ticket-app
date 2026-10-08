import pandas as pd
import streamlit as st
from supabase import create_client
import re

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
                tessere_esistenti = df_db["numero_tessera"].tolist() if not df_db.empty else []
                tessere_totali = list(set(tessere_base + tessere_esistenti))
                tessere_totali.sort()

                rows_data = []
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
                st.markdown("Carica il file Excel o CSV. Il sistema filtrerà **esclusivamente i valori numerici associati a PREORD e SMARTW** nella colonna AQ.")

                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    m_presenza = st.selectbox("Mese Presenze:", MESI_TUTTI, index=8)
                with col_u2:
                    a_presenza = st.selectbox("Anno Presenze:", ANNI_DISPONIBILI, index=0)

                file_presenze = st.file_uploader("Carica Libro Presenze (Excel o CSV)", type=["xlsx", "xls", "csv"])

                if file_presenze:
                    try:
                        if file_presenze.name.endswith(".csv"):
                            df_raw = pd.read_csv(file_presenze, header=None)
                        else:
                            df_raw = pd.read_excel(file_presenze, header=None)

                        res_regole = supabase.table("regole_dipendenti").select("*").eq("ha_diritto", True).execute()
                        dip_abilitati = [r["nome_cognome"] for r in res_regole.data] if res_regole.data else []

                        if not dip_abilitati:
                            st.warning("⚠️ Non ci sono dipendenti abilitati nell'Anagrafica. Aggiungili nel tab 'Anagrafica Nominativi con Diritto'.")
                        else:
                            st.success(f"File '{file_presenze.name}' caricato. Estraggo i dati per PREORD e SMARTW dalla Colonna AQ...")

                            risultati_calcolo = []
                            idx_colonna_aq = 42  # Indice della colonna AQ (0-indexed)

                            for dip in dip_abilitati:
                                parts = dip.strip().lower().split()
                                trovato = False
                                totale_dip_ticket = 0

                                # Cerca le righe dedicate a questo dipendente
                                for idx_row in range(len(df_raw)):
                                    row = df_raw.iloc[idx_row]
                                    row_str_vals = [str(val).strip().lower() for val in row.values if pd.notna(val)]
                                    row_text = " ".join(row_str_vals)

                                    if all(part in row_text for part in parts):
                                        trovato = True

                                        # Scansiona le righe adiacenti del blocco del dipendente (es. 10 righe sotto)
                                        max_search_rows = min(len(df_raw), idx_row + 12)
                                        for r_i in range(idx_row, max_search_rows):
                                            sub_row = df_raw.iloc[r_i]
                                            sub_row_text = " ".join([str(v).strip().upper() for v in sub_row.values if pd.notna(v)])

                                            # Se incontriamo un altro dipendente ci fermiamo
                                            if r_i > idx_row and any(c_val in sub_row_text.lower() for c_val in ["matr.", "badge", "cod. dip"]):
                                                break

                                            # Se la riga contiene PREORD o SMARTW
                                            if "PREORD" in sub_row_text or "SMARTW" in sub_row_text:
                                                # Estrai il valore numerico dalla colonna AQ (o da celle vicine)
                                                val_aq = None
                                                if len(sub_row) > idx_colonna_aq and pd.notna(sub_row.iloc[idx_colonna_aq]):
                                                    val_aq = sub_row.iloc[idx_colonna_aq]

                                                if val_aq is not None:
                                                    # Estrai solo cifre o numeri decimali
                                                    nums = re.findall(r'\d+(?:\.\d+)?', str(val_aq))
                                                    if nums:
                                                        totale_dip_ticket += int(float(nums[0]))
                                                    else:
                                                        # Se la riga riporta la causale senza il totale, conta 1
                                                        totale_dip_ticket += 1
                                                else:
                                                    totale_dip_ticket += 1

                                        break

                                risultati_calcolo.append({
                                    "Cognome e Nome": dip,
                                    "Presente nel Libro Presenze": "✅ SI" if trovato else "❌ NO / Non Trovato",
                                    "Ticket PREORD + SMARTW (Col. AQ)": totale_dip_ticket,
                                    "N° Ticket Spettanti": totale_dip_ticket,
                                    "Valore Economico (€)": totale_dip_ticket * 5.20
                                })

                            df_res_calc = pd.DataFrame(risultati_calcolo)
                            
                            st.markdown("---")
                            st.markdown("### 🧮 Risultati Calcolo Spettanze Ticket")
                            st.dataframe(df_res_calc, use_container_width=True)

                            tot_ticket_calc = df_res_calc["N° Ticket Spettanti"].sum()
                            tot_valore_calc = tot_ticket_calc * 5.20

                            c_k1, c_k2 = st.columns(2)
                            c_k1.metric("Totale Ticket Spettanti Mese", f"{tot_ticket_calc} ticket")
                            c_k2.metric("Valore Economico Totale Mese", f"€ {tot_valore_calc:.2f}")

                            st.markdown("---")
                            st.subheader("⚡ Compilazione Automatica Matrice Tessere Digitali")
                            st.write(f"Clicca sul pulsante sottostante per riportare automaticamente questi conteggi nella **Matrice Tessere Digitali** per il mese di **{m_presenza.capitalize()} {a_presenza}**.")

                            if st.button(f"⚡ Applica e Popola Matrice Tessere ({m_presenza.capitalize()} {a_presenza})", type="primary"):
                                try:
                                    res_mat = supabase.table("matrice_tessere").select("*").eq("anno", a_presenza).execute()
                                    df_mat_db = pd.DataFrame(res_mat.data) if res_mat.data else pd.DataFrame()

                                    aggiornati_cnt = 0
                                    for idx_c, row_c in df_res_calc.iterrows():
                                        nome_dip_c = row_c["Cognome e Nome"]
                                        n_ticket_c = int(row_c["N° Ticket Spettanti"])

                                        if not df_mat_db.empty and "assegnato_a" in df_mat_db.columns:
                                            parts_c = nome_dip_c.strip().lower().split()
                                            
                                            match_tess = df_mat_db[df_mat_db["assegnato_a"].apply(
                                                lambda x: all(p in str(x).lower() for p in parts_c) if pd.notna(x) and str(x).strip() != "" else False
                                            )]
                                            
                                            if not match_tess.empty:
                                                tess_row = match_tess.iloc[0]
                                                t_num = tess_row["numero_tessera"]

                                                update_dict = {
                                                    "numero_tessera": t_num,
                                                    "anno": a_presenza,
                                                    "assegnato_a": tess_row["assegnato_a"],
                                                    m_presenza.lower(): n_ticket_c
                                                }

                                                supabase.table("matrice_tessere").upsert(
                                                    update_dict, on_conflict="numero_tessera,anno"
                                                ).execute()
                                                aggiornati_cnt += 1

                                    if aggiornati_cnt > 0:
                                        st.success(f"✅ Matrice aggiornata con successo per {aggiornati_cnt} dipendenti/tessere nel mese di {m_presenza.capitalize()}!")
                                    else:
                                        st.warning("⚠️ Nessun abbinamento trovato tra la colonna 'Assegnato Momentaneamente a' delle Tessere e i Nominativi nell'Anagrafica. Assicurati che i nomi corrispondano nella Matrice Tessere.")

                                except Exception as e_pop:
                                    st.error(f"Errore durante l'aggiornamento automatico della matrice: {e_pop}")

                    except Exception as e:
                        st.error(f"Errore nella lettura del file presenze: {e}")

            # SUB-TAB C: ANAGRAFICA NOMINATIVI CON DIRITTO
            with sub_tab_c:
                st.markdown("### 👥 Anagrafica Personale e Gestione Diritto Ticket")
                st.markdown("Aggiungi o modifica i dipendenti che hanno diritto a **1 ticket per giorno lavorato**.")

                with st.form("form_add_dip", clear_on_submit=True):
                    c_n1, c_n2 = st.columns([3, 1])
                    with c_n1:
                        nuovo_nome = st.text_input("Cognome e Nome Dipendente *")
                    with c_n2:
                        ha_diritto_input = st.checkbox("Ha Diritto ai Ticket", value=True)
                    
                    note_dip = st.text_input("Note (opzionale)")
                    if st.form_submit_button("Aggiungi / Aggiorna Dipendente"):
                        if nuovo_nome:
                            supabase.table("regole_dipendenti").upsert({
                                "nome_cognome": nuovo_nome.strip(),
                                "ha_diritto": ha_diritto_input,
                                "note": note_dip
                            }, on_conflict="nome_cognome").execute()
                            st.success(f"Dipendente '{nuovo_nome}' registrato!")
                            st.rerun()
                        else:
                            st.error("Inserisci il nome e cognome.")

                res_dip = supabase.table("regole_dipendenti").select("*").order("nome_cognome").execute()
                if
