#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 2025

@author: medphysiker_sergei
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from datetime import datetime
import os
from io import StringIO, BytesIO

st.set_page_config(page_title="GreenSight – Algae Analysis", layout="wide")

st.title("GreenSight – Smart Monitoring for Sustainable Algal Biotechnology")

# === Datei Upload ===
uploaded_file = st.file_uploader("CSV oder TXT Datei hochladen", type=["csv", "txt"])

if uploaded_file is not None:

    # === Datei laden ===
    def load_spectral_file(path_or_file):
        if isinstance(path_or_file, str):
            ext = os.path.splitext(path_or_file)[1].lower()
        else:
            ext = os.path.splitext(path_or_file.name)[1].lower()

        if ext == ".csv":
            return pd.read_csv(path_or_file, header=None)

        if ext in [".txt", ".text"]:
            if isinstance(path_or_file, str):
                with open(path_or_file, "r") as f:
                    lines = f.readlines()
            else:
                lines = path_or_file.read().decode("utf-8").splitlines()

            for i, line in enumerate(lines):
                if "Begin Spectral Data" in line:
                    start = i + 1
                    break
            else:
                raise ValueError("❌ 'Begin Spectral Data' nicht gefunden!")

            data_lines = lines[start:]
            uses_decimal_comma = any(
                ("," in ln and any(char.isdigit() for char in ln))
                for ln in data_lines[:5]
            )
            if uses_decimal_comma:
                data_lines = [ln.replace(",", ".") for ln in data_lines]

            return pd.read_csv(StringIO("".join(data_lines)), sep=r"\s+", header=None, engine="python")

        raise ValueError(f"❌ Dateiformat '{ext}' wird nicht unterstützt!")

    # Daten einlesen
    df = load_spectral_file(uploaded_file)

    if df.shape[1] < 2:
        st.error("❌ Die Datei muss mindestens zwei Spalten enthalten!")
    else:
        df = df.iloc[:, :2]
        df.columns = ["Wavelength", "Intensity"]
        df = df.apply(pd.to_numeric, errors="coerce").dropna()

        heute = datetime.now().strftime("%d %B %Y")

        # === Baseline bei 850 nm ===
        target_nm = 850
        if (df["Wavelength"] == target_nm).any():
            baseline_value = df.loc[df["Wavelength"] == target_nm, "Intensity"].values[0]
        else:
            nearest_idx = (df["Wavelength"] - target_nm).abs().idxmin()
            baseline_value = df.loc[nearest_idx, "Intensity"]

        df["Y_corrected"] = df["Intensity"] - baseline_value
        df.loc[df["Wavelength"] == target_nm, "Y_corrected"] = 0.0

        st.write(f"✅ Baseline bei 850 nm: {baseline_value:.6f}")

        # === Peak 650–750 nm ===
        subset = df[(df["Wavelength"] >= 650) & (df["Wavelength"] <= 750)]
        peak_idx = subset["Y_corrected"].idxmax()
        peak_wavelength = df.loc[peak_idx, "Wavelength"]
        peak_intensity = df.loc[peak_idx, "Y_corrected"]
        st.write(f"🟢 Exakter Peak: {peak_wavelength:.2f} nm, Intensität: {peak_intensity:.2f}")

        # === OD Peak ±5 nm ===
        od_low  = math.ceil((peak_wavelength - 5) / 10) * 10
        od_high = math.ceil((peak_wavelength + 5) / 10) * 10
        od_region = df[(df["Wavelength"] >= od_low) & (df["Wavelength"] <= od_high)]
        od_value = od_region["Intensity"].mean()
        st.write(f"✅ OD (peak ±5 nm) = {od_value:.4f}")

        # === Integral 660–670 nm ===
        lower, upper = 660, 670
        sum_region = df[(df["Wavelength"] >= lower) & (df["Wavelength"] <= upper)]
        integral_uncorrected = np.trapezoid(sum_region["Intensity"], sum_region["Wavelength"])
        integral_corrected   = np.trapezoid(sum_region["Y_corrected"], sum_region["Wavelength"])
        st.write(f"📈 Integral (uncorrected, {lower}-{upper} nm): {integral_uncorrected:.4f}")
        st.write(f"📈 Integral (corrected, {lower}-{upper} nm): {integral_corrected:.4f}")

        # === Plot ===
        plt.figure(figsize=(8, 5))

        # Spektren
        plt.plot(df["Wavelength"], df["Intensity"], color="blue", label="Baseline-uncorrected spectrum")
        plt.plot(df["Wavelength"], df["Y_corrected"], color="green", label="Baseline-corrected spectrum")

        # Integralflächen
        plt.fill_between(sum_region["Wavelength"], df.loc[sum_region.index, "Intensity"], color="blue", alpha=0.15)
        plt.fill_between(sum_region["Wavelength"], df.loc[sum_region.index, "Y_corrected"], color="orange", alpha=0.35)

        # Peak markieren
        plt.plot(peak_wavelength, peak_intensity, 'ro', label=f"Peak: {peak_wavelength:.2f} nm | {peak_intensity:.2f} a.u.")

        # Achsen und Titel
        plt.title("GreenSight – Smart Monitoring for Sustainable Algal Biotechnology")
        plt.xlabel("Wavelength [nm]")
        plt.ylabel("Absorbance [a.u.]")
        plt.xlim(250, df["Wavelength"].max())
        plt.ylim(0, 1.0)
        plt.yticks(np.arange(0, 1.1, 0.1))

        # === Legende exakt wie im Spyder-Code ===
        handles, labels = plt.gca().get_legend_handles_labels()

        header_handle = plt.Line2D([], [], color="white")
        header_label = f"Comparative absorption spectra of algae\n(Scenedesmus), {heute}\n"
        handles.insert(0, header_handle)
        labels.insert(0, header_label)

        # Baseline-uncorrected Spectrum Position
        base_idx = labels.index("Baseline-uncorrected spectrum")

        # Integral unter Baseline-uncorrected
        int_unc_handle = plt.Line2D([], [], color="white")
        int_unc_label  = f"Integral ({lower}-{upper} nm, uncorrected): {integral_uncorrected:.4f}"
        handles.insert(base_idx + 1, int_unc_handle)
        labels.insert(base_idx + 1, int_unc_label)

        # Integral unter Baseline-corrected
        int_corr_handle = plt.Line2D([], [], color="white")
        int_corr_label  = f"Integral ({lower}-{upper} nm, corrected): {integral_corrected:.4f}"
        handles.insert(base_idx + 2, int_corr_handle)
        labels.insert(base_idx + 2, int_corr_label)

        # OD direkt darunter
        od_handle = plt.Line2D([], [], color="white")
        od_label  = f"OD ({od_low}-{od_high} nm): {od_value:.4f}"
        handles.insert(base_idx + 3, od_handle)
        labels.insert(base_idx + 3, od_label)

        plt.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.435, 1), borderaxespad=0.5, labelspacing=0.6)

        # Plot im Streamlit anzeigen
        st.pyplot(plt)

        # === Download Plot als PNG ===
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        st.download_button("Download Plot", buf, file_name="spectrum.png", mime="image/png")
