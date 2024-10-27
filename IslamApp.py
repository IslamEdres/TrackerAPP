import sqlite3
import threading
import paramiko
import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import pandas as pd
import datetime
import socket
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#ADD      
# Function to execute the remote script on the server using SSH
def execute_remote_script(server_ip, port, username, password, script_path):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, port=port, username=username, password=password)

        stdin, stdout, stderr = ssh.exec_command(f'bash {script_path}')
        output = stdout.read().decode()
        error = stderr.read().decode()

        ssh.close()
        return error if error else output

    except Exception as e:
        return f"Failed to connect to {server_ip}: {str(e)}"

# Function to monitor the selected servers
def monitor_servers(live=False):
    selected_servers = [server_id for server_id, var in server_vars if var.get()]

    if not selected_servers:
        messagebox.showerror("Error", "No servers selected. Please select servers first.")
        return

    if not live:
        result_text.delete(1.0, tk.END)

    def monitor_loop():
        threads = []

        for server_id in selected_servers:
            conn = sqlite3.connect('calls_data.db')
            cursor = conn.cursor()
            cursor.execute('SELECT server_name, server_ip, port, username, password FROM servers WHERE id = ?', (server_id,))
            server = cursor.fetchone()
            conn.close()

            if server is None:
                continue

            server_name, server_ip, port, username, password = server

            def run_on_server(server_name, server_ip):
                result = execute_remote_script(server_ip, port, username, password, '/home/islam/PRI-TIME/bash-dahdicalls.sh')
                result_text.insert(tk.END, f"Data for {server_name} ({server_ip}):\n{result}\n\n")
                
                # Save result to the database
                save_result_to_db(server_name, result)

            thread = threading.Thread(target=run_on_server, args=(server_name, server_ip))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if live:
            root.after(1, lambda: monitor_servers(live=True))

    threading.Thread(target=monitor_loop, daemon=True).start()

# Function to save the result data to the database
def save_result_to_db(server_name, result):
    conn = sqlite3.connect('calls_data.db')
    cursor = conn.cursor()

    # Assuming the result format is:
    # inbound_calls:90
    # outbound_calls:0
    # pri_lines:3
    lines = result.splitlines()
    inbound_calls = outbound_calls = pri_lines = None
    
    for line in lines:
        if "inbound_calls" in line:
            inbound_calls = int(line.split(':')[1].strip())
        elif "outbound_calls" in line:
            outbound_calls = int(line.split(':')[1].strip())
        elif "pri_lines" in line:
            pri_lines = int(line.split(':')[1].strip())

    # Insert data into the report table
    try:
        cursor.execute('''INSERT INTO your_report_table (server_name, inbound_calls, outbound_calls, pri_lines, date_column)
                          VALUES (?, ?, ?, ?, DATE('now'))''', (server_name, inbound_calls, outbound_calls, pri_lines))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while saving data to the database: {e}")  # Log the error

    conn.close()

# Function to fetch servers from the database and populate the server list
def fetch_servers():
    conn = sqlite3.connect('calls_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, server_name FROM servers')
    servers = cursor.fetchall()
    conn.close()

    # Clear previous server checkbuttons before populating new ones
    for widget in server_frame.winfo_children():
        widget.destroy()

    for server_id, server_name in servers:
        var = tk.BooleanVar()
        server_vars.append((server_id, var))
        cb = tk.Checkbutton(server_frame, text=server_name, variable=var)
        cb.pack(anchor=tk.W)

# Function to clear all data from the database
def clear_data():
    conn = sqlite3.connect('calls_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM servers')
    cursor.execute('DELETE FROM your_report_table')  # Clear report data as well
    conn.commit()
    conn.close()

    # Clear checkbuttons
    for widget in server_frame.winfo_children():
        widget.destroy()
    
    messagebox.showinfo("Info", "All servers and report data have been deleted.")

# Function to add a new server to the database after validating credentials
def add_server():
    server_name = server_name_entry.get()
    server_ip = server_ip_entry.get()
    port = int(port_entry.get())
    username = username_entry.get()
    password = password_entry.get()

    if not server_name or not server_ip or not username or not password:
        messagebox.showerror("Error", "All fields are required.")
        return

    # Check if the server credentials are valid
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, port=port, username=username, password=password)
        ssh.close()

        # If connection is successful, add server to the database
        conn = sqlite3.connect('calls_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO servers (server_name, server_ip, port, username, password) VALUES (?, ?, ?, ?, ?)',
                       (server_name, server_ip, port, username, password))
        conn.commit()
        conn.close()

        # Clear the input fields
        server_name_entry.delete(0, tk.END)
        server_ip_entry.delete(0, tk.END)
        port_entry.delete(0, tk.END)
        username_entry.delete(0, tk.END)
        password_entry.delete(0, tk.END)

        messagebox.showinfo("Success", f"Server {server_name} added successfully!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect to {server_ip}: {str(e)}")

# Function to show the report window
def show_report_window():
    report_window = tk.Toplevel(root)
    report_window.title("Report")

    tk.Label(report_window, text="From Date").pack()
    from_date = DateEntry(report_window, width=12, background='darkblue', foreground='white', borderwidth=2)
    from_date.pack(padx=10, pady=10)

    tk.Label(report_window, text="To Date").pack()
    to_date = DateEntry(report_window, width=12, background='darkblue', foreground='white', borderwidth=2)
    to_date.pack(padx=10, pady=10)

    tk.Label(report_window, text="Select Server").pack()
    server_combobox = ttk.Combobox(report_window)

    conn = sqlite3.connect('calls_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT server_name FROM servers')
    server_names = cursor.fetchall()
    conn.close()

    server_combobox['values'] = ["All Servers"] + [name[0] for name in server_names]
    server_combobox.pack(pady=10)

    def generate_report():
        start_date = from_date.get_date()
        end_date = to_date.get_date()
        selected_server = server_combobox.get()

        if start_date > end_date:
            messagebox.showerror("Error", "The start date must be earlier than the end date.")
            return

        conn = sqlite3.connect('calls_data.db')
        cursor = conn.cursor()

        if selected_server == "All Servers":
            cursor.execute('SELECT * FROM your_report_table WHERE date_column BETWEEN ? AND ?', (start_date, end_date))
        else:
            cursor.execute('SELECT * FROM your_report_table WHERE server_name = ? AND date_column BETWEEN ? AND ?', (selected_server, start_date, end_date))

        reports = cursor.fetchall()

        if not reports:
            report_output.delete(1.0, tk.END)
            report_output.insert(tk.END, "No reports found for the selected criteria.")
        else:
            # Create a DataFrame and save to Excel
            df = pd.DataFrame(reports, columns=['ID', 'Server Name', 'Total INbound', 'Total Outbound', 'Total PRI', 'Date'])
            excel_file = f'report_{selected_server.replace(" ", "_")}_{start_date}.xlsx'  # Generate a filename
            df.to_excel(excel_file, index=False)
            messagebox.showinfo("Success", f"Report saved as {excel_file}")

            report_output.delete(1.0, tk.END)
            report_text = "\n".join(str(report) for report in reports)
            report_output.insert(tk.END, report_text)

        conn.close()

    report_button = tk.Button(report_window, text="Generate Report", command=generate_report)
    report_button.pack(pady=10)

    report_output = tk.Text(report_window, height=10, width=50)
    report_output.pack(padx=10, pady=10)

# Initialize the main window
root = tk.Tk()
root.title("Call Monitoring Application")

# Create a frame for server management
server_frame = tk.Frame(root)
server_frame.pack(pady=10)

# Entry fields for server credentials
tk.Label(root, text="Server Name").pack()
server_name_entry = tk.Entry(root)
server_name_entry.pack(pady=5)

tk.Label(root, text="Server IP").pack()
server_ip_entry = tk.Entry(root)
server_ip_entry.pack(pady=5)

tk.Label(root, text="Port").pack()
port_entry = tk.Entry(root)
port_entry.pack(pady=5)

tk.Label(root, text="Username").pack()
username_entry = tk.Entry(root)
username_entry.pack(pady=5)

tk.Label(root, text="Password").pack()
password_entry = tk.Entry(root, show='*')
password_entry.pack(pady=5)

# Button frame for adding and clearing servers
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

add_button = tk.Button(button_frame, text="Add Server", command=add_server)
add_button.pack(side=tk.LEFT, padx=5)

clear_button = tk.Button(button_frame, text="Clear Data", command=clear_data)
clear_button.pack(side=tk.LEFT, padx=5)

fetch_servers_button = tk.Button(button_frame, text="Fetch Servers", command=fetch_servers)
fetch_servers_button.pack(side=tk.LEFT, padx=5)

# Dashboard buttons frame
dashboard_frame = tk.Frame(root)
dashboard_frame.pack(pady=10)

monitor_button = tk.Button(dashboard_frame, text="Monitor", command=lambda: monitor_servers(live=False))
monitor_button.pack(side=tk.LEFT, padx=5)

live_monitor_button = tk.Button(dashboard_frame, text="Live Monitor", command=lambda: monitor_servers(live=True))
live_monitor_button.pack(side=tk.LEFT, padx=5)

report_button = tk.Button(dashboard_frame, text="Show Report", command=show_report_window)
report_button.pack(side=tk.LEFT, padx=5)

# Text widget to display monitoring results
result_text = tk.Text(root, height=20, width=70)
result_text.pack(pady=10)

# List to keep track of server variables
server_vars = []

# Run the main application loop
root.mainloop()
