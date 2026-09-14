"""Interactive Nursing Station IV Drip Monitoring & Demo Dashboard.

Assigned Module: Nifa (nifa/drip_monitoring/)
Technologies: Streamlit, Python
DISCLAIMER: This is a hackathon prototype for demonstration purposes only.
Not intended for clinical diagnosis or real medical monitoring.
"""

import os
import sys
import json
import streamlit as st

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from nifa.drip_monitoring.src.constants import (
    SeverityLevel,
    AlertStatus,
    AlertCategory,
    DripEventType,
    DropFactor,
)
from nifa.drip_monitoring.src.infusion_manager import PatientInfusionManager
from nifa.drip_monitoring.src.drip_calculator import DripCalculator
from simulator.drip_simulator.drip_simulator import IVDripSimulator, DripSimulationScenario
from simulator.drip_simulator.telemetry_generator import DripTelemetryGenerator

st.set_page_config(
    page_title="SmartPatientCare — IV Drip Monitor",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern clinical nursing station aesthetic
st.markdown(
    """
    <style>
    .demo-banner {
        background-color: #fff3cd;
        border-left: 6px solid #ffc107;
        padding: 12px 18px;
        margin-bottom: 20px;
        border-radius: 4px;
        color: #856404;
        font-weight: 500;
    }
    .status-card-normal {
        background-color: #e8f5e9;
        border-left: 6px solid #2e7d32;
        padding: 14px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .status-card-warning {
        background-color: #fff8e1;
        border-left: 6px solid #f57f17;
        padding: 14px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .status-card-critical {
        background-color: #ffebee;
        border-left: 6px solid #c62828;
        padding: 14px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .status-card-completed {
        background-color: #f3e5f5;
        border-left: 6px solid #7b1fa2;
        padding: 14px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .metric-box {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .badge-patient {
        background: #1976d2;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    .badge-equipment {
        background: #e65100;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_infusion_manager():
    return PatientInfusionManager()


@st.cache_resource
def get_telemetry_generator():
    return DripTelemetryGenerator()


manager = get_infusion_manager()
generator = get_telemetry_generator()

# Persistent session state for simulator
if "simulators" not in st.session_state:
    st.session_state.simulators = {}

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.title("🏥 SmartPatientCare")
    st.markdown("**Module:** IV Drip Monitoring (`nifa/`)")
    st.markdown("**Assigned Teammate:** Nifa")
    st.divider()

    # Patient Selector
    patients = manager.get_all_sessions()
    patient_options = {f"{s.patient_id} — {s.patient_name} ({s.room_id})": s.patient_id for s in patients}
    selected_label = st.selectbox("Select Patient Room:", list(patient_options.keys()))
    selected_pid = patient_options[selected_label]
    session = manager.get_session(selected_pid)

    # Initialize simulator for this patient if not present
    if selected_pid not in st.session_state.simulators:
        st.session_state.simulators[selected_pid] = IVDripSimulator(
            patient_id=session.patient_id,
            room_id=session.room_id,
            total_volume_ml=session.total_volume_ml,
            prescribed_rate_ml_h=session.prescribed_rate_ml_h,
            drop_factor=session.drop_factor,
        )
    simulator: IVDripSimulator = st.session_state.simulators[selected_pid]

    st.markdown("### 📋 Patient Card")
    st.markdown(f"**Name:** {session.patient_name}")
    st.markdown(f"**Room:** `{session.room_id}` | **ID:** `{session.patient_id}`")
    st.markdown(f"**Diagnosis:** {session.patient_condition}")
    st.markdown(f"**Status:** `{session.patient_status}`")
    st.divider()

    st.markdown("### 💉 Infusion Order")
    st.markdown(f"**Fluid:** {session.fluid_name}")
    st.markdown(f"**Bag Volume:** {session.total_volume_ml:.0f} mL")
    st.markdown(f"**Prescribed Rate:** {session.prescribed_rate_ml_h:.0f} mL/h")
    st.markdown(f"**Drop Factor:** {session.drop_factor} gtt/mL")
    st.divider()

    st.caption(
        "⚠️ **HACKATHON DEMO PROTOTYPE**\n\n"
        "This software is developed strictly for hackathon evaluation and demonstration. "
        "It does not interface with certified medical infusion pumps or physiological sensors."
    )


# ----------------- MAIN CONTENT -----------------

# Demo Banner
st.markdown(
    """
    <div class="demo-banner">
        <strong>⚠️ HACKATHON DEMONSTRATION MODE (SIMULATED DATA)</strong><br>
        All vital signs, flow rates, and IV fluid mechanics displayed below are simulated telemetry.
        This module evaluates real-time drip algorithms, anomaly detection, and event schema compliance.
    </div>
    """,
    unsafe_allow_html=True,
)

# Title and Status Overview
col_title, col_stat = st.columns([3, 1])
with col_title:
    st.subheader(f"Nursing Station Telemetry — {session.patient_name} ({session.room_id})")
    st.caption(f"Infusion Solution: **{session.fluid_name}** | Target Rate: **{session.prescribed_rate_ml_h} mL/h**")

# Determine active clinical condition
active_alerts = manager.alert_manager.get_active_alerts(patient_id=selected_pid)
critical_alerts = [a for a in active_alerts if a["severity"] == SeverityLevel.CRITICAL.value]
warning_alerts = [a for a in active_alerts if a["severity"] == SeverityLevel.WARNING.value]

if simulator.remaining_volume_ml <= 0.0:
    system_status = "IV COMPLETED"
    card_class = "status-card-completed"
    status_icon = "🟣"
elif critical_alerts:
    system_status = "CRITICAL ALERT"
    card_class = "status-card-critical"
    status_icon = "🔴"
elif warning_alerts:
    system_status = "WARNING"
    card_class = "status-card-warning"
    status_icon = "🟡"
else:
    system_status = "NORMAL"
    card_class = "status-card-normal"
    status_icon = "🟢"

with col_stat:
    st.markdown(
        f"""
        <div class="{card_class}" style="text-align: center;">
            <div style="font-size: 13px; font-weight: bold; text-transform: uppercase;">System Status</div>
            <div style="font-size: 20px; font-weight: 800;">{status_icon} {system_status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------- METRIC CARDS -----------------
m1, m2, m3, m4 = st.columns(4)

flow_delta = simulator.current_flow_rate_ml_h - simulator.prescribed_rate_ml_h
flow_delta_str = f"{flow_delta:+.1f} mL/h vs prescribed" if simulator.prescribed_rate_ml_h > 0 else "0"

with m1:
    st.metric(
        label="Flow Rate (mL/h)",
        value=f"{simulator.current_flow_rate_ml_h:.1f} mL/h",
        delta=flow_delta_str,
        delta_color="off" if abs(flow_delta) < 5 else ("inverse" if flow_delta > 0 else "normal"),
    )

with m2:
    st.metric(
        label="Drip Rate (gtt/min)",
        value=f"{simulator.drops_per_min:.1f} gtt/min",
        help=f"Drop factor: {simulator.drop_factor} drops/mL",
    )

with m3:
    rem_pct = simulator.volume_percentage
    st.metric(
        label="Volume Remaining",
        value=f"{simulator.remaining_volume_ml:.1f} mL",
        delta=f"{rem_pct:.1f}% remaining",
        delta_color="normal" if rem_pct > 15 else "inverse",
    )

with m4:
    _, eta_display = DripCalculator.calculate_time_to_completion(
        simulator.remaining_volume_ml, simulator.current_flow_rate_ml_h
    )
    st.metric(
        label="Time to Empty (ETA)",
        value=eta_display,
        help="Estimated run-out time based on current rate",
    )

# Fluid level visual progress
progress_val = max(0.0, min(1.0, simulator.remaining_volume_ml / simulator.total_volume_ml))
st.progress(
    progress_val,
    text=f"IV Bag Level: {simulator.remaining_volume_ml:.1f} mL / {simulator.total_volume_ml:.1f} mL ({progress_val * 100:.1f}%)",
)

st.divider()

# ----------------- HACKATHON DEMO SIMULATION PANEL -----------------
st.markdown("### 🎛️ Hackathon Demo Control Panel (One-Click Scenario Simulation)")
st.caption(
    "Use these interactive controls to demonstrate how Nifa's monitoring and anomaly algorithms "
    "detect abnormal readings, generate standardized events, and update nursing station alerts."
)

btn_c1, btn_c2, btn_c3, btn_c4, btn_c5, btn_c6, btn_c7 = st.columns(7)

with btn_c1:
    if st.button("🟢 Normal\n(100 mL/h)", use_container_width=True, help="Simulate standard steady infusion"):
        events = simulator.apply_scenario(DripSimulationScenario.NORMAL)
        manager.update_telemetry(
            patient_id=selected_pid,
            current_flow_rate_ml_h=simulator.current_flow_rate_ml_h,
            clamp_closed=False,
            air_in_line=False,
        )
        st.rerun()

with btn_c2:
    if st.button("🟡 Low Volume\n(10% left)", use_container_width=True, help="Simulate fluid level dropping below 15%"):
        events = simulator.apply_scenario(DripSimulationScenario.WARNING_LOW_VOLUME)
        for evt in events:
            manager.alert_manager.register_event(evt)
        st.rerun()

with btn_c3:
    if st.button("🔴 Occlusion\n(0 mL/h Block)", use_container_width=True, help="Simulate kinked tubing or closed clamp (EQUIPMENT ALERT)"):
        events = simulator.apply_scenario(DripSimulationScenario.CRITICAL_OCCLUSION)
        for evt in events:
            manager.alert_manager.register_event(evt)
        st.rerun()

with btn_c4:
    if st.button("🔴 Runaway\n(250 mL/h)", use_container_width=True, help="Simulate dangerous free-flow over-infusion (PATIENT ALERT)"):
        events = simulator.apply_scenario(DripSimulationScenario.CRITICAL_RUNAWAY)
        for evt in events:
            manager.alert_manager.register_event(evt)
        st.rerun()

with btn_c5:
    if st.button("⚠️ Air Bubble\n(Line Alert)", use_container_width=True, help="Simulate air bubble sensor detection (EQUIPMENT ALERT)"):
        events = simulator.apply_scenario(DripSimulationScenario.CRITICAL_AIR_IN_LINE)
        for evt in events:
            manager.alert_manager.register_event(evt)
        st.rerun()

with btn_c6:
    if st.button("🟣 IV Completed\n(Empty Bag)", use_container_width=True, help="Simulate infusion completion with 0 mL remaining"):
        events = simulator.apply_scenario(DripSimulationScenario.CRITICAL_EMPTY)
        for evt in events:
            manager.alert_manager.register_event(evt)
        st.rerun()

with btn_c7:
    if st.button("🔄 Reset Bag\n(New 500 mL)", use_container_width=True, help="Hang fresh IV bag and resolve active alerts"):
        simulator.reset_bag(500.0)
        manager.reset_bag(selected_pid, total_volume_ml=500.0, prescribed_rate_ml_h=100.0)
        st.rerun()

# Fine-tuning sliders inside an expander
with st.expander("⚙️ Manual Telemetry Fine-Tuning"):
    sc1, sc2 = st.columns(2)
    with sc1:
        custom_flow = st.slider(
            "Simulate Flow Rate (mL/h):",
            min_value=0.0,
            max_value=300.0,
            value=float(simulator.current_flow_rate_ml_h),
            step=5.0,
        )
        if custom_flow != simulator.current_flow_rate_ml_h:
            simulator.current_flow_rate_ml_h = custom_flow
            manager.update_telemetry(selected_pid, current_flow_rate_ml_h=custom_flow)
            st.rerun()

    with sc2:
        custom_rem = st.slider(
            "Simulate Remaining Volume (mL):",
            min_value=0.0,
            max_value=float(simulator.total_volume_ml),
            value=float(simulator.remaining_volume_ml),
            step=10.0,
        )
        if custom_rem != simulator.remaining_volume_ml:
            simulator.infused_volume_ml = simulator.total_volume_ml - custom_rem
            manager.update_telemetry(selected_pid)
            st.rerun()

st.divider()

# ----------------- ACTIVE ALERTS & NOTIFICATIONS -----------------
col_alerts, col_contract = st.columns([2, 1])

with col_alerts:
    st.markdown("### 🚨 Live Alerts & Notifications")

    if not active_alerts:
        st.success("✅ **No active alerts** — Infusion telemetry within safe operating parameters.")
    else:
        for alert in active_alerts:
            sev = alert["severity"]
            status = alert["status"]
            is_critical = sev == SeverityLevel.CRITICAL.value
            is_acknowledged = status == AlertStatus.ACKNOWLEDGED.value

            # Determine category badge
            cat_label = "EQUIPMENT ALERT" if "EQUIPMENT" in alert["message"] or "occlusion" in alert.get("parameter", "") or "air" in alert.get("parameter", "") else "PATIENT ALERT"
            badge_class = "badge-equipment" if "EQUIPMENT" in cat_label else "badge-patient"

            card_border = "#c62828" if is_critical else "#f57f17"
            bg_color = "#fff5f5" if is_critical else "#fffdf0"

            st.markdown(
                f"""
                <div style="border-left: 5px solid {card_border}; background: {bg_color}; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span>
                            <strong style="color: {card_border};">[{sev}]</strong>
                            <span class="{badge_class}">{cat_label}</span>
                            <span style="font-size: 12px; color: #666; margin-left: 8px;">Event: <code>{alert['event_id']}</code></span>
                        </span>
                        <span style="font-size: 12px; color: #444;">Status: <strong>{status}</strong> | Time: {alert['timestamp']}</span>
                    </div>
                    <div style="font-size: 14px; margin-bottom: 8px;">{alert['message']}</div>
                    <div style="font-size: 12px; color: #555;">
                        <strong>Trigger Parameter:</strong> <code>{alert['parameter']}</code> = <code>{alert['value']} {alert['unit']}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Acknowledge and Resolve action buttons
            b_ack, b_res, _ = st.columns([1, 1, 3])
            with b_ack:
                if not is_acknowledged:
                    if st.button("🔔 Acknowledge", key=f"ack_{alert['event_id']}"):
                        manager.alert_manager.acknowledge_alert(alert["event_id"])
                        st.rerun()
            with b_res:
                if st.button("✅ Resolve", key=f"res_{alert['event_id']}"):
                    manager.alert_manager.resolve_alert(alert["event_id"])
                    # If this was empty bag or occlusion, reset simulator
                    if "EMPTY" in alert["event_type"] or "OCCLUSION" in alert["event_type"]:
                        simulator.reset_bag(500.0)
                    st.rerun()

with col_contract:
    st.markdown("### 📜 Event Schema Contract")
    st.caption("Validating all generated events against `shared/schemas/event_schema.json`")

    history = manager.alert_manager.get_alert_history(patient_id=selected_pid, limit=1)
    if history:
        sample_event = history[0]
        is_valid, error = generator.is_valid(sample_event)
        if is_valid:
            st.success("✅ **100% Schema Compliant**\nEvent structure validated against JSON Schema.")
        else:
            st.error(f"❌ Schema Validation Error: {error}")

        with st.expander("Latest Telemetry JSON Payload", expanded=True):
            st.code(json.dumps(sample_event, indent=2), language="json")
    else:
        st.info("Trigger any scenario on the left to inspect generated event telemetry.")

st.divider()

# ----------------- RECENT EVENT AUDIT TRAIL -----------------
with st.expander("📜 Full Audit Log & Event History", expanded=False):
    all_events = manager.alert_manager.get_alert_history(patient_id=selected_pid, limit=20)
    if not all_events:
        st.write("No events recorded yet.")
    else:
        st.dataframe(
            all_events,
            column_order=["timestamp", "event_id", "severity", "event_type", "parameter", "value", "unit", "status", "message"],
            use_container_width=True,
        )
