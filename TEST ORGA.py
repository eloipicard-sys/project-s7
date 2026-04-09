import sys
import time
from datetime import datetime
from thermal_model import ThermalProcessModel
from plc_connector import PLCConnector

#!/usr/bin/env python3
"""
Test CLI for S7-1500 Thermal Process Monitor PID Control Demonstration
Presents process state and setpoint control via command-line interface
"""


def print_header():
    """Display application header"""
    print("\n" + "="*70)
    print("  S7-1500 THERMAL PROCESS MONITOR - PID CONTROL TEST CLI".center(70))
    print("="*70 + "\n")

def print_state(model, plc_connected=False):
    """Display current process state"""
    source = "PLC" if plc_connected else "Simulation"
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] - Source: {source}")
    print("-" * 70)
    print(f"  Temperature:        {model.temp:.2f}°C  (Setpoint: {model.setpoint_temp:.2f}°C)")
    print(f"  Flow Rate:          {model.flow:.2f} m³/h  (Setpoint: {model.setpoint_flow:.2f} m³/h)")
    print(f"  Valve State:        {model.valve_state}")
    print(f"  Error (PID input):  {model.temp - model.setpoint_temp:.2f}°C")
    print("-" * 70)

def print_menu():
    """Display control menu"""
    print("\nOptions:")
    print("  [1] Increase temperature setpoint (+5°C)")
    print("  [2] Decrease temperature setpoint (-5°C)")
    print("  [3] Increase flow setpoint (+1 m³/h)")
    print("  [4] Decrease flow setpoint (-1 m³/h)")
    print("  [5] Run auto-demo (10 cycles)")
    print("  [0] Exit")
    print()

def run_simulation_cycle(model, cycles=1):
    """Execute simulation cycles"""
    for _ in range(cycles):
        model.step()
        time.sleep(0.5)

def main():
    """Main CLI loop"""
    print_header()
    
    # Initialize thermal model
    model = ThermalProcessModel(
        setpoint_temp=70.0,
        setpoint_flow=5.0,
        kp=2.0
    )
    
    print("Initializing thermal process model...")
    print(f"  Initial setpoint: {model.setpoint_temp}°C, {model.setpoint_flow} m³/h")
    print(f"  PLC Kp gain: {model.kp}")
    
    while True:
        print_state(model)
        print_menu()
        
        choice = input("Select option: ").strip()
        
        if choice == "1":
            model.setpoint_temp = min(model.setpoint_temp + 5, 100)
            print(f"✓ Temperature setpoint → {model.setpoint_temp}°C")
            run_simulation_cycle(model, cycles=3)
            
        elif choice == "2":
            model.setpoint_temp = max(model.setpoint_temp - 5, 20)
            print(f"✓ Temperature setpoint → {model.setpoint_temp}°C")
            run_simulation_cycle(model, cycles=3)
            
        elif choice == "3":
            model.setpoint_flow = min(model.setpoint_flow + 1, 15)
            print(f"✓ Flow setpoint → {model.setpoint_flow} m³/h")
            run_simulation_cycle(model, cycles=3)
            
        elif choice == "4":
            model.setpoint_flow = max(model.setpoint_flow - 1, 0.5)
            print(f"✓ Flow setpoint → {model.setpoint_flow} m³/h")
            run_simulation_cycle(model, cycles=3)
            
        elif choice == "5":
            print("\n► Auto-demo: adjusting setpoint to 85°C over 10 cycles...")
            model.setpoint_temp = 85.0
            for i in range(10):
                print(f"\n  Cycle {i+1}/10:")
                print_state(model)
                run_simulation_cycle(model, cycles=1)
                
        elif choice == "0":
            print("\n✓ Exiting. Goodbye!\n")
            sys.exit(0)
        else:
            print("✗ Invalid option. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Program interrupted by user.\n")
        sys.exit(0)


if __name__ == "__other__":
    # This block is for testing the logger independently
    from logger import init_logger, log_sample

    init_logger()
    log_sample({
        "timestamp": "2024-06-01 12:00:00",
        "temperature": 75.5,
        "setpoint_temp": 80.0,
        "flow_rate": 5.2,
        "setpoint_flow": 5.0,
        "valve_state": "OPEN",
        "source": "TEST"
    })