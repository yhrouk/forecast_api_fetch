import requests
import pandas as pd
import os
from datetime import datetime

# ============================================================
# PARTIE 1 — Récupération
# ============================================================

def fetch_weather(lat, lon, days=7):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min"],
        "forecast_days": days,
        "timezone": "auto"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise Exception("❌ Pas de connexion Internet.")
    except requests.exceptions.Timeout:
        raise Exception("❌ Timeout : serveur injoignable.")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"❌ Erreur API (HTTP {e.response.status_code}).")

    try:
        data = resp.json()
    except ValueError:
        raise Exception("❌ Réponse non-JSON.")

    if "daily" not in data or len(data["daily"]["time"]) == 0:
        raise Exception("❌ Données vides ou structure invalide.")

    return data

# ============================================================
# PARTIE 2 — Traitement
# ============================================================

def process(data):
    df = pd.DataFrame({
        "date": data["daily"]["time"],
        "t_min": data["daily"]["temperature_2m_min"],
        "t_max": data["daily"]["temperature_2m_max"]
    })
    print(f'df = {df}')
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df["t_min"] = pd.to_numeric(df["t_min"], errors="coerce")
    df["t_max"] = pd.to_numeric(df["t_max"], errors="coerce")

    # Valeurs manquantes
    missing = df[["t_min", "t_max"]].isnull().sum()
    if missing.sum() > 0:
        print(f"⚠️  {missing.sum()} valeur(s) manquante(s), suppression des lignes.")
        df = df.dropna(subset=["t_min", "t_max"]).reset_index(drop=True)

    df["t_moyenne"] = (df["t_min"] + df["t_max"]) / 2

    print(f"\n📊 Moyenne : {df['t_moyenne'].mean():.1f} °C")
    print(f"Min : {df['t_min'].min():.1f} °C | Max : {df['t_max'].max():.1f} °C")
    print(f"✅ {len(df)} jours, aucune valeur manquante.")

    return df


# ============================================================
# PARTIE 3 — Export
# ============================================================

def export(df, csv_path, xlsx_path):
    
    resume = pd.DataFrame({
        "date": ["RÉSUMÉ"],
        "t_min": [df["t_min"].min()],
        "t_max": [df["t_max"].max()],
        "t_moyenne": [df["t_moyenne"].mean()]
    })

    # CSV
    pd.concat([df, resume], ignore_index=True).to_csv(csv_path, index=False)
    
    print(f"✅ CSV : {csv_path}")

    # Excel
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Données", index=False)
            resume.to_excel(w, sheet_name="Résumé", index=False)
        print(f"✅ Excel : {xlsx_path}")
    except PermissionError:
        print(f"⚠️  Excel verrouillé (fichier ouvert ?). Ignoré.")

    # Vérification
    df_check = pd.read_csv(csv_path)
    assert len(df_check) == len(df) + 1
    assert df_check.iloc[-1]["date"] == "RÉSUMÉ"
    print(f"✅ Vérification OK : {len(df_check)} lignes.")


# ============================================================
# PARTIE 5 — Seconde exécution / Actualisation
# ============================================================

def second_run(csv_path, lat, lon):
    print("\n" + "=" * 45)
    print("🔄 SECONDE EXÉCUTION")
    print("=" * 45)

    if not os.path.exists(csv_path):
        print("Aucun fichier précédent.")
        return

    df_old = pd.read_csv(csv_path)
    df_old = df_old[df_old["date"] != "RÉSUMÉ"].reset_index(drop=True)
    ts_old = datetime.fromtimestamp(os.path.getmtime(csv_path)).strftime("%H:%M:%S")
    print(f"📄 Fichier précédent ({ts_old}) : moyenne = {df_old['t_moyenne'].mean():.1f} °C")

    data = fetch_weather(lat, lon)
    df_new = process(data)
    export(df_new, csv_path, csv_path.replace(".csv", ".xlsx"))

    diff = abs(df_new["t_moyenne"].mean() - df_old["t_moyenne"].mean())
    if diff < 0.5:
        print(f"\n✅ Données stables (écart moyen : {diff:.2f} °C).")
    else:
        print(f"\n🔄 Données actualisées (écart moyen : {diff:.2f} °C).")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    city = "Paris"
    lat, lon = 48.8566, 2.3522
    timestamp = datetime.now().strftime("%H%M%S")
    csv_path = f"meteo_{city.lower()}_{timestamp}.csv"
    xlsx_path = f"meteo_paris_{timestamp}.xlsx"

    try:
        data = fetch_weather(lat, lon)
        print(data)
        df = process(data)
        print(f"\n📍 {city} :\n")
        print(df.to_string(index=False))
        export(df, csv_path, xlsx_path)
        second_run(csv_path, lat, lon)

    except Exception as e:
        print(f"\n{e}")   