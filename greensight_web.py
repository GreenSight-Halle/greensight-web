#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 2025
@author: GreenSight
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from datetime import datetime
from io import StringIO, BytesIO
import os

# >>> Hellgrüner Hintergrund für die gesamte Web-App <<<
st.markdown(
    """
    <style>
    /* Gesamter Hintergrund hellgrün */
    .stApp {
        background-color: #e8fbe8;
    }

    /* Sidebar etwas dunkler hellgrün */
    section[data-testid="stSidebar"] {
        background-color: #d4f3d4 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# >>> Titel: erste Zeile blau, zweite Zeile normal schwarz (inline CSS zwingend)
st.markdown(
    """
    <h1 style="color:#0099CC; font-size:30px; font-weight:800; text-align:center; line-height:1.2; margin-bottom:10px;">
        GreenSight – Smart Monitoring for Sustainable Algal Biotechnology
    </h1>
    <p style="color:black; font-size:18px; text-align:center; line-height:1.2;">
        Auswertungsprogramm für den Extrakt aus Algenzellen (Scenedesmus)
    </p>
    """,
    unsafe_allow_html=True
)

# === Datei Upload ===
uploaded_file = st.file_uploader("CSV oder TXT Datei hochladen", type=["csv", "txt"])

if uploaded_file is not None:

    # === Funktion zum Laden ===
    def load_spectral_file(file_or_path):
        if isinstance(file_or_path, str):
            ext = os.path.splitext(file_or_path)[1].lower()
        else:
            ext = os.path.splitext(file_or_path.name)[1].lower()

        if ext == ".csv":
            return pd.read_csv(file_or_path, header=None)

        if ext in [".txt", ".text"]:
            if isinstance(file_or_path, str):
                with open(file_or_path, "r") as f:
                    lines = f.readlines()
            else:
                lines = file_or_path.read().decode("utf-8").splitlines()

            # Header finden
            for i, line in enumerate(lines):
                if line.strip().startswith("200"):   # ← einzig geänderte Zeile
                    start = i + 1
                    break
            else:
                raise ValueError("❌ '200' nicht gefunden!")

            data_lines = lines[start:]

            # Dezimal-Komma erkennen und ersetzen
            uses_decimal_comma = any(
                ("," in ln and any(c.isdigit() for c in ln))
                for ln in data_lines[:10]
            )
            if uses_decimal_comma:
                data_lines = [ln.replace(",", ".") for ln in data_lines]

            return pd.read_csv(StringIO("\n".join(data_lines)), sep=r"\s+", header=None, engine="python")

        raise ValueError(f"❌ Dateiformat '{ext}' wird nicht unterstützt!")

    # === Daten laden ===
    try:
        df = load_spectral_file(uploaded_file)
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei: {e}")
        st.stop()

    if df.shape[1] < 2:
        st.error("❌ Die Datei muss mindestens zwei Spalten enthalten!")
        st.stop()

    df = df.iloc[:, :2]
    df.columns = ["Wavelength", "Intensity"]
    df = df.apply(pd.to_numeric, errors="coerce").dropna()

    heute = datetime.now().strftime("%d %B %Y")

    ## --- Baseline bei 850 nm ---
    #target_nm = 850
    #if (df["Wavelength"] == target_nm).any():
    #    baseline_value = df.loc[df["Wavelength"] == target_nm, "Intensity"].values[0]
    #else:
    #    nearest_idx = (df["Wavelength"] - target_nm).abs().idxmin()
    #    baseline_value = df.loc[nearest_idx, "Intensity"]

    #df["Y_corrected"] = df["Intensity"] - baseline_value
    #df.loc[df["Wavelength"] == target_nm, "Y_corrected"] = 0.0
    #df["Y_corrected"] = df["Y_corrected"].round(6)

    #st.write(f"✅ Baseline bei 850 nm korrigiert → exakt 0")

    ## --- Peak 650–750 nm ---
    #subset = df[(df["Wavelength"] >= 650) & (df["Wavelength"] <= 750)]
    #if subset.empty:
    #    st.warning("⚠️ Kein Datenbereich für Peak 650–750 nm gefunden!")
    #    peak_wavelength = np.nan
    #    peak_intensity = np.nan
    #else:
    #    peak_idx = subset["Y_corrected"].idxmax()
    #    peak_wavelength = df.loc[peak_idx, "Wavelength"]
    #    peak_intensity = df.loc[peak_idx, "Y_corrected"]
    #    st.write(f"🟢 Exakter Peak: {peak_wavelength:.2f} nm, Intensität: {peak_intensity:.2f} a.u. ")


    # --- Baseline als Mittelwert 740–760 nm ---
    baseline_subset = df[(df["Wavelength"] >= 740) & (df["Wavelength"] <= 760)]

    if baseline_subset.empty:
        st.warning("⚠️ Kein Datenbereich für Baseline 740–760 nm gefunden!")
        baseline_value = np.nan
    else:
        baseline_value = baseline_subset["Intensity"].mean()
        st.write(
            f"✅ Baseline (Mittelwert 740–760 nm): {baseline_value:.6f}"
        )

    # --- Baseline-Korrektur ---
    df["Y_corrected"] = df["Intensity"] - baseline_value
    df["Y_corrected"] = df["Y_corrected"].round(6)

    st.write("✅ Baseline 740–760 nm korrigiert → Mittelwert = 0")

    # --- Peak 650–750 nm ---
    subset = df[(df["Wavelength"] >= 650) & (df["Wavelength"] <= 750)]

    if subset.empty:
        st.warning("⚠️ Kein Datenbereich für Peak 650–750 nm gefunden!")
        peak_wavelength = np.nan
        peak_intensity = np.nan
    else:
        peak_idx = subset["Y_corrected"].idxmax()
        peak_wavelength = df.loc[peak_idx, "Wavelength"]
        peak_intensity = df.loc[peak_idx, "Y_corrected"]

        st.write(
            f"🟢 Exakter Peak: {peak_wavelength:.2f} nm, "
            f"Intensität: {peak_intensity:.2f} a.u."
        )

    # --- OD Peak ±5 nm ---
    if not np.isnan(peak_wavelength):
        od_low  = math.ceil((peak_wavelength - 5) / 10) * 10
        od_high = math.ceil((peak_wavelength + 5) / 10) * 10
        od_region = df[(df["Wavelength"] >= od_low) & (df["Wavelength"] <= od_high)]
        #od_value = od_region["Intensity"].mean()
        od_value = od_region["Y_corrected"].mean()
        st.write(f"✅ OD (660-670 nm) = {od_value:.4f}")
    else:
        od_value = np.nan

    # --- Integral 660–670 nm ---
    lower, upper = 660, 670
    sum_region = df[(df["Wavelength"] >= lower) & (df["Wavelength"] <= upper)]
    integral_uncorrected = np.trapz(sum_region["Intensity"], sum_region["Wavelength"])
    integral_corrected   = np.trapz(sum_region["Y_corrected"], sum_region["Wavelength"])
    st.write(f"📈 Integral (Baseline-uncorrected, {lower}-{upper} nm): {integral_uncorrected:.4f}")
    st.write(f"📈 Integral (Baseline-corrected, {lower}-{upper} nm): {integral_corrected:.4f}")

    # --- Plot ---
    plt.figure(figsize=(8, 5))

    # Spektren
    plt.plot(df["Wavelength"], df["Intensity"], color="blue", label="Baseline-uncorrected spectrum")
    plt.plot(df["Wavelength"], df["Y_corrected"], color="green", label="Baseline-corrected spectrum")

    # Fill-Bereiche
    plt.fill_between(sum_region["Wavelength"], sum_region["Intensity"], color="blue", alpha=0.15,
                     label=f"Integral ({lower}-{upper} nm): {integral_uncorrected:.4f}")
    plt.fill_between(sum_region["Wavelength"], sum_region["Y_corrected"], color="orange", alpha=0.35,
                     label=f"Integral ({lower}-{upper} nm): {integral_corrected:.4f}")

    # Peak markieren
    if not np.isnan(peak_wavelength):
        plt.plot(peak_wavelength, peak_intensity, 'ro',
                 label=f"Peak: {peak_wavelength:.2f} nm | {peak_intensity:.2f} a.u.")

    # Achsen & Titel
    plt.title("GreenSight – Smart Monitoring for Sustainable Algal Biotechnology")
    plt.xlabel("Wavelength [nm]")
    plt.ylabel("Absorbance [a.u.]")
    plt.xlim(250, df["Wavelength"].max())
    plt.ylim(0, 1.0)
    plt.yticks(np.arange(0, 1.1, 0.1))

    # === Legende exakt wie Desktop-Version ===
    handles, labels = plt.gca().get_legend_handles_labels()

    # Header
    header_handle = plt.Line2D([], [], color="white")
    header_label = f"Comparative absorption spectra of algae\n(Scenedesmus), {heute}\n"
    handles.insert(0, header_handle)
    labels.insert(0, header_label)

    # Funktion zum Einfügen nach einem Label
    def insert_after(base_label, new_handle, new_label):
        idx = labels.index(base_label)
        handles.insert(idx + 1, new_handle)
        labels.insert(idx + 1, new_label)

    # OD-Eintrag
    od_handle = plt.Line2D([], [], color="white")
    od_label = f"OD ({od_low}-{od_high} nm): {od_value:.4f}"

    # --- Reihenfolge setzen ---

    # 1. Baseline-uncorrected spectrum
    insert_after("Baseline-uncorrected spectrum",
                 handles.pop(labels.index(f"Integral ({lower}-{upper} nm): {integral_uncorrected:.4f}")),
                 labels.pop(labels.index(f"Integral ({lower}-{upper} nm): {integral_uncorrected:.4f}")))

    insert_after(f"Integral ({lower}-{upper} nm): {integral_uncorrected:.4f}", od_handle, od_label)

    # Leerzeile (eine echte Zeile Abstand) zwischen OD und Baseline-corrected spectrum
    blank_handle = plt.Line2D([], [], color="white")
    blank_label = ""
    insert_after(od_label, blank_handle, blank_label)

    # 2. Baseline-corrected spectrum
    insert_after("Baseline-corrected spectrum",
                 handles.pop(labels.index(f"Integral ({lower}-{upper} nm): {integral_corrected:.4f}")),
                 labels.pop(labels.index(f"Integral ({lower}-{upper} nm): {integral_corrected:.4f}")))

    # Legende zeichnen
    leg = plt.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.435, 1),
                     borderaxespad=0.5, labelspacing=0.6)
    for text in leg.get_texts():
        text.set_ha('left')
        text.set_x(text.get_position()[0] + 0.01)

    # Streamlit Plot
    st.pyplot(plt)

    # --- Hochauflösender Download (600 DPI) ---
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=600)
    buf.seek(0)
    st.download_button("Download Plot", buf, file_name="spectrum.png", mime="image/png")
