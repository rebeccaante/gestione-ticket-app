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

# -----------------------------------------------------------------------------
# MENU NAVIGAZIONE
# -----------------------------------------------------------------------------
st.sidebar.title("📌 Menu Navigazione")
ruolo = st.sidebar.radio(
    "Seleziona Sezione:",
    [
        "Dipendente - Nuova Richiesta",
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
# 1. PORTALE DIPENDENTE
# -----------------------------------------------------------------------------
if ruolo == "Dipendente - Nuova Richiesta":
    st.title("🎟️ Richiesta Ticket Buoni Pasto")
    st.markdown("Compila i campi sottostanti e carica la foto o il PDF del modulo firmato.")

    with st.form("form_richiesta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email aziendale *")
            nome_cognome = st.text_input("Cognome e Nome *")
            anno = st.selectbox("Anno *", [2025, 2026, 2027])
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

                    supabase.storage.from_("moduli-firmati").upload(
                        file_name,
                        file_bytes,
                        file_options={"content-type": allegato.type},
                    )

                    file_url = supabase.storage.from_("moduli-firmati").get_public_url(file_name)

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

        # SUB-TAB 2: TICKET DIGITALI / TESSERE
        with tab2:
            st.subheader("💳 Caricamento & Tracciamento Tessere Digitali")

            with st.expander("➕ Inserisci/Aggiorna Ricarica Tessera Digital", expanded=True):
                with st.form("form_tessera"):
                    c1, c2 = st.columns(2)
                    with c1:
                        num_tessera = st.text_input("Numero Tessera *")
                        assegnato_a = st.text_input("Assegnata Momentaneamente a (Persona)")
                        num_t = st.number_input("N° Ticket da caricare *", min_value=1, step=1)
                    with c2:
                        m_tessera = st.selectbox(
                            "Mese di riferimento *",
                            [
                                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
                            ]
                        )
                        a_tessera = st.selectbox("Anno di riferimento *", [2025, 2026, 2027])

                    if st.form_submit_button("Registra Ricarica Tessera"):
                        if num_tessera:
                            supabase.table("tessere_digitali").insert({
                                "numero_tessera": num_tessera,
                                "assegnato_a": assegnato_a,
                                "mese": m_tessera,
                                "anno": a_tessera,
                                "num_ticket": num_t
                            }).execute()
                            st.success("Ricarica tessera salvata con successo!")
                            st.rerun()
                        else:
                            st.error("Inserisci il numero di tessera.")

            # Tabella Tessere Registrate
            res_tessere = supabase.table("tessere_digitali").select("*").order("created_at", desc=True).execute()
            if res_tessere.data:
                df_tess = pd.DataFrame(res_tessere.data)

                st.markdown("### 📋 Registro Ricariche Tessere Digitali")
                
                # Calcolo Valore Economico (€ 5.20 / ticket)
                df_tess["Valore Economico (€)"] = df_tess["num_ticket"] * 5.20

                df_show = df_tess[[
                    "numero_tessera", "assegnato_a", "mese", "anno", "num_ticket", "Valore Economico (€)"
                ]].rename(columns={
                    "numero_tessera": "N° Tessera",
                    "assegnato_a": "Assegnato a",
                    "mese": "Mese",
                    "anno": "Anno",
                    "num_ticket": "N° Ticket Caricati"
                })

                st.dataframe(df_show, use_container_width=True)

                # Totali Generali Digitali
                tot_ticket_dig = df_tess["num_ticket"].sum()
                tot_valore_dig = tot_ticket_dig * 5.20

                c1, c2 = st.columns(2)
                c1.metric("Totale Ticket Digitali Erogati", f"{tot_ticket_dig} ticket")
                c2.metric("Valore Economico Totale Digitali", f"€ {tot_valore_dig:.2f}")

                # Possibilità di eliminare ricariche di prova
                with st.expander("🗑️ Elimina Ricarica Tessera"):
                    tess_del = st.selectbox(
                        "Seleziona carica da eliminare:",
                        options=df_tess["id"].tolist(),
                        format_func=lambda x: f"Tessera: {df_tess[df_tess['id']==x]['numero_tessera'].values[0]} - {df_tess[df_tess['id']==x]['assegnato_a'].values[0]} ({df_tess[df_tess['id']==x]['num_ticket'].values[0]} ticket)"
                    )
                    if st.button("Elimina Voce Tessera", type="primary"):
                        supabase.table("tessere_digitali").delete().eq("id", tess_del).execute()
                        st.success("Voce eliminata!")
                        st.rerun()
            else:
                st.info("Nessuna ricarica tessera digitale registrata.")

# -----------------------------------------------------------------------------
# 3. PORTALE HR: MAGAZZINO E ORDINI
# -----------------------------------------------------------------------------
elif ruolo == "HR - Magazzino & Ordini":
    if verifica_accesso_hr():
        st.title("📦 Magazzino Ticket & Tracciamento Ordini")

        res_ordini = supabase.table("ordini").select("*").order("created_at", desc=False).execute()
        res_richieste = supabase.table("richieste").select("*").eq("stato", "Pronti").execute()

        df_ord = pd.DataFrame(res_ordini.data) if res_ordini.data else pd.DataFrame()
        df_rich = pd.DataFrame(res_richieste.data) if res_richieste.data else pd.DataFrame()

        ultimo_residuo_suggerito = 0
        if not df_ord.empty:
            last_order = df_ord.iloc[-1]
            erogati_last = df_rich[df_rich["ordine_id"] == last_order["id"]]["num_ticket"].sum() if not df_rich.empty else 0
            res_prec_last = last_order.get("residuo_precedente", 0) or 0
            ultimo_residuo_suggerito = max(0, (last_order["quantita_acquistata"] - erogati_last) + res_prec_last)

        with st.expander("➕ Registra Nuova Fattura / Ordine Ticket"):
            with st.form("form_ordine"):
                num_fat = st.text_input("Numero Fattura / Ordine *")
                val_uni = st.number_input("Valore Singolo Ticket (€) *", value=5.20, step=0.10)
                qta = st.number_input("Quantità Ticket Acquistati *", min_value=1, value=2000, step=100)
                res_prec = st.number_input(
                    "Residuo Ordine Precedente", 
                    value=int(ultimo_residuo_suggerito), 
                    step=1
                )

                if st.form_submit_button("Salva Ordine"):
                    if num_fat:
                        supabase.table("ordini").insert(
                            {
                                "numero_fattura": num_fat,
                                "valore_unitario": val_uni,
                                "quantita_acquistata": qta,
                                "quantita_residua": qta,
                                "residuo_precedente": res_prec,
                            }
                        ).execute()
                        st.success("Ordine salvato con successo!")
                        st.rerun()
                    else:
                        st.error("Inserisci il numero di fattura o ordine.")

        if not df_ord.empty:
            st.subheader("📋 Riepilogo Ordini & Giacenza Ticket")

            ordini_calcolati = []
            for idx, row_ord in df_ord.iterrows():
                if not df_rich.empty and "ordine_id" in df_rich.columns:
                    erogati = df_rich[df_rich["ordine_id"] == row_ord["id"]]["num_ticket"].sum()
                else:
                    erogati = 0

                acquistati = row_ord["quantita_acquistata"]
                residuo_prec = row_ord.get("residuo_precedente", 0) or 0
                residui_totali = (acquistati - erogati) + residuo_prec

                ordini_calcolati.append({
                    "ID": row_ord["id"],
                    "Fattura/Ordine": row_ord["numero_fattura"],
                    "Valore Unitario": f"€ {row_ord['valore_unitario']:.2f}",
                    "Ticket Acquistati": acquistati,
                    "Ticket Erogati": erogati,
                    "Residuo Ordine Precedente": residuo_prec,
                    "Ticket Residui TOT": residui_totali
                })

            df_display = pd.DataFrame(ordini_calcolati)

            st.dataframe(
                df_display.drop(columns=["ID"]),
                use_container_width=True
            )

            st.markdown("---")
            st.subheader("⚙️ Gestione & Eliminazione Ordini di Prova")
            
            c_sel, c_btn = st.columns([3, 1])
            with c_sel:
                ordine_da_eliminare = st.selectbox(
                    "Seleziona l'ordine da eliminare:",
                    options=df_display["ID"].tolist(),
                    format_func=lambda x: f"Fattura/Ordine: {df_display[df_display['ID']==x]['Fattura/Ordine'].values[0]}"
                )
            with c_btn:
                st.write("")
                st.write("")
                if st.button("🗑️ Elimina Ordine", type="primary"):
                    try:
                        supabase.table("richieste").update({"ordine_id": None}).eq("ordine_id", ordine_da_eliminare).execute()
                        supabase.table("ordini").delete().eq("id", ordine_da_eliminare).execute()
                        st.success("Ordine eliminato!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore durante l'eliminazione: {e}")
        else:
            st.info("Nessun ordine registrato nel magazzino.")
