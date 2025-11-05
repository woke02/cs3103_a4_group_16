"""
H-UDP Sender/Receiver Application

This application provides a comprehensive UI to demonstrate the H-UDP protocol:
1. Initialize as either sender or receiver
2. Select game-relevant payload presets or customize payloads
3. Control reliability (reliable SR-ARQ vs unreliable fire-and-forget)
4. View real-time logs and protocol metrics
5. Save logs to file for later analysis

The application uses threading to run network operations without blocking the UI.
It integrates with the GameNetAPI from src/game_net_api.py.
"""


import json
import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

import config

# Add parent directory to path to import src and config
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the H-UDP API
from src.protocol import packet as pkt
from src.game_net_api import GameNetAPI

class HUDPApp:
    """
    Main application class for the H-UDP sender/receiver demo.

    This class manages the UI, logging, and network operations for demonstrating
    the H-UDP protocol with game-relevant payloads.
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the application.

        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("H-UDP Protocol Demo")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")

        # --- State Variables ---
        self.running = True
        self.api = None  # Will be initialized when user selects role
        self.role = None  # 'sender' or 'receiver'
        self.sender_thread = None
        self.receiver_thread = None
        self.log_queue = queue.Queue()  # Thread-safe queue for log messages

        # Statistics tracking
        self.stats = {
            'sent_reliable': 0,
            'sent_unreliable': 0,
            'received_reliable': 0,
            'received_unreliable': 0,
            'total_latency': 0,
            'latency_count': 0,
            'bytes_sent_reliable': 0,
            'bytes_sent_unreliable': 0,
            'bytes_received_reliable': 0,
            'bytes_received_unreliable': 0,
            'start_time': None,  # Will be set when operation starts
        }

        # --- UI Setup ---
        self.create_widgets()
        self.setup_logging()

        # --- Window close handler ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start log queue processor
        self.root.after(100, self.process_log_queue)

        logging.info("Application initialized. Select a role to begin.")

    # ========================================================================
    # UI CREATION
    # ========================================================================

    def create_widgets(self):
        """Creates all UI elements in the main window."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Role Selection Frame ---
        self.create_role_frame(main_frame)

        # --- Control Frame ---
        self.create_control_frame(main_frame)

        # --- Payload Configuration Frame ---
        self.create_payload_frame(main_frame)

        # --- Statistics Frame ---
        self.create_stats_frame(main_frame)

        # --- Logging Frame ---
        self.create_log_frame(main_frame)

        # Configure grid weights for responsive layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Log frame expands

    def create_role_frame(self, parent: ttk.Frame):
        """Creates the role selection and network configuration frame."""
        role_frame = ttk.LabelFrame(
            parent, text="1. Network Configuration & Role Selection", padding="10")
        role_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Role selection
        ttk.Label(role_frame, text="Role:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")

        self.role_var = tk.StringVar(value="sender")
        self.role_var.trace('w', self.on_role_change)

        # Store radio button references so we can disable them later
        self.role_sender_radio = ttk.Radiobutton(
            role_frame, text="Sender", variable=self.role_var, value="sender")
        self.role_sender_radio.grid(row=0, column=1, padx=5, pady=5)

        self.role_receiver_radio = ttk.Radiobutton(
            role_frame, text="Receiver", variable=self.role_var, value="receiver")
        self.role_receiver_radio.grid(row=0, column=2, padx=5, pady=5)

        # Network configuration fields
        # Local port
        ttk.Label(role_frame, text="Local Port:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w")

        self.local_port_var = tk.StringVar(value=str(config.SENDER_PORT))
        self.local_port_entry = ttk.Entry(
            role_frame, textvariable=self.local_port_var, width=10)
        self.local_port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Remote port (for sender only)
        ttk.Label(role_frame, text="Remote Port:").grid(
            row=1, column=2, padx=5, pady=5, sticky="w")

        self.remote_port_var = tk.StringVar(value=str(config.RECEIVER_PORT))
        self.remote_port_entry = ttk.Entry(
            role_frame, textvariable=self.remote_port_var, width=10)
        self.remote_port_entry.grid(
            row=1, column=3, padx=5, pady=5, sticky="w")

        # Remote host (for sender only)
        ttk.Label(role_frame, text="Remote Host:").grid(
            row=1, column=4, padx=5, pady=5, sticky="w")

        self.remote_host_var = tk.StringVar(value=config.HOST)
        self.remote_host_entry = ttk.Entry(
            role_frame, textvariable=self.remote_host_var, width=15)
        self.remote_host_entry.grid(
            row=1, column=5, padx=5, pady=5, sticky="w")

        # Timeouts
        ttk.Label(role_frame, text="Sender Timeout (ms):").grid(
            row=2, column=0, padx=5, pady=5, sticky="w")

        self.sender_timeout_var = tk.StringVar(
            value=str(int(config.SENDER_TIMEOUT * 1000)))
        self.sender_timeout_entry = ttk.Entry(
            role_frame, textvariable=self.sender_timeout_var, width=10)
        self.sender_timeout_entry.grid(
            row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(role_frame, text="Receiver Timeout (ms):").grid(
            row=2, column=2, padx=5, pady=5, sticky="w")

        self.receiver_timeout_var = tk.StringVar(
            value=str(int(config.RECEIVER_TIMEOUT * 1000)))
        self.receiver_timeout_entry = ttk.Entry(
            role_frame, textvariable=self.receiver_timeout_var, width=10)
        self.receiver_timeout_entry.grid(
            row=2, column=3, padx=5, pady=5, sticky="w")

        # Log filename field
        ttk.Label(role_frame, text="Log Filename:").grid(
            row=2, column=4, padx=5, pady=5, sticky="w")

        self.log_filename_var = tk.StringVar(value=config.SENDER_LOG_FILE)
        self.log_filename_entry = ttk.Entry(
            role_frame, textvariable=self.log_filename_var, width=15)
        self.log_filename_entry.grid(
            row=2, column=5, padx=5, pady=5, sticky="w")

        # Log Level selection
        ttk.Label(role_frame, text="Log Level:").grid(
            row=3, column=0, padx=5, pady=5, sticky="w")

        # Map logging levels to user-friendly names
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        self.log_level_names = list(log_levels.keys())
        self.log_level_values = log_levels

        # Get current log level name
        current_level_name = "INFO"
        for name, level in log_levels.items():
            if level == config.LOG_LEVEL:
                current_level_name = name
                break

        self.log_level_var = tk.StringVar(value=current_level_name)
        self.log_level_menu = ttk.OptionMenu(
            role_frame, self.log_level_var, current_level_name, *self.log_level_names)
        self.log_level_menu.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Initialize button
        self.btn_initialize = ttk.Button(
            role_frame, text="Initialize", command=self.initialize_api)
        self.btn_initialize.grid(
            row=3, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        # Status label
        self.status_label = ttk.Label(role_frame, text="Status: Not Initialized",
                                      foreground="red")
        self.status_label.grid(
            row=3, column=4, columnspan=2, padx=5, pady=5, sticky="w")

        # Configure column weights
        role_frame.columnconfigure(0, weight=0)
        role_frame.columnconfigure(1, weight=1)
        role_frame.columnconfigure(2, weight=0)
        role_frame.columnconfigure(3, weight=1)

        # Initially update field states based on role
        self.on_role_change()

    def create_control_frame(self, parent: ttk.Frame):
        """Creates the sender control buttons frame."""
        control_frame = ttk.LabelFrame(
            parent, text="2. Sender Control", padding="10")
        control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.btn_start = ttk.Button(
            control_frame, text="Start", command=self.start_operation,
            state="disabled")
        self.btn_start.grid(row=0, column=0, padx=5, pady=5)

        self.btn_stop = ttk.Button(
            control_frame, text="Stop", command=self.stop_operation,
            state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=5, pady=5)

        self.btn_send_one = ttk.Button(
            control_frame, text="Send One Packet", command=self.send_one_packet,
            state="disabled")
        self.btn_send_one.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(control_frame, text="Send Interval (ms):").grid(
            row=0, column=3, padx=5, pady=5)

        self.interval_var = tk.StringVar(
            value=str(int(config.PACKET_INTERVAL_SEC * 1000)))
        self.interval_entry = ttk.Entry(control_frame, textvariable=self.interval_var,
                                        width=10)
        self.interval_entry.grid(row=0, column=4, padx=5, pady=5)

    def create_payload_frame(self, parent: ttk.Frame):
        """Creates the payload configuration frame."""
        payload_frame = ttk.LabelFrame(parent, text="3. Payload Configuration",
                                       padding="10")
        payload_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        # Preset selection
        ttk.Label(payload_frame, text="Preset:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")

        self.payload_preset_var = tk.StringVar(self.root)
        presets = list(config.PAYLOAD_PRESETS.keys())
        self.payload_preset_var.set(presets[0])

        self.payload_preset_menu = ttk.OptionMenu(
            payload_frame, self.payload_preset_var, presets[0], *presets,
            command=self.on_preset_change)
        self.payload_preset_menu.grid(
            row=0, column=1, padx=5, pady=5, sticky="ew")

        # Description display
        ttk.Label(payload_frame, text="Description:").grid(
            row=1, column=0, padx=5, pady=5, sticky="nw")

        self.description_label = ttk.Label(payload_frame, text="", wraplength=600,
                                           justify="left")
        self.description_label.grid(row=1, column=1, columnspan=2, padx=5, pady=5,
                                    sticky="w")

        # Custom payload entry
        ttk.Label(payload_frame, text="Payload:").grid(
            row=2, column=0, padx=5, pady=5, sticky="nw")

        self.payload_text = scrolledtext.ScrolledText(
            payload_frame, height=9, width=70, wrap=tk.WORD)
        self.payload_text.grid(row=2, column=1, columnspan=3, padx=5, pady=5,
                               sticky="ew")

        # Reliability selection
        ttk.Label(payload_frame, text="Reliability:").grid(
            row=3, column=0, padx=5, pady=5, sticky="w")

        self.reliability_var = tk.StringVar(value="auto")

        # Create a frame to hold the radio buttons together
        self.reliability_buttons_frame = ttk.Frame(payload_frame)
        self.reliability_buttons_frame.grid(
            row=3, column=1, padx=5, pady=2, sticky="w")

        # Store reliability radio button references
        self.reliability_auto_radio = ttk.Radiobutton(
            self.reliability_buttons_frame, text="Auto (Based on Type)",
            variable=self.reliability_var, value="auto")
        self.reliability_auto_radio.pack(side="left", padx=(0, 10))

        self.reliability_reliable_radio = ttk.Radiobutton(
            self.reliability_buttons_frame, text="Force Reliable",
            variable=self.reliability_var, value="reliable")
        self.reliability_reliable_radio.pack(side="left", padx=(0, 10))

        self.reliability_unreliable_radio = ttk.Radiobutton(
            self.reliability_buttons_frame, text="Force Unreliable",
            variable=self.reliability_var, value="unreliable")
        self.reliability_unreliable_radio.pack(side="left")

        payload_frame.columnconfigure(1, weight=1)

        # Initialize with first preset
        self.on_preset_change(presets[0])

    def create_stats_frame(self, parent: ttk.Frame):
        """Creates the statistics display frame."""
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding="10")
        stats_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        self.stats_text = tk.Text(stats_frame, height=3, width=80,
                                  state="disabled")
        self.stats_text.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Buttons frame for Reset and Show PDR
        btn_frame = ttk.Frame(stats_frame)
        btn_frame.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.btn_reset_stats = ttk.Button(
            btn_frame, text="Reset Statistics", command=self.reset_statistics)
        self.btn_reset_stats.pack(side="left", padx=(0, 5))

        self.btn_show_pdr = ttk.Button(
            btn_frame, text="Show PDR Stats", command=self.show_pdr_stats)
        self.btn_show_pdr.pack(side="left")

        stats_frame.columnconfigure(0, weight=1)

        self.update_stats_display()

    def create_log_frame(self, parent: ttk.Frame):
        """Creates the log display frame."""
        log_frame = ttk.LabelFrame(
            parent, text="Application Log", padding="10")
        log_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")

        # Log display with scrollbar
        self.log_widget = scrolledtext.ScrolledText(
            log_frame, height=15, width=80, state="disabled", wrap=tk.WORD)
        self.log_widget.grid(row=0, column=0, sticky="nsew")

        # Configure tag colors for different log levels
        for level, color in config.LOG_COLORS.items():
            self.log_widget.tag_config(level, foreground=color)

        # Control buttons
        btn_frame = ttk.Frame(log_frame)
        btn_frame.grid(row=1, column=0, pady=5, sticky="ew")

        ttk.Button(btn_frame, text="Clear Log",
                   command=self.clear_log).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save Log to File",
                   command=self.save_log).pack(side="left", padx=5)

        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def on_role_change(self, *args):
        """
        Handles role selection change to enable/disable relevant fields.
        """
        role = self.role_var.get()

        # Update default local port and log filename based on role
        if role == 'sender':
            self.local_port_var.set(str(config.SENDER_PORT))
            self.log_filename_var.set(config.SENDER_LOG_FILE)
            # Enable sender-specific fields
            self.remote_host_entry.config(state="normal")
            self.remote_port_entry.config(state="normal")
            self.sender_timeout_entry.config(state="normal")
            # Disable receiver-specific fields
            self.receiver_timeout_entry.config(state="disabled")
            # Enable payload configuration (sender needs it) - only if widgets exist
            if hasattr(self, 'payload_preset_menu'):
                self.payload_preset_menu.config(state="normal")
                self.payload_text.config(state="normal")
                self.reliability_auto_radio.config(state="normal")
                self.reliability_reliable_radio.config(state="normal")
                self.reliability_unreliable_radio.config(state="normal")
            # Enable send interval (sender needs it)
            if hasattr(self, 'interval_entry'):
                self.interval_entry.config(state="normal")
        else:  # receiver
            self.local_port_var.set(str(config.RECEIVER_PORT))
            self.log_filename_var.set(config.RECEIVER_LOG_FILE)
            # Disable sender-specific fields (not needed)
            self.remote_host_entry.config(state="disabled")
            self.remote_port_entry.config(state="disabled")
            self.sender_timeout_entry.config(state="disabled")
            # Enable receiver-specific fields
            self.receiver_timeout_entry.config(state="normal")
            # Disable payload configuration (receiver doesn't send) - only if widgets exist
            if hasattr(self, 'payload_preset_menu'):
                self.payload_preset_menu.config(state="disabled")
                self.payload_text.config(state="disabled")
                self.reliability_auto_radio.config(state="disabled")
                self.reliability_reliable_radio.config(state="disabled")
                self.reliability_unreliable_radio.config(state="disabled")
            # Disable send interval (receiver doesn't send)
            if hasattr(self, 'interval_entry'):
                self.interval_entry.config(state="disabled")

    def on_preset_change(self, selected_preset):
        """
        Handles preset selection change.

        Args:
            selected_preset (str): The selected preset name
        """
        if selected_preset == "Custom":
            self.payload_text.delete(1.0, tk.END)
            self.payload_text.insert(1.0, "")
            self.description_label.config(
                text="Enter custom payload (JSON format recommended)")
        else:
            # Get preset data
            preset_data = config.PAYLOAD_PRESETS[selected_preset]
            description = preset_data.get("description", "")

            # Update description
            self.description_label.config(text=description)

            # Update payload text
            payload_json = json.dumps(preset_data, indent=2)
            self.payload_text.delete(1.0, tk.END)
            self.payload_text.insert(1.0, payload_json)

    def initialize_api(self):
        """Initializes the GameNetAPI with values from UI fields."""
        if self.api is not None:
            messagebox.showwarning("Already Initialized",
                                   "API is already initialized. Restart the application to change roles.")
            return

        self.role = self.role_var.get()

        # Validate and parse input values
        try:
            local_port = int(self.local_port_var.get())
            if not (1024 <= local_port <= 65535):
                raise ValueError("Port must be between 1024 and 65535")

            # Convert ms to seconds
            sender_timeout = float(self.sender_timeout_var.get()) / 1000.0
            # Convert ms to seconds
            receiver_timeout = float(self.receiver_timeout_var.get()) / 1000.0

            if sender_timeout <= 0 or receiver_timeout <= 0:
                raise ValueError("Timeouts must be positive values")

            # Validate log filename
            log_filename = self.log_filename_var.get().strip()
            if not log_filename:
                raise ValueError("Log filename cannot be empty")

            remote_host = None
            remote_port = None

            if self.role == 'sender':
                remote_host = self.remote_host_var.get().strip()
                remote_port = int(self.remote_port_var.get())

                if not remote_host:
                    raise ValueError("Remote host cannot be empty")
                if not (1024 <= remote_port <= 65535):
                    raise ValueError(
                        "Remote port must be between 1024 and 65535")

        except ValueError as e:
            messagebox.showerror(
                "Invalid Input", f"Invalid configuration: {e}")
            return

        try:
            if self.role == 'sender':
                # Initialize as sender with UI values
                self.api = GameNetAPI(
                    role='sender',
                    local_port=local_port,
                    remote_addr=(remote_host, remote_port),
                    sender_timeout=sender_timeout,
                    receiver_timeout=receiver_timeout
                )
                logging.info(f"Initialized as SENDER on port {local_port}, "
                             f"remote={remote_host}:{remote_port}, "
                             f"sender_timeout={sender_timeout}s, receiver_timeout={receiver_timeout}s")
            else:
                # Initialize as receiver with UI values
                self.api = GameNetAPI(
                    role='receiver',
                    local_port=local_port,
                    sender_timeout=sender_timeout,
                    receiver_timeout=receiver_timeout
                )
                logging.info(f"Initialized as RECEIVER on port {local_port}, "
                             f"sender_timeout={sender_timeout}s, receiver_timeout={receiver_timeout}s")

            # Apply the selected log level
            selected_log_level = self.log_level_values[self.log_level_var.get(
            )]
            logging.getLogger().setLevel(selected_log_level)
            logging.info(f"Log level set to {self.log_level_var.get()}")

            # Add file logging now that role is set
            self.add_file_logging()

            # Disable configuration fields after initialization
            self.role_sender_radio.config(state="disabled")
            self.role_receiver_radio.config(state="disabled")
            self.local_port_entry.config(state="disabled")
            self.remote_host_entry.config(state="disabled")
            self.remote_port_entry.config(state="disabled")
            self.sender_timeout_entry.config(state="disabled")
            self.receiver_timeout_entry.config(state="disabled")
            self.log_level_menu.config(state="disabled")
            self.log_filename_entry.config(state="disabled")

            # Update UI with clear visual feedback
            self.status_label.config(
                text=f"Status: Initialized as {self.role.upper()}",
                foreground="green")
            # Change button text and disable it (macOS ttk doesn't always show visual disabled state)
            self.btn_initialize.config(text="✓ Initialized", state="disabled")

            # Enable start/stop only for sender
            if self.role == 'sender':
                self.btn_start.config(state="normal")
                self.btn_send_one.config(state="normal")
            else:
                # Receiver doesn't need start/stop buttons
                self.btn_start.config(state="disabled")
                self.btn_stop.config(state="disabled")
                self.btn_send_one.config(state="disabled")
                # Auto-start receiver (it runs continuously)
                self.start_receiver()

        except Exception as e:
            logging.error(f"Failed to initialize API: {e}")
            messagebox.showerror("Initialization Error",
                                 f"Failed to initialize API:\n{e}")

    def start_operation(self):
        """Starts the sender operation (automatic sending)."""
        if self.api is None:
            messagebox.showwarning(
                "Not Initialized", "Please initialize first.")
            return

        if self.role != 'sender':
            return

        self.start_sender()

        # Update button states with visual feedback
        self.btn_start.config(text="▶ Running", state="disabled")
        self.btn_stop.config(text="Stop", state="normal")

    def stop_operation(self):
        """Stops the sender operation (automatic sending)."""
        if self.role != 'sender':
            # This shouldn't happen since button is disabled for receiver
            return

        if self.sender_thread:
            logging.info("Stopping sender...")

        self.api.log_experiment(start=False)
        self.running = False

        # Update button states with visual feedback
        self.btn_start.config(text="Start", state="normal")
        self.btn_stop.config(text="■ Stopped", state="disabled")

    def send_one_packet(self):
        """Sends a single packet with the current payload configuration."""
        if self.api is None:
            messagebox.showwarning(
                "Not Initialized", "Please initialize first.")
            return

        if self.role != 'sender':
            # This shouldn't happen since button is disabled for receiver
            return

        try:
            # Get payload from UI
            payload_text = self.payload_text.get(1.0, tk.END).strip()

            if not payload_text:
                logging.warning("Empty payload, cannot send.")
                messagebox.showwarning(
                    "Empty Payload", "Please enter a payload to send.")
                return

            # Determine reliability
            reliability_choice = self.reliability_var.get()

            if reliability_choice == "auto":
                is_reliable = config.get_suggested_reliability(payload_text)
            elif reliability_choice == "reliable":
                is_reliable = True
            else:  # unreliable
                is_reliable = False

            # Convert to bytes
            payload_bytes = payload_text.encode('utf-8')

            # Check payload size
            if len(payload_bytes) > pkt.MAX_PAYLOAD_SIZE:
                logging.error(
                    f"Payload too large: {len(payload_bytes)} bytes > {pkt.MAX_PAYLOAD_SIZE} bytes")
                messagebox.showerror(
                    "Payload Too Large",
                    f"Payload size ({len(payload_bytes)}B) exceeds maximum ({pkt.MAX_PAYLOAD_SIZE}B)")
                return

            # Send via API
            seq_no = self.api.send(payload_bytes, reliable=is_reliable)

            # Log what we're sending
            payload_preview = payload_text[:50] + \
                "..." if len(payload_text) > 50 else payload_text
            logging.info(f"[SENDING ONE] Seq={seq_no}, Reliable={is_reliable}, "
                         f"Size={len(payload_bytes)}B, Payload={payload_preview}")

            # Update statistics
            if is_reliable:
                self.stats['sent_reliable'] += 1
                self.stats['bytes_sent_reliable'] += len(payload_bytes)
            else:
                self.stats['sent_unreliable'] += 1
                self.stats['bytes_sent_unreliable'] += len(payload_bytes)

            # Initialize start_time if this is the first packet
            if self.stats['start_time'] is None:
                self.stats['start_time'] = time.time()

            self.update_stats_display()

        except Exception as e:
            logging.error(f"Failed to send packet: {e}")
            messagebox.showerror("Send Error", f"Failed to send packet:\n{e}")

    # ========================================================================
    # ========================================================================

    def start_sender(self):
        """Starts the sender loop in a separate thread."""
        self.running = True
        self.api.log_experiment(start=True)

        # Reset start time only if this is the first start (not a resume)
        if self.stats['start_time'] is None:
            self.stats['start_time'] = time.time()

        # Start sender thread if not already running
        if self.sender_thread is None or not self.sender_thread.is_alive():
            self.sender_thread = threading.Thread(
                target=self.sender_loop, daemon=True)
            self.sender_thread.start()
            print("Sender thread started.")
            logging.info("Sender thread started.")

    def sender_loop(self):
        """
        Main sender loop - runs in a separate thread.
        Sends packets at the configured interval.
        """
        while self.running:
            interval_sec = config.PACKET_INTERVAL_SEC  # Default value
            try:
                # Get interval from UI
                try:
                    interval_ms = int(self.interval_var.get())
                    interval_sec = interval_ms / 1000.0
                except ValueError:
                    interval_sec = config.PACKET_INTERVAL_SEC

                # Get payload from UI
                payload_text = self.payload_text.get(1.0, tk.END).strip()

                if not payload_text:
                    logging.warning("Empty payload, skipping send.")
                    time.sleep(interval_sec)
                    continue

                # Determine reliability
                reliability_choice = self.reliability_var.get()

                if reliability_choice == "auto":
                    is_reliable = config.get_suggested_reliability(
                        payload_text)
                elif reliability_choice == "reliable":
                    is_reliable = True
                else:  # unreliable
                    is_reliable = False

                # Convert to bytes
                payload_bytes = payload_text.encode('utf-8')

                # Check payload size
                if len(payload_bytes) > pkt.MAX_PAYLOAD_SIZE:
                    logging.error(
                        f"Payload too large: {len(payload_bytes)} bytes > {pkt.MAX_PAYLOAD_SIZE} bytes")
                    time.sleep(interval_sec)
                    continue

                # Send via API
                if self.api is None:
                    logging.error("API not initialized, cannot send.")
                    time.sleep(interval_sec)
                    continue
                seq_no = self.api.send(payload_bytes, reliable=is_reliable)

                # Log what we're sending
                payload_preview = payload_text[:50] + \
                    "..." if len(payload_text) > 50 else payload_text
                logging.info(f"[SENDING] Seq={seq_no}, Reliable={is_reliable}, "
                             f"Size={len(payload_bytes)}B, Payload={payload_preview}")

                # Update statistics
                if is_reliable:
                    self.stats['sent_reliable'] += 1
                    self.stats['bytes_sent_reliable'] += len(payload_bytes)
                else:
                    self.stats['sent_unreliable'] += 1
                    self.stats['bytes_sent_unreliable'] += len(payload_bytes)

                self.update_stats_display()

            except Exception as e:
                if self.running:
                    logging.error(f"Sender loop error: {e}")

            # Wait for next interval
            time.sleep(interval_sec)

        logging.info("Sender loop stopped.")

    # ========================================================================
    # RECEIVER LOGIC
    # ========================================================================

    def start_receiver(self):
        """Starts the receiver loop in a separate thread (called automatically on init)."""
        self.running = True
        self.stats['start_time'] = time.time()

        self.receiver_thread = threading.Thread(
            target=self.receiver_loop, daemon=True)
        self.receiver_thread.start()
        logging.info("Receiver thread started.")

    def receiver_loop(self):
        """
        Main receiver loop - runs in a separate thread.
        Continuously receives packets from the API.
        """
        while self.running:
            try:
                # Receive packet (with timeout to allow checking self.running)
                if self.api is None:
                    logging.error("API not initialized, cannot receive.")
                    time.sleep(0.1)
                    continue
                packet = self.api.receive(timeout=1.0)

                if packet:
                    # Extract packet information
                    seq_no = packet['seq_no']
                    payload = packet['payload']
                    latency = packet['latency']
                    channel = packet['channel']

                    is_reliable = (channel == 'reliable')

                    # Try to decode payload
                    try:
                        payload_str = payload.decode('utf-8')
                        payload_preview = payload_str[:50] + \
                            "..." if len(payload_str) > 50 else payload_str
                    except UnicodeDecodeError:
                        payload_preview = f"[BINARY: {len(payload)} bytes]"

                    # Log the received packet
                    logging.info(f"[RECEIVED] Seq={seq_no}, Channel={channel}, "
                                 f"Latency={latency}ms, Payload={payload_preview}")

                    # Update statistics
                    if is_reliable:
                        self.stats['received_reliable'] += 1
                        self.stats['bytes_received_reliable'] += len(payload)
                    else:
                        self.stats['received_unreliable'] += 1
                        self.stats['bytes_received_unreliable'] += len(payload)

                    self.stats['total_latency'] += latency
                    self.stats['latency_count'] += 1

                    self.update_stats_display()

            except Exception as e:
                if self.running:
                    logging.error(f"Receiver loop error: {e}")

        logging.info("Receiver loop stopped.")

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    def setup_logging(self):
        """Configures the logging system for UI display (file logging added on init)."""

        class QueueHandler(logging.Handler):
            """Custom logging handler that puts messages into a thread-safe queue."""

            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue

            def emit(self, record):
                self.log_queue.put(self.format(record))

        # Get or create logger
        logger = logging.getLogger()
        logger.setLevel(config.LOG_LEVEL)

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatter
        self.log_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)-5s] %(message)s',
            datefmt='%H:%M:%S'
        )

        # Queue handler for UI (file handler will be added after role is set)
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(self.log_formatter)
        logger.addHandler(queue_handler)

    def add_file_logging(self):
        """Adds file logging handler using the user-specified filename."""
        logger = logging.getLogger()

        # Use the filename from the UI field
        log_file = self.log_filename_var.get().strip()

        # Create logs directory in the directory where the script is run
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Add file handler
        file_handler = logging.FileHandler(
            os.path.join(logs_dir, log_file), mode='w')
        file_handler.setFormatter(self.log_formatter)
        logger.addHandler(file_handler)

        logging.info(f"File logging enabled: {log_file}")

    def process_log_queue(self):
        """
        Processes log messages from the queue and updates the UI.
        This method is called periodically by the tkinter event loop.
        """
        while not self.log_queue.empty():
            try:
                message = self.log_queue.get_nowait()

                # Determine log level from message
                level = "INFO"
                if "[ERROR]" in message or "ERROR" in message:
                    level = "ERROR"
                elif "[WARNING]" in message or "WARNING" in message:
                    level = "WARNING"
                elif "[DEBUG]" in message or "DEBUG" in message:
                    level = "DEBUG"

                # Insert into log widget with appropriate color
                self.log_widget.config(state="normal")
                self.log_widget.insert(tk.END, message + "\n", level)
                self.log_widget.see(tk.END)  # Auto-scroll
                self.log_widget.config(state="disabled")

            except queue.Empty:
                break

        # Reschedule
        self.root.after(100, self.process_log_queue)

    def clear_log(self):
        """Clears the log display."""
        self.log_widget.config(state="normal")
        self.log_widget.delete(1.0, tk.END)
        self.log_widget.config(state="disabled")
        logging.info("Log display cleared.")

    def save_log(self):
        """Saves the current log display to a file."""
        # Create logs directory in the directory where the script is run
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Generate filename with role and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(logs_dir, f"{self.role}_{timestamp}.log")

        try:
            with open(filename, 'w') as f:
                log_content = self.log_widget.get(1.0, tk.END)
                f.write(log_content)

            logging.info(f"Log saved to {filename}")
            messagebox.showinfo("Log Saved", f"Log saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save log: {e}")
            messagebox.showerror("Save Error", f"Failed to save log:\n{e}")

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def reset_statistics(self):
        """Resets all statistics counters."""
        self.stats = {
            'sent_reliable': 0,
            'sent_unreliable': 0,
            'received_reliable': 0,
            'received_unreliable': 0,
            'total_latency': 0,
            'latency_count': 0,
            'bytes_sent_reliable': 0,
            'bytes_sent_unreliable': 0,
            'bytes_received_reliable': 0,
            'bytes_received_unreliable': 0,
            'start_time': time.time() if self.running else None,  # Reset timer if running
        }

        # Clear API tracking data (sent/received packet files)
        if self.api:
            try:
                self.api.clear_tracking_data()
                logging.info("API tracking data cleared.")
            except Exception as e:
                logging.error(f"Failed to clear API tracking data: {e}")

        self.update_stats_display()
        logging.info("Statistics reset.")

    def update_stats_display(self):
        """Updates the statistics display (without PDR - use Show PDR button for that)."""
        avg_latency = (self.stats['total_latency'] / self.stats['latency_count']
                       if self.stats['latency_count'] > 0 else 0)

        # Calculate duration
        duration = time.time() - \
            self.stats['start_time'] if self.stats['start_time'] else 0

        # Calculate throughput (bytes/second) for each channel (receiver only)
        throughput_reliable = (self.stats['bytes_received_reliable'] / duration
                               if duration > 0 else 0)
        throughput_unreliable = (self.stats['bytes_received_unreliable'] / duration
                                 if duration > 0 else 0)

        # Build stats text based on role (without PDR)
        if self.role == 'sender':
            stats_text = (
                f"Sent Reliable: {self.stats['sent_reliable']} ({self.stats['bytes_sent_reliable']}B)  |  "
                f"Sent Unreliable: {self.stats['sent_unreliable']} ({self.stats['bytes_sent_unreliable']}B)\n"
                f"Duration: {duration:.2f}s"
            )
        else:  # receiver
            stats_text = (
                f"Received Reliable: {self.stats['received_reliable']} ({self.stats['bytes_received_reliable']}B)  |  "
                f"Received Unreliable: {self.stats['received_unreliable']} ({self.stats['bytes_received_unreliable']}B)\n"
                f"Throughput: Reliable={throughput_reliable:.2f} B/s, Unreliable={throughput_unreliable:.2f} B/s\n"
                f"Average Latency: {avg_latency:.2f}ms  |  Duration: {duration:.2f}s"
            )

        self.stats_text.config(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)
        self.stats_text.config(state="disabled")

    def show_pdr_stats(self):
        """Shows PDR statistics in a popup window."""
        if self.api is None:
            messagebox.showwarning(
                "Not Initialized", "Please initialize first.")
            return

        try:
            # Get delivery stats from API
            delivery_stats = self.api.get_delivery_stats()

            # Create popup window
            pdr_window = tk.Toplevel(self.root)
            pdr_window.title("Packet Delivery Ratio Statistics")
            pdr_window.geometry("500x400")

            # Create text widget with scrollbar
            text_frame = ttk.Frame(pdr_window, padding="10")
            text_frame.pack(fill="both", expand=True)

            pdr_text = scrolledtext.ScrolledText(
                text_frame, height=20, width=70, wrap=tk.WORD)
            pdr_text.pack(fill="both", expand=True)

            # Format PDR statistics
            separator = "=" * 60
            line = "-" * 60

            pdr_info = (
                f"{separator}\n"
                f"PACKET DELIVERY RATIO (PDR) STATISTICS\n"
                f"{separator}\n\n"
                f"Total Packets Sent: {delivery_stats['total_sent']}\n"
                f"Total Packets Received: {delivery_stats['total_received']}\n"
                f"Overall PDR: {delivery_stats['overall_delivery_ratio']:.2f}%\n\n"
                f"{line}\n"
                f"RELIABLE CHANNEL:\n"
                f"{line}\n"
                f"  Sent: {delivery_stats['reliable_sent']}\n"
                f"  Received: {delivery_stats['reliable_received']}\n"
                f"  PDR: {delivery_stats['reliable_delivery_ratio']:.2f}%\n\n"
                f"{line}\n"
                f"UNRELIABLE CHANNEL:\n"
                f"{line}\n"
                f"  Sent: {delivery_stats['unreliable_sent']}\n"
                f"  Received: {delivery_stats['unreliable_received']}\n"
                f"  PDR: {delivery_stats['unreliable_delivery_ratio']:.2f}%\n\n"
                f"{line}\n"
                f"LOST PACKETS: {len(delivery_stats['lost_packets'])}\n"
                f"{line}\n"
            )

            # Add lost packet details if any
            if delivery_stats['lost_packets']:
                pdr_info += "\nLost Packet Details:\n"
                # Show first 50
                for i, lost_pkt in enumerate(delivery_stats['lost_packets'][:50], 1):
                    channel = "Reliable" if lost_pkt['reliable'] else "Unreliable"
                    pdr_info += f"  {i}. Seq={lost_pkt['seq_no']}, Channel={channel}\n"
                if len(delivery_stats['lost_packets']) > 50:
                    pdr_info += f"\n  ... and {len(delivery_stats['lost_packets']) - 50} more\n"

            # Insert text
            pdr_text.insert(1.0, pdr_info)
            pdr_text.config(state="disabled")

            # Close button
            ttk.Button(pdr_window, text="Close",
                       command=pdr_window.destroy).pack(pady=10)

            logging.info("PDR statistics window opened.")

        except Exception as e:
            logging.error(f"Failed to get PDR stats: {e}")
            messagebox.showerror(
                "Error", f"Failed to get PDR statistics:\n{e}")
    # ========================================================================
    # CLEANUP
    # ========================================================================

    def on_closing(self):
        """Handles the window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            logging.info("Application shutting down...")
            self.running = False

            # Close API
            if self.api:
                try:
                    self.api.close()
                    logging.info("API closed successfully.")
                except Exception as e:
                    logging.error(f"Error closing API: {e}")

            # Give threads time to finish
            time.sleep(0.5)

            self.root.destroy()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = HUDPApp(root)
    root.mainloop()
