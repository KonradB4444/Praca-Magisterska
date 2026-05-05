import streamlit as st
import json
import os
import time
from datetime import datetime, timezone
from asystent_silnik import Asystent
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="Asystent Medyczny", layout="wide")

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

if "zalogowany_user" not in st.session_state:
    st.session_state.zalogowany_user = None
if "profil_lekarza" not in st.session_state:
    st.session_state.profil_lekarza = None
if "historia_czatu" not in st.session_state:
    st.session_state.historia_czatu = []
if "aktywny_czat_id" not in st.session_state:
    st.session_state.aktywny_czat_id = None
if "lista_czatow" not in st.session_state:
    st.session_state.lista_czatow = []

cookie_manager = CookieController()

# Logika odtwarzania sesji po odświeżeniu strony
if st.session_state.zalogowany_user is None:
    # Próbujemy odczytać ciastka
    try:
        zapisany_token = cookie_manager.get("asystent_token")
        zapisany_refresh = cookie_manager.get("asystent_refresh")
    except TypeError:
        zapisany_token = None
        zapisany_refresh = None
    
    if zapisany_token and zapisany_refresh:
        try:
            res = supabase.auth.set_session(zapisany_token, zapisany_refresh)
            st.session_state.zalogowany_user = res.user

            cookie_manager.set("asystent_token", res.session.access_token)
            cookie_manager.set("asystent_refresh", res.session.refresh_token)

            profil = supabase.table("profiles").select("*").eq("id", res.user.id).execute()
            if profil.data:
                st.session_state.profil_lekarza = profil.data[0]["username"]
        except Exception:
            cookie_manager.remove("asystent_token")
            cookie_manager.remove("asystent_refresh")

def ekran_logowania():
    st.markdown("<br><br><br>", unsafe_allow_html=True) # Robimy odstęp z góry
    st.markdown("<h1 style='text-align: center;'>System Wspomagania Decyzji Klinicznych</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab_log, tab_rej = st.tabs(["Logowanie", "Rejestracja"])
        
        with tab_log:
            login_email = st.text_input("E-mail")
            login_haslo = st.text_input("Hasło", type="password")
            if st.button("Zaloguj się", use_container_width=True, type="primary"):
                try:
                    response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_haslo})
                    st.session_state.zalogowany_user = response.user
                    
                    cookie_manager.set("asystent_token", response.session.access_token)
                    cookie_manager.set("asystent_refresh", response.session.refresh_token)
                    
                    profil = supabase.table("profiles").select("*").eq("id", response.user.id).execute()
                    if profil.data:
                        st.session_state.profil_lekarza = profil.data[0]["username"]
                    
                    st.rerun()
                except Exception as e:
                    st.error("Błędny e-mail lub hasło.")

        with tab_rej:
            rej_nazwa = st.text_input("Imię i Nazwisko (Username)")
            rej_email = st.text_input("Nowy E-mail")
            rej_haslo = st.text_input("Nowe Hasło", type="password")
            rej_haslo_potwierdz = st.text_input("Powtórz Nowe Hasło", type="password") # NOWE POLE
            
            if st.button("Zarejestruj", use_container_width=True):
                # Zabezpieczenia Frontendowe
                if len(rej_nazwa) < 3 or len(rej_nazwa) > 50:
                    st.warning("Imię i nazwisko musi mieć od 3 do 50 znaków.")
                elif len(rej_haslo) < 6:
                    st.warning("Hasło musi mieć co najmniej 6 znaków.")
                elif len(rej_haslo) > 64:
                    st.warning("Hasło jest zbyt długie (maksymalnie 64 znaki).")
                elif rej_haslo != rej_haslo_potwierdz:
                    st.warning("Hasła nie są identyczne!")
                else:
                    try:
                        nowy_user = supabase.auth.sign_up({
                            "email": rej_email, 
                            "password": rej_haslo,
                            "options": {
                                "data": {
                                    "username": rej_nazwa
                                }
                            }
                        })
                        st.success("Konto utworzone! Sprawdź swoją skrzynkę e-mail i kliknij w link aktywacyjny, a następnie się zaloguj.")
                    except Exception as e:
                        st.error(f"Błąd rejestracji: {e}")

@st.dialog("Potwierdzenie usunięcia")
def potwiedz_usuniecie(czat_id):
    st.write("Czy na pewno chcesz usunąć tę konsultację? Tej operacji nie można cofnąć.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Tak, usuń", use_container_width=True, type="primary"):
            supabase.table("chat_sessions").delete().eq("id", czat_id).execute()
            
            if st.session_state.aktywny_czat_id == czat_id:
                st.session_state.aktywny_czat_id = None
                st.session_state.historia_czatu = []
                if "agent_backend" in st.session_state:
                    del st.session_state.agent_backend
            
            st.rerun()
            
    with col2:
        if st.button("Anuluj", use_container_width=True):
            st.rerun()

@st.dialog("Zarządzanie kontem")
def zarzadzanie_kontem():
    st.write(f"Konto powiązane z e-mailem: **{st.session_state.zalogowany_user.email}**")
    st.divider()
    
    st.subheader("Zmiana nazwy użytkownika")
    nowa_nazwa = st.text_input("Nowa nazwa (Imię i Nazwisko)", value=st.session_state.profil_lekarza)
    if st.button("Aktualizuj nazwę", use_container_width=True):
        if len(nowa_nazwa) < 3 or len(nowa_nazwa) > 50:
            st.warning("Nazwa użytkownika musi mieć od 3 do 50 znaków.")
        else:
            try:
                supabase.table("profiles").update({"username": nowa_nazwa}).eq("id", st.session_state.zalogowany_user.id).execute()
                st.session_state.profil_lekarza = nowa_nazwa
                st.success("Nazwa zaktualizowana pomyślnie!")
                time.sleep(1)
                st.rerun() # Przeładowanie, żeby sidebar załapał nową nazwę
            except Exception as e:
                st.error(f"Błąd aktualizacji: {e}")
            
    st.divider()
    
    st.subheader("Zmiana hasła")
    nowe_haslo = st.text_input("Wpisz nowe hasło", type="password")
    nowe_haslo_potwierdz = st.text_input("Powtórz nowe hasło", type="password") # NOWE POLE
    
    if st.button("Aktualizuj hasło", use_container_width=True):
        # Zabezpieczenia Frontendowe
        if len(nowe_haslo) < 6:
            st.warning("Hasło musi składać się z minimum 6 znaków.")
        elif len(nowe_haslo) > 64:
            st.warning("Hasło jest zbyt długie (maksymalnie 64 znaki).")
        elif nowe_haslo != nowe_haslo_potwierdz:
            st.warning("Hasła nie są identyczne!")
        else:
            try:
                supabase.auth.update_user({"password": nowe_haslo})
                st.success("Hasło zostało pomyślnie zmienione!")
            except Exception as e:
                st.error(f"Błąd zmiany hasła: {e}")
            
    st.divider()

    st.subheader("Niebezpieczna strefa")
    with st.expander("Usuń konto na stałe"):
        st.warning("Ta operacja jest nieodwracalna. Stracisz dostęp do aplikacji oraz całą historię konsultacji medycznych.")
        potwierdzenie = st.checkbox("Rozumiem, chcę trwale usunąć moje konto")
        
        if potwierdzenie:
            if st.button("Trwale usuń konto", use_container_width=True):
                try:
                    supabase.rpc("delete_user").execute()

                    supabase.auth.sign_out()
                    st.session_state.zalogowany_user = None
                    st.session_state.profil_lekarza = None
                    st.session_state.historia_czatu = []
                    st.session_state.aktywny_czat_id = None
                    cookie_manager.remove("asystent_token")
                    cookie_manager.remove("asystent_refresh")
                    
                    st.rerun() # Przeładuje aplikację i wyrzuci nas do ekranu logowania
                except Exception as e:
                    st.error(f"Błąd usuwania konta: {e}")

# Czysty bajer dodany żeby fajnie wyglądać
def renderuj_karte(wyniki):
    st.markdown("### Wyniki Analizy Ryzyka (XGBoost)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(label="Ryzyko Zgonu", value=f"{wyniki['zgon']}%")
        st.progress(wyniki['zgon'] / 100.0)
        
    with col2:
        st.metric(label="Ryzyko Konieczności Dializy", value=f"{wyniki['dializa']}%")
        st.progress(wyniki['dializa'] / 100.0)
        
    st.divider()

def wyczysc_wyszukiwarke():
    st.session_state.wyszukiwarka = ""

# Główny widok apki
def ekran_glowny():
    if "agent_backend" not in st.session_state:
        klucz_gemini = st.secrets["GOOGLE_API_KEY"] 
        st.session_state.agent_backend = Asystent(klucz_gemini)

    response_czaty = supabase.table("chat_sessions").select("id, title").order("updated_at", desc=True).execute()
    st.session_state.lista_czatow = response_czaty.data

    with st.sidebar:
        nazwa_wyswietlana = st.session_state.profil_lekarza or st.session_state.zalogowany_user.email
        st.success(f"Zalogowano: **{nazwa_wyswietlana}**")

        if st.button("Konto...", use_container_width=True):
            zarzadzanie_kontem()
        
        if st.button("Wyloguj się", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.zalogowany_user = None
            st.session_state.profil_lekarza = None
            st.session_state.historia_czatu = []
            st.session_state.aktywny_czat_id = None
            cookie_manager.remove("asystent_token")
            cookie_manager.remove("asystent_refresh")
            
            st.info("Trwa wylogowywanie...")
            import time
            time.sleep(1.5)
            st.rerun()
            
        st.divider()
        
        if st.button("Nowy Czat", use_container_width=True, type="primary"):
            st.session_state.aktywny_czat_id = None
            st.session_state.historia_czatu = []
            if "agent_backend" in st.session_state:
                del st.session_state.agent_backend
            st.rerun()
            
        st.subheader("Twoje Konsultacje")

        col_search, col_clear = st.columns([5, 1])
        
        with col_search:
            st.text_input(
                "Szukaj", 
                key="wyszukiwarka", 
                label_visibility="collapsed", 
                placeholder="Szukaj konsultacji..."
            )
            
        with col_clear:
            st.button("X", on_click=wyczysc_wyszukiwarke, use_container_width=True)
            
        st.divider()
        
        # Filtrowanie przez czaty
        fraza = st.session_state.get("wyszukiwarka", "").strip().lower()

        if fraza:
            lista_do_wyswietlenia = [c for c in st.session_state.lista_czatow if c['title'] and fraza in c['title'].lower()]
        else:
            lista_do_wyswietlenia = st.session_state.lista_czatow
            
        # Renderowanie wyników
        if not lista_do_wyswietlenia:
            if fraza:
                st.markdown(f"*Brak wyników dla: **{fraza}***")
            else:
                st.markdown("*Brak historii czatów*")
        else:
            for czat in lista_do_wyswietlenia:
                czy_aktywny = (czat['id'] == st.session_state.aktywny_czat_id)
                typ_przycisku = "primary" if czy_aktywny else "secondary"
                
                col_chat, col_del = st.columns([4, 1])
                
                with col_chat:
                    if st.button(f"{czat['title']}", key=f"btn_{czat['id']}", use_container_width=True, type=typ_przycisku):
                        st.session_state.aktywny_czat_id = czat['id']
                        pelny_czat = supabase.table("chat_sessions").select("history").eq("id", czat['id']).execute()
                        
                        if pelny_czat.data:
                            st.session_state.historia_czatu = pelny_czat.data[0]["history"]
                            st.session_state.agent_backend.odtworz_historie_z_ui(st.session_state.historia_czatu)
                            
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_{czat['id']}", use_container_width=True):
                        potwiedz_usuniecie(czat['id'])
        
    # Renderowanie wiadomości
    for msg in st.session_state.historia_czatu:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "karta_wynikow" in msg:
                renderuj_karte(msg["karta_wynikow"]) 
                pass 

    # Input od użytkownika
    if user_input := st.chat_input("Opisz pacjenta..."):
        st.session_state.historia_czatu.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        if st.session_state.aktywny_czat_id is None:
            nowy_rekord = supabase.table("chat_sessions").insert({
                "user_id": st.session_state.zalogowany_user.id,
                "history": st.session_state.historia_czatu
            }).execute()
            st.session_state.aktywny_czat_id = nowy_rekord.data[0]["id"]
            
        with st.spinner("Asystent analizuje dane..."):
            odpowiedz = st.session_state.agent_backend.przetworz_wiadomosc(user_input)
            
            nowy_msg_asystenta = {"role": "assistant", "content": odpowiedz}
            
            # Łapanie wyników XGBoosta
            if "tymczasowe_wyniki_ui" in st.session_state and st.session_state.tymczasowe_wyniki_ui is not None:
                nowy_msg_asystenta["karta_wynikow"] = st.session_state.tymczasowe_wyniki_ui
                
                # Czyszczenie sesji bo inaczej karta kopiowałaby się do każdej następnej wiadomości
                st.session_state.tymczasowe_wyniki_ui = None 
            
            # Zapisujemy kompletną wiadomość do historii UI
            st.session_state.historia_czatu.append(nowy_msg_asystenta)
            
            supabase.table("chat_sessions").update({
                "history": st.session_state.historia_czatu,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", st.session_state.aktywny_czat_id).execute()
            
            # Generowanie tytułu
            obecny_czat = next((c for c in st.session_state.lista_czatow if c['id'] == st.session_state.aktywny_czat_id), {})
            if obecny_czat.get("title") is None:
                wygenerowany_tytul = wygeneruj_tytul_czatu(user_input)
                if wygenerowany_tytul != "BRAK_DANYCH":
                    supabase.table("chat_sessions").update({
                        "title": wygenerowany_tytul
                    }).eq("id", st.session_state.aktywny_czat_id).execute()

            st.rerun()

def wygeneruj_tytul_czatu(wiadomosc):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        klucz = st.secrets["GOOGLE_API_KEY"]
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=klucz)
        
        prompt = f"""Przeanalizuj poniższą wiadomość od lekarza.
Jeśli wiadomość zawiera jakiekolwiek konkretne informacje medyczne pacjenta (np. wiek, objawy, diagnozy, parametry), wygeneruj dla niej krótki, 
medyczny tytuł (MAKSYMALNIE 4 SŁOWA) który zawiera te dane (czyli jak wiadomość np. zawiera wiek pacjenta, w tytule też musi się znaleźć). Nie używaj kropek na końcu, absolutnie nie twórz list.
Jeśli wiadomość to tylko powitanie, prośba o instrukcję, ogólne pytanie (np. "dzień dobry", "czego potrzebujesz?"), czy nawet losowe uderzanie w klawiaturę, zwróć dokładnie i tylko jedno słowo: BRAK_DANYCH.

Wiadomość lekarza: {wiadomosc}"""
        
        odpowiedz = llm.invoke(prompt)
        # Zabezpieczenie przed gwiazdkami markdowna bo model lubi dodawać
        return odpowiedz.content.strip().replace("**", "").replace("*", "")
    except Exception as e:
        return "BRAK_DANYCH"

# Zarządzanie widokami
if st.session_state.zalogowany_user is None:
    # Zabezpieczenie przed "mignięciem" formularza
    if "ukryj_blysk" not in st.session_state:
        st.session_state.ukryj_blysk = True
        
        # Wyświetlamy ładny ekran ładowania zamiast okna logowania
        st.markdown("<br><br><br><br><h3 style='text-align: center; color: gray;'>Weryfikacja bezpiecznej sesji...</h3>", unsafe_allow_html=True)
        
        # 0.6 sekundy na pobranie ciastek i wymuszanie odświeżenia kodu
        time.sleep(0.6)
        st.rerun()
    else:
        # Skoro to już drugie przejście pętli, a użytkownika nadal nie ma to znaczy, że faktycznie jest wylogowany. Pokazujemy właściwy formularz.
        ekran_logowania()
else:
    ekran_glowny()