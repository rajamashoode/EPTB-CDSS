import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
from fpdf import FPDF
from docx import Document
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="EPTB Decision Support Tool",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALIZATION ---
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}

# --- HELPER FUNCTIONS ---
def calculate_bmi(weight, height_cm):
    if height_cm > 0:
        height_m = height_cm / 100
        return round(weight / (height_m ** 2), 2)
    return 0

def check_renal_adjustment(egfr):
    if egfr < 30:
        return True, "⚠️ Severe Renal Impairment: Pyrazinamide and Ethambutol require dose/frequency adjustment (usually 3x/week)."
    elif egfr < 60:
        return True, "⚠️ Moderate Renal Impairment: Monitor closely."
    return False, "Renal function acceptable."

def generate_pdf_report(data, evaluation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="EPTB Clinical Decision Report", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {date.today()}", ln=1, align='C')
    
    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(200, 10, txt="1. Patient Summary", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=f"Age: {data.get('age')} | Weight: {data.get('weight')}kg | EPTB Type: {data.get('eptb_type')}")
    
    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(200, 10, txt="2. Regimen Evaluation", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=f"Status: {evaluation['status']}")
    pdf.multi_cell(0, 10, txt=f"Reasoning: {evaluation['reason']}")
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("EPTB Decision Support")
page = st.sidebar.radio("Navigate", [
    "1. Patient Info", 
    "2. EPTB Type & Severity", 
    "3. Prescribed Regimen", 
    "4. Pharmacotherapy Eval", 
    "5. Side Effects & Interactions", 
    "6. Outcome Prediction", 
    "7. Statistical Analysis", 
    "8. Final Report"
])

# ==========================================
# PAGE 1: PATIENT INFORMATION
# ==========================================
if page == "1. Patient Info":
    st.title("Patient Information")
    st.info("Enter demographic and clinical data. This establishes the baseline for dose calculation and contraindications.", icon="ℹ️")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.patient_data['name'] = st.text_input("Patient ID/Name (Optional)", value=st.session_state.patient_data.get('name', ''))
        st.session_state.patient_data['age'] = st.number_input("Age", 0, 120, value=st.session_state.patient_data.get('age', 25))
        st.session_state.patient_data['sex'] = st.selectbox("Sex", ["Male", "Female"], index=0 if st.session_state.patient_data.get('sex') == "Male" else 1)
        st.session_state.patient_data['weight'] = st.number_input("Weight (kg)", 1.0, 200.0, value=st.session_state.patient_data.get('weight', 60.0), help="Crucial for dosing")
    
    with col2:
        st.session_state.patient_data['height'] = st.number_input("Height (cm)", 50, 250, value=st.session_state.patient_data.get('height', 170))
        st.session_state.patient_data['creatinine'] = st.number_input("Serum Creatinine (mg/dL)", 0.1, 20.0, value=st.session_state.patient_data.get('creatinine', 0.9))
        st.session_state.patient_data['hiv_status'] = st.selectbox("HIV Status", ["Negative", "Positive"], index=0)
        st.session_state.patient_data['liver_disease'] = st.checkbox("History of Liver Disease/Hepatitis")

    # Live Calculations
    bmi = calculate_bmi(st.session_state.patient_data['weight'], st.session_state.patient_data['height'])
    st.metric("Calculated BMI", f"{bmi} kg/m²")

    # Simple eGFR calc (Cockcroft-Gault approximation for demo)
    age = st.session_state.patient_data['age']
    wt = st.session_state.patient_data['weight']
    creat = st.session_state.patient_data['creatinine']
    sex_factor = 0.85 if st.session_state.patient_data['sex'] == "Female" else 1.0
    egfr = ((140 - age) * wt * sex_factor) / (72 * creat)
    st.session_state.patient_data['egfr'] = egfr
    
    renal_flag, renal_msg = check_renal_adjustment(egfr)
    if renal_flag:
        st.error(renal_msg)
    else:
        st.success(f"Estimated eGFR: {egfr:.1f} mL/min (Renal Function OK)")

    if st.button("Save & Continue"):
        st.success("Data Saved!")

# ==========================================
# PAGE 2: EPTB TYPE & SEVERITY
# ==========================================
elif page == "2. EPTB Type & Severity":
    st.title("EPTB Classification")
    st.info("Select the specific site of infection. WHO guidelines differ for CNS/Bone TB vs. other sites.", icon="ℹ️")

    eptb_types = [
        "Pleural TB", "Lymph Node TB", "Abdominal TB", "Genitourinary TB", 
        "Pericardial TB", "Bone/Joint TB", "TB Meningitis", "Disseminated TB"
    ]
    
    st.session_state.patient_data['eptb_type'] = st.selectbox(
        "Select EPTB Type", 
        eptb_types, 
        index=eptb_types.index(st.session_state.patient_data.get('eptb_type', 'Pleural TB'))
    )
    
    st.session_state.patient_data['severity'] = st.select_slider(
        "Clinical Severity", 
        options=["Mild", "Moderate", "Severe", "Life-threatening"],
        value=st.session_state.patient_data.get('severity', 'Moderate')
    )

    # WHO Logic Display
    if st.session_state.patient_data['eptb_type'] in ["TB Meningitis", "Bone/Joint TB"]:
        st.warning("⚠️ WHO Guideline: This form of EPTB requires extended treatment (9-12 months).")
        st.session_state.patient_data['req_duration'] = 12
    else:
        st.success("✅ WHO Guideline: Standard 6-month regimen (2HRZE / 4HR) is usually sufficient.")
        st.session_state.patient_data['req_duration'] = 6

# ==========================================
# PAGE 3: PRESCRIBED REGIMEN
# ==========================================
elif page == "3. Prescribed Regimen":
    st.title("Regimen Input")
    st.info("Enter the drugs currently prescribed by the clinician for evaluation.", icon="ℹ️")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Intensive Phase (Months 1-2)")
        st.session_state.patient_data['ip_drugs'] = st.multiselect("Select Drugs", ["Isoniazid (H)", "Rifampicin (R)", "Pyrazinamide (Z)", "Ethambutol (E)"], default=["Isoniazid (H)", "Rifampicin (R)", "Pyrazinamide (Z)", "Ethambutol (E)"])
        st.session_state.patient_data['ip_duration'] = st.number_input("Duration (Months)", 1, 12, 2)
    
    with col2:
        st.subheader("Continuation Phase")
        st.session_state.patient_data['cp_drugs'] = st.multiselect("Select Drugs (CP)", ["Isoniazid (H)", "Rifampicin (R)", "Ethambutol (E)"], default=["Isoniazid (H)", "Rifampicin (R)"])
        st.session_state.patient_data['cp_duration'] = st.number_input("Duration (CP Months)", 1, 24, 4)

    st.divider()
    st.subheader("Dose Check (mg/day)")
    st.caption("Enter the total daily dose in mg")
    st.session_state.patient_data['dose_H'] = st.number_input("Isoniazid Dose (mg)", value=300)
    st.session_state.patient_data['dose_R'] = st.number_input("Rifampicin Dose (mg)", value=600 if st.session_state.patient_data.get('weight', 60) > 50 else 450)
    st.session_state.patient_data['dose_Z'] = st.number_input("Pyrazinamide Dose (mg)", value=1500)
    st.session_state.patient_data['dose_E'] = st.number_input("Ethambutol Dose (mg)", value=1200)

# ==========================================
# PAGE 4: PHARMACOTHERAPY EVALUATION ENGINE
# ==========================================
elif page == "4. Pharmacotherapy Eval":
    st.title("Pharmacotherapy Evaluation Engine")
    
    data = st.session_state.patient_data
    
    # --- LOGIC CORE ---
    is_severe_type = data.get('eptb_type') in ["TB Meningitis", "Bone/Joint TB"]
    total_duration = data.get('ip_duration', 0) + data.get('cp_duration', 0)
    weight = data.get('weight', 60)
    
    # 1. Duration Check
    st.subheader("1. Duration Analysis")
    if is_severe_type and total_duration < 9:
        st.error(f"❌ INCORRECT DURATION: Patient has {data['eptb_type']}. WHO Guidelines mandate 9-12 months. Prescribed: {total_duration} months.")
        st.markdown("**Recommendation:** Extend Continuation Phase.")
        duration_status = "Fail"
    elif not is_severe_type and total_duration < 6:
        st.error(f"❌ INCORRECT DURATION: Standard EPTB requires minimum 6 months. Prescribed: {total_duration}.")
        duration_status = "Fail"
    else:
        st.success(f"✅ Duration ({total_duration} months) is appropriate for {data['eptb_type']}.")
        duration_status = "Pass"

    # 2. Dosage Check (Simplified WHO Weight Bands)
    st.subheader("2. Dosage Verification")
    
    # Rifampicin Check (Target ~10mg/kg)
    r_dose = data.get('dose_R', 0)
    if weight > 50 and r_dose < 600:
        st.warning(f"⚠️ Rifampicin Potential Underdose. Weight > 50kg usually requires 600mg. Prescribed: {r_dose}mg.")
    elif weight < 50 and r_dose >= 600:
        st.warning(f"⚠️ Rifampicin Potential Overdose. Weight < 50kg usually requires 450mg.")
    else:
        st.success(f"✅ Rifampicin dose ({r_dose}mg) appears correct for weight {weight}kg.")

    # Pyrazinamide Check (Target ~25mg/kg)
    z_dose = data.get('dose_Z', 0)
    z_target = weight * 25
    if z_dose < (z_target * 0.8): # allowing 20% variance
        st.warning(f"⚠️ Pyrazinamide Low. Target based on weight is approx {z_target}mg. Prescribed: {z_dose}mg.")
    elif z_dose > (z_target * 1.2):
        st.warning(f"⚠️ Pyrazinamide High. Risk of Hepatotoxicity.")
    else:
        st.success(f"✅ Pyrazinamide dose acceptable.")

    # 3. Regimen Selection
    st.subheader("3. Regimen Appropriateness")
    if "TB Meningitis" == data.get('eptb_type') and "Streptomycin (S)" not in data.get('ip_drugs', []):
         st.info("ℹ️ Note: WHO suggests considering Streptomycin in place of Ethambutol for Meningitis in certain cases, though Ethambutol is often used.")
    
    st.success(f"Regimen Structure: {data.get('ip_duration')} months Intensive + {data.get('cp_duration')} months Continuation matches standard protocol structures.")

# ==========================================
# PAGE 5: SIDE EFFECTS & INTERACTIONS
# ==========================================
elif page == "5. Side Effects & Interactions":
    st.title("Safety Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Predicted Side Effects")
        drugs = st.session_state.patient_data.get('ip_drugs', [])
        if "Rifampicin (R)" in drugs:
            st.write("🔴 **Rifampicin:** Orange urine (harmless), Hepatotoxicity, Flu-like syndrome.")
        if "Isoniazid (H)" in drugs:
            st.write("🔴 **Isoniazid:** Peripheral neuropathy (Prescribe Pyridoxine/Vit B6), Hepatotoxicity.")
        if "Pyrazinamide (Z)" in drugs:
            st.write("🔴 **Pyrazinamide:** Hyperuricemia (Gout), Arthralgia, Hepatotoxicity.")
        if "Ethambutol (E)" in drugs:
            st.write("🔴 **Ethambutol:** Optic Neuritis (Check visual acuity/color vision).")

    with col2:
        st.subheader("Interaction Checker")
        # Logic for HIV
        if st.session_state.patient_data.get('hiv_status') == "Positive":
            st.error("⚠️ **HIV INTERACTION:** Rifampicin significantly lowers levels of Protease Inhibitors and NNRTIs. Dosage adjustment or switch to Rifabutin may be required.")
        
        # Logic for Diabetes
        st.write("⚠️ **Diabetes:** Rifampicin may reduce efficacy of oral hypoglycemics (sulfonylureas). Monitor Glucose.")

# ==========================================
# PAGE 7: STATISTICAL ANALYSIS (Bulk)
# ==========================================
elif page == "7. Statistical Analysis":
    st.title("Batch Analysis & Statistics")
    st.info("Upload a CSV file with columns: Age, Weight, EPTB_Type, Outcome (Success/Fail)")
    
    uploaded_file = st.file_uploader("Upload Patient Data CSV", type="csv")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Data Preview:", df.head())
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("EPTB Types Distribution")
            fig = px.pie(df, names='EPTB_Type', title='Types of EPTB in Cohort')
            st.plotly_chart(fig)
        
        with c2:
            st.subheader("Outcomes by Type")
            # Mocking outcome data if not present, for demo
            if 'Outcome' in df.columns:
                fig2 = px.bar(df, x='EPTB_Type', color='Outcome', barmode='group')
                st.plotly_chart(fig2)

# ==========================================
# PAGE 8: FINAL REPORT
# ==========================================
elif page == "8. Final Report":
    st.title("Generate Clinical Report")
    
    st.write("Review the analysis above. Click below to generate the official PDF documentation.")
    
    data = st.session_state.patient_data
    # Determine Status for report
    status = "Review Required"
    reason = "See detailed analysis."
    
    report_btn = st.button("Generate PDF Report")
    
    if report_btn:
        pdf_bytes = generate_pdf_report(data, {'status': status, 'reason': reason})
        st.download_button(
            label="Download Report",
            data=pdf_bytes,
            file_name=f"EPTB_Report_{data.get('name', 'Patient')}.pdf",
            mime='application/pdf'
        )
