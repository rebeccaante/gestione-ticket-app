import pandas as pd
import streamlit as st
from supabase import create_client

# Configurazione Pagina
st.set_page_config(
    page_title="Gestione Ticket HR", layout="wide", page_icon="🎟️"
)

# -----------------------------------------------------------------------------
# CONFIGURAZIONE CREDENZIALI SUPABASE
# -----------------------------------------------------------------------------
SUPABASE_URL = "https://mvdcrqmgjtqtllnexdwb.supabase.co"
SUPABASE_KEY = (
    "sb_publishable_BzXfnuLH_bur-gQFf77keQ_RTbUSiOo"  
)

# Inizializzazione client Supabase
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

# -----------------------------------------------------------------------------
# 1. PORTALE DIPENDENTE: INSERIMENTO RICHIESTA
# -----------------------------------------------------------------------------
if ruolo == "Dipendente - Nuova Richiesta":
    st.title("🎟️ Richiesta Ticket Buoni Pasto")
    st.markdown(
        "Compila i campi sottostanti e carica la foto o il PDF del modulo firmato."
    )

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
                    "Gennaio",
                    "Febbraio",
                    "Marzo",
                    "Aprile",
                    "Maggio",
                    "Giugno",
                    "Luglio",
                    "Agosto",
                    "Settembre",
                    "Ottobre",
                    "Novembre",
                    "Dicembre",
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
                st.error(
                    "Tutti i campi e l'allegato del modulo firmato sono obbligatori."
                )
            else:
                try:
                    # 1. Carica File su Supabase Storage
                    file_bytes = allegato.read()
                    file_name = (
                        f"{nome_cognome.replace(' ', '_')}_{allegato.name}"
                    )

                    supabase.storage.from_("moduli-firmati").upload(
                        file_name,
                        file_bytes,
                        file_options={"content-type": allegato.type},
                    )

                    file_url = supabase.storage.from_(
                        "moduli-firmati"
                    ).get_public_url(file_name)

                    # 2. Inserisci Record nel Database Supabase
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
# 2. PORTALE HR: GESTIONE RICHIESTE E SCALO TICKET
# -----------------------------------------------------------------------------
elif ruolo == "HR - Gestione Richieste":
    st.title("📋 Dashboard Gestione Richieste (HR)")

    richieste_res = supabase.table("richieste").select("*").execute()
    ordini_res = (
        supabase.table("ordini")
        .select("*")
        .gt("quantita_residua", 0)
        .execute()
    )

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
                st.link_button(
                    "📄 Scarica/Apri Modulo Firmato", row["file_url"]
                )

            with col2:
                if not is_pronto:
                    if not df_ordini.empty:
                        ord_sel = st.selectbox(
                            "Seleziona Ordine/Fattura da cui scalare:",
                            df_ordini["numero_fattura"].tolist(),
                            key=f"sel_{row['id']}",
                        )
                        if st.button(
                            "Segna come PRONTI 🚀", key=f"btn_{row['id']}"
                        ):
                            ord_data = df_ordini[
                                df_ordini["numero_fattura"] == ord_sel
                            ].iloc[0]
                            nuova_qta = (
                                ord_data["quantita_residua"] - row["num_ticket"]
                            )

                            if nuova_qta >= 0:
                                # Update Quantità Residua su Ordini
                                supabase.table("ordini").update(
                                    {"quantita_residua": nuova_qta}
                                ).eq("id", ord_data["id"]).execute()

                                # Update Stato su Richieste
                                supabase.table("richieste").update(
                                    {
                                        "stato": "Pronti",
                                        "ordine_id": ord_data["id"],
                                    }
                                ).eq("id", row["id"]).execute()

                                st.success(
                                    "Stato aggiornato e ticket scalati con successo!"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Quantità insufficiente nella fattura selezionata."
                                )
                    else:
                        st.warning(
                            "⚠️ Nessun ordine con ticket disponibili in magazzino."
                        )

# -----------------------------------------------------------------------------
# 3. PORTALE HR: MAGAZZINO E TRACCIAMENTO FATTURE
# -----------------------------------------------------------------------------
elif ruolo == "HR - Magazzino & Ordini":
    st.title("📦 Magazzino Ticket & Ordini d'Acquisto")

    with st.expander("➕ Registra Nuova Fattura / Ordine Ticket"):
        with st.form("form_ordine"):
            num_fat = st.text_input("Numero Fattura / Ordine *")
            val_uni = st.number_input(
                "Valore Singolo Ticket (€) *", value=7.00, step=0.50
            )
            qta = st.number_input(
                "Quantità Ticket Acquistati *", min_value=1, step=10
            )

            if st.form_submit_button("Salva Ordine"):
                if num_fat:
                    supabase.table("ordini").insert(
                        {
                            "numero_fattura": num_fat,
                            "valore_unitario": val_uni,
                            "quantita_acquistata": qta,
                            "quantita_residua": qta,
                        }
                    ).execute()
                    st.success("Ordine salvato in magazzino!")
                    st.rerun()
                else:
                    st.error("Inserisci il numero di fattura o ordine.")

    res_ordini = supabase.table("ordini").select("*").execute()
    if res_ordini.data:
        df_ord = pd.DataFrame(res_ordini.data)
        st.subheader("Giacenza Attuale Magazzino")
        st.dataframe(df_ord, use_container_width=True)

        tot_residui = df_ord["quantita_residua"].sum()
        valore_tot = (
            df_ord["quantita_residua"] * df_ord["valore_unitario"]
        ).sum()

        c1, c2 = st.columns(2)
        c1.metric("Totale Ticket Rimanenti", f"{tot_residui} ticket")
        c2.metric("Valore Rimanente Totale", f"€ {valore_tot:.2f}")
    else:
        st.info("Nessun ordine registrato nel magazzino.")
